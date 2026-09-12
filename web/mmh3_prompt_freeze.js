import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Prompt Freeze 는 통과한 프롬프트를 자기 칸에 적어 둡니다. 파이썬 쪽이 실행 결과에
// {"ui": {"captured": [text]}} 를 실어 보내고, 여기서 그걸 받아 위젯에 씁니다.
//
// 칸이 늘 최신이라 따로 "지금 것을 고정" 같은 동작이 필요 없습니다 — 마음에 드는
// 결과가 나왔으면 드롭다운만 '저장된 것' 으로 바꾸면 그 텍스트가 계속 나갑니다.

const NODE = "MMH3_PromptFreeze";
const SAVED = "저장된 것 사용 — 위쪽 실행 안 함";

const w = (node, name) => node.widgets?.find(x => x.name === name);

api.addEventListener("executed", ({ detail }) => {
  try {
    const text = detail?.output?.captured?.[0];
    if (typeof text !== "string" || !text) return;
    const node = app.graph?.getNodeById?.(Number(detail.node));
    if (!node || node.comfyClass !== NODE) return;
    const box = w(node, "prompt_text");
    if (box && box.value !== text) box.value = text;
    // 요구사항이 적용됐으면 칸을 비웁니다. 남겨 두면 다음 실행에서 같은 수정이
    // 또 얹혀서, 클로즈업을 두 번 요청한 것처럼 됩니다.
    if (detail?.output?.clear_revise?.[0]) {
      const req = w(node, "revise");
      if (req) req.value = "";
    }
    node.setDirtyCanvas(true, true);
  } catch (e) { console.warn("[MMH3] prompt capture failed", e); }
});

app.registerExtension({
  name: "MMH3.PromptFreeze",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;

    // 지금 새 프롬프트가 오고 있는지, 저장된 걸 쓰고 있는지는 링크 상태로만 알 수
    // 있는데 그게 눈에 잘 안 띕니다. 한 줄로 보여줍니다.
    const onDraw = nodeType.prototype.onDrawForeground;
    nodeType.prototype.onDrawForeground = function (ctx) {
      onDraw?.apply(this, arguments);
      if (this.flags?.collapsed) return;
      const n = ((w(this, "prompt_text")?.value) || "").trim().length;
      const slot = this.inputs?.find(i => i.name === "live");
      const src = slot && slot.link != null ? this.graph?.getNodeById?.(
        this.graph.links[slot.link]?.origin_id) : null;
      const live = src && src.mode === 0;           // 0 = 정상, 2 = 뮤트, 4 = 바이패스
      const want = ((w(this, "revise")?.value) || "").trim().length;
      let msg, col;
      if (live && want) { msg = "위쪽이 켜져 있어 요구사항은 무시됨 · 뮤트하면 적용";
                          col = "#f4a742"; }
      else if (live)    { msg = "위쪽에서 새로 받는 중 · 실행하면 칸이 갱신됨"; col = "#9e9e9e"; }
      else if (want && n) { msg = `요구사항 ${want}자 · 실행하면 LLM이 고쳐서 다시 저장`;
                            col = "#7ee19d"; }
      else if (n)       { msg = `저장된 ${n}자 사용 · LLM 호출 안 함`;         col = "#8ecbff"; }
      else              { msg = "칸이 비어 있음 — 위쪽을 켜고 한 번 실행하세요"; col = "#f4a742"; }
      ctx.save();
      ctx.font = "11px sans-serif";
      ctx.fillStyle = col;
      ctx.textAlign = "left";
      ctx.fillText(msg, 10, this.size[1] + 14);
      ctx.restore();
    };
  },
});
