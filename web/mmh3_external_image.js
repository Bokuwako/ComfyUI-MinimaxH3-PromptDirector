import { app } from "../../scripts/app.js";

const PATH = "external_image_1_path";
const isLink = v => Array.isArray(v) && v.length === 2;

function dependsOn(output, root, target, seen = new Set()) {
  const id = String(root);
  if (id === target) return true;
  if (seen.has(id)) return false;
  seen.add(id);
  return Object.values(output[id]?.inputs || {}).some(v =>
    isLink(v) && dependsOn(output, v[0], target, seen));
}

// Fan out the real upstream path in the API graph, before caching/list mapping.
// Reading a Director output here would create Writer -> Director -> Writer cycles.
export function linkExternalImages(output) {
  const directors = Object.entries(output).filter(([, n]) => n.class_type === "MiniMaxH3Director");
  for (const [id, writer] of Object.entries(output)) {
    if (writer.class_type !== "MMH3_OllamaPromptWriter" || writer.inputs?.link_to_director === false) continue;
    const inputs = writer.inputs;
    const hint = String(inputs.director_node_id || "").trim();
    let candidates = directors.filter(([nid]) => nid === hint);
    if (!candidates.length) {
      candidates = directors.filter(([nid]) => dependsOn(output, nid, id));
      if (!candidates.length && directors.length === 1) candidates = directors;
    }
    if (candidates.length !== 1) {
      if (directors.some(([, d]) => d.inputs?.[PATH] != null))
        throw new Error("외부 이미지: Writer의 director_node_id로 사용할 Director를 지정하세요.");
      continue;
    }
    const [directorId, director] = candidates[0];
    const source = director.inputs?.[PATH];
    if (source == null) continue;
    if (isLink(source) && dependsOn(output, source[0], id))
      throw new Error("외부 이미지 경로는 Writer보다 앞쪽 노드에서 가져와야 합니다.");
    if (inputs[PATH] != null && JSON.stringify(inputs[PATH]) !== JSON.stringify(source))
      throw new Error("Director와 Writer의 external_image_1_path 연결이 다릅니다.");
    if (["first_frame", "last_frame", "ref_images"].some(k => inputs[k] != null))
      throw new Error("자동 이미지 연동을 쓰려면 Writer의 수동 IMAGE 연결을 해제하세요. 추가 레퍼런스는 Director에 넣으세요.");
    inputs[PATH] = isLink(source) ? [...source] : source;
    inputs.director_node_id = directorId;
  }
}

app.registerExtension({
  name: "MMH3.ExternalImageOne",
  setup() {
    const original = app.graphToPrompt;
    app.graphToPrompt = async function (...args) {
      const result = await original.apply(this, args);
      linkExternalImages(result.output);
      return result;
    };
  },
});
