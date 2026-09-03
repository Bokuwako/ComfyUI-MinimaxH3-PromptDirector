/**
 * picture_roles — a row editor for the MMH3 Prompt Writer.
 *
 * The `picture_roles` STRING widget stays the single source of truth: every row
 * edit rewrites it as "N: role" lines, and every reload rebuilds the rows from it.
 * The row widgets themselves are never serialized, so they can never shift the
 * node's widgets_values and break the Python side.
 *
 * If anything here throws, the node keeps working — you just type into the text
 * field like before.
 */

import { app } from "../../scripts/app.js";

const NODE = "MMH3_OllamaPromptWriter";
const FIELD = "picture_roles";
const TAG = "__mmh3RoleRow";
const TAG_BTN = "__mmh3RoleBtn";
const DELETE = "──────  ✕ 이 행 삭제";

const ROLES = [
  ["character", "캐릭터 / 인물"],
  ["background", "배경 / 장소"],
  ["costume", "의상"],
  ["pose", "자세 / 포즈"],
  ["expression", "표정"],
  ["motion", "동작 / 움직임"],
  ["style", "화풍 / 그림체"],
  ["prop", "소품 / 사물"],
  ["composition", "구도 / 프레이밍"],
  ["frame", "프레임 앵커"],
];

const CHOICES = ROLES.map(([k, ko]) => `${k}  ·  ${ko}`);
const keyOf = (choice) => String(choice || "").split("·")[0].trim().split(/\s+/)[0];
const choiceOf = (key) => CHOICES[ROLES.findIndex(([k]) => k === key)] || CHOICES[0];

function textWidget(node) {
  return (node.widgets || []).find((w) => w.name === FIELD);
}

function readRows(node) {
  const w = textWidget(node);
  const rows = [];
  if (!w) return rows;
  for (const raw of String(w.value || "").split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const m = line.match(/^(\d{1,2})\s*[:=]?\s*([^#]+?)\s*(?:#\s*(.*))?$/);
    if (!m) continue;
    const key = keyOf(m[2]) || m[2].trim().toLowerCase();
    if (!ROLES.some(([k]) => k === key)) continue;
    rows.push({ n: parseInt(m[1], 10) || 1, role: key, note: (m[3] || "").trim() });
  }
  return rows;
}

function writeRows(node, rows) {
  const w = textWidget(node);
  if (!w) return;
  // Insertion order is preserved on purpose: re-sorting here would make rows jump
  // around under the cursor mid-edit. The Python side sorts by picture number.
  w.value = rows
    .map((r) => `${r.n}: ${r.role}${r.note ? "  # " + r.note : ""}`)
    .join("\n");
  node.setDirtyCanvas(true, true);
}

function clearRowWidgets(node) {
  node.widgets = (node.widgets || []).filter((w) => !w[TAG]);
}

function addRowWidgets(node, rows) {
  rows.forEach((row, i) => {
    const combo = node.addWidget(
      "combo",
      `　${i + 1}. 역할`,
      choiceOf(row.role),
      (v) => {
        const cur = readRows(node);
        if (v === DELETE) cur.splice(i, 1);
        else if (cur[i]) cur[i].role = keyOf(v);
        writeRows(node, cur);
        rebuild(node);
      },
      { values: CHOICES.concat([DELETE]), serialize: false }
    );
    combo[TAG] = true;

    // The name MUST be unique per row. Two widgets sharing a name get bound to the
    // same state by the Vue-based node renderer, which made every row's picture
    // number change together.
    const num = node.addWidget(
      "number",
      `　　${i + 1} └ 이미지 번호`,
      row.n,
      (v) => {
        const cur = readRows(node);
        if (cur[i]) cur[i].n = Math.max(1, Math.min(9, Math.round(v)));
        writeRows(node, cur);
        // No rebuild here — the row order is unchanged, so the closures stay valid
        // and the widget keeps focus while you drag the value.
      },
      { min: 1, max: 9, step: 10, precision: 0, serialize: false }
    );
    num[TAG] = true;
  });
}

function rebuild(node) {
  try {
    clearRowWidgets(node);
    const rows = readRows(node);
    addRowWidgets(node, rows);
    // Grow to fit, but never shrink a node the user has widened by hand.
    const want = node.computeSize();
    node.setSize([
      Math.max(node.size ? node.size[0] : 0, want[0]),
      Math.max(node.size ? node.size[1] : 0, want[1]),
    ]);
    node.setDirtyCanvas(true, true);
  } catch (e) {
    console.error("[MMH3] picture_roles rebuild failed:", e);
  }
}

function setup(node) {
  try {
    if (!textWidget(node) || node.__mmh3RolesReady) return;
    node.__mmh3RolesReady = true;
    // onConfigure can run setup() again on a node that already has buttons.
    node.widgets = (node.widgets || []).filter((w) => !w[TAG_BTN] && !w[TAG]);

    const mkButton = (label, fn) => {
      const b = node.addWidget("button", label, null, fn);
      b.serialize = false;
      if (b.options) b.options.serialize = false;
      b[TAG_BTN] = true;
      return b;
    };

    mkButton("＋  역할 추가", () => {
      const rows = readRows(node);
      const used = new Set(rows.map((r) => r.n));
      let next = 1;
      while (used.has(next) && next < 9) next += 1;
      rows.push({ n: next, role: "character", note: "" });
      writeRows(node, rows);
      rebuild(node);
    });

    mkButton("－  마지막 행 삭제", () => {
      const rows = readRows(node);
      if (!rows.length) return;
      rows.pop();
      writeRows(node, rows);
      rebuild(node);
    });

    mkButton("⌫  전체 지우기", () => {
      writeRows(node, []);
      rebuild(node);
    });

    rebuild(node);
  } catch (e) {
    console.error("[MMH3] picture_roles setup failed:", e);
  }
}

app.registerExtension({
  name: "mmh3.picture_roles",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE) return;

    const created = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = created ? created.apply(this, arguments) : undefined;
      setup(this);
      return r;
    };

    const configured = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const r = configured ? configured.apply(this, arguments) : undefined;
      // Widget values are restored by now — rebuild the rows from the text field.
      setTimeout(() => {
        this.__mmh3RolesReady = false;
        setup(this);
      }, 0);
      return r;
    };
  },
});
