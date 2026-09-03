import { app } from "../../scripts/app.js";

// Shot-card editor for MMH3_ShotBuilder.
//
// The cards are a CUSTOM WIDGET, not onDrawForeground. LiteGraph lays custom widgets out
// with the ordinary ones and hands draw() the y it assigned, so the cards can never paint
// over the dropdowns above them — which is exactly what went wrong when this was drawn as
// a node overlay.
//
// State lives in the hidden `shots_data` string widget as JSON. Dropdown lists and their
// Korean explanations come from /mmh3/shotcards/vocab so they cannot drift from the
// sentences Python builds.

const FIELDS = [
  { key: "size",      label: "사이즈" },
  { key: "shot_type", label: "샷타입" },
  { key: "angle",     label: "앵글" },
  { key: "facing",    label: "방향" },
  { key: "viewpoint", label: "시점" },
  { key: "motion",    label: "모션" },
  { key: "amp",       label: "폭" },
  { key: "speed",     label: "속도" },
];
const COLS = 4;
const MIN_W = 640;

const PAD = 8;
const ADD = 26;
const HEAD = 24;
const ROW = 26;
// 두 줄입니다: '내용'(장소·의상·표정)과 '추가 동작'(행위 위에 겹치는 동작).
// 한 칸일 때는 규칙도 하나뿐이라, 장면을 지키려 하면 동작이 자세를 흔들고
// 자세를 지키려 하면 사용자가 쓴 동작이 버려졌습니다.
const TEXT_ROW = 26;
const TEXT = TEXT_ROW * 2 + 6;
const LINE_H = 17;        // 대사 한 줄
const DLG_BAR = 16;       // [+ 대사] 줄
const SPK_W = 132;        // 대사 줄의 화자 칸
const AT_W  = 46;         // 대사 줄의 시각 칸
const ACT_BAR = 16;       // [+ 행위] 줄
const ACT_H = 17;         // 행위 한 줄
const ACT_W = 118;        // 행위 이름 칸
const SLOT_W = 108;       // 참여자 칸
const MOVER_W = 74;       // 무버 칸

// 행위는 같은 시각이면 동시에 일어납니다 — 대사 줄과 의미가 반대입니다.
function actsOf(shot) {
  const ls = Array.isArray(shot?.acts) ? shot.acts.filter(l => l && typeof l === "object") : [];
  return ls.filter(l => (l.act || "").trim());
}
const actRow = k => (rowsOf("act").find(r => r.key === (k || "")) || {});
const posLabel = k => (rowsOf("act_pos").find(r => r.key === (k || "")) || {}).ko || "";
// 빈 칸에 "—" 만 그리면 어느 쪽이 어느 역할인지 볼 방법이 없습니다. 행위마다 두 칸의
// 뜻이 다르고(받는/하는, 위/아래, 제공/움직이는) 성별로 못 박을 수도 없어서 — 후타나리
// 같은 구성이 막힙니다 — 칸 이름 자체를 흐리게 띄웁니다. 고르면 인물 이름으로 바뀌고,
// 비어 있으면 "받는 쪽" 처럼 그 자리가 무엇을 담는 칸인지 그대로 보입니다.
function slotText(who, pos, slotName) {
  if (!who) return slotName ? `▸ ${slotName}` : "—";
  const t = targetChoices().find(o => o.v === who);
  const base = t ? t.ko : who;
  const p = posLabel(pos);
  return p && pos ? `${base} · ${p}` : base;
}

// 대사가 늘면 카드도 늘어납니다. 한 칸에 여러 화자를 몰아넣으면 순서를 모델이
// 지어내고, 그게 "Simultaneously, <Subject 2> says" 로 나옵니다.
function linesOf(shot) {
  const ls = Array.isArray(shot?.lines) ? shot.lines.filter(l => l && typeof l === "object") : [];
  if (ls.length) return ls;
  const legacy = (shot?.dialogue || "").trim();
  return legacy ? [{ who: "", text: legacy }] : [];
}
const actsH = s => ACT_BAR + actsOf(s).length * ACT_H;
const cardH = s => HEAD + ROW * 2 + TEXT + actsH(s)
                 + DLG_BAR + linesOf(s).length * LINE_H + 8;
const cardsH = shots => shots.reduce((a, s) => a + cardH(s), 0);

const REF_MAX = 9;
const REF_PER_ROW = 5;
const REF_LABEL_H = 15;
const REF_ROW_H = 19;
const refsH = n => REF_LABEL_H
  + Math.ceil(Math.max(1, n) / Math.min(Math.max(1, n), REF_PER_ROW)) * REF_ROW_H + 4;

let VOCAB = null, pending = null;
function loadVocab() {
  if (VOCAB) return Promise.resolve(VOCAB);
  if (!pending) {
    pending = fetch("/mmh3/shotcards/vocab").then(r => r.json())
      .then(v => { VOCAB = v; app.graph?.setDirtyCanvas(true); return v; })
      .catch(e => { console.warn("[MMH3] vocab load failed", e); return null; });
  }
  return pending;
}
const rowsOf = f => (VOCAB && VOCAB[f]) || [];
const rowOf = (f, k) => rowsOf(f).find(r => r.key === (k || "")) || {};
const labelOf = (f, k) => rowOf(f, k).ko || "—";
const tipOf = (f, k) => rowOf(f, k).tip || "";
const menuFor = f => rowsOf(f).map(r => ({ v: r.key, ko: r.ko, tip: r.tip }));

function blankShot() {
  return { text: "", viewpoint: "", vp_target: "", size: "", angle: "", facing: "",
           shot_type: "", motion: "", amp: "", speed: "", at: null, transition: "cut",
           extra: "", acts: [], lines: [] };
}

const dataWidget = n => n.widgets?.find(w => w.name === "shots_data");

function readData(node) {
  try {
    const d = JSON.parse(dataWidget(node)?.value || "{}");
    const shots = Array.isArray(d) ? d : d.shots;
    const refs = (d && d.refs) || [];
    return {
      shots: Array.isArray(shots) && shots.length ? shots : [blankShot()],
      refs: Array.isArray(refs) && refs.length ? refs : [1, 2, 3].map(n => ({ n, role: "" })),
    };
  } catch {
    return { shots: [blankShot()], refs: [1, 2, 3].map(n => ({ n, role: "" })) };
  }
}

function writeData(node, shots, refs) {
  const w = dataWidget(node);
  if (w) w.value = JSON.stringify({ version: 1, shots, refs });
  // 높이만 다시 잡고 폭은 사용자가 늘린 값을 유지합니다. size[0] 을 직접 대입하지 않고
  // setSize 로 넘겨야 must_not 같은 DOM 위젯도 같은 폭으로 다시 배치됩니다.
  node.properties = node.properties || {};
  const keep = Math.max(node.size[0], MIN_W);
  node.properties.mmh3_width = keep;
  const sz = node.computeSize();
  node.setSize([Math.max(sz[0], keep), sz[1]]);
  node.setDirtyCanvas(true, true);
}

function targetChoices() {
  const out = [{ v: "", ko: "— 대상 없음", tip: "시점의 주인을 정하지 않습니다." }];
  for (let i = 1; i <= REF_MAX; i++)
    out.push({ v: `pic:${i}`, ko: `이미지 ${i}의 인물`,
               tip: `레퍼런스 이미지 ${i} 에 있는 인물이 시점의 주인입니다.` });
  out.push({ v: "man", ko: "이 샷의 남자",
             tip: "행위에 참여하는 남자입니다. 레퍼런스 이미지에 없어도 됩니다." });
  out.push({ v: "woman", ko: "이 샷의 여자",
             tip: "행위에 참여하는 여자입니다. 레퍼런스 이미지에 없어도 됩니다." });
  out.push({ v: "third", ko: "지켜보는 제3자",
             tip: "행위에 참여하지 않고 옆에서 보고만 있는 인물입니다." });
  return out;
}

// 라벨 옆에 설명을 붙여 고르는 순간 무슨 기능인지 보이게 합니다.
// title 은 참여자 메뉴에서 "지금 고르는 칸이 어느 역할인지"(받는 쪽 / 하는 쪽 ...)를
// 머리에 띄우는 데 씁니다. 행위마다 두 칸의 뜻이 달라서, 메뉴만 봐서는 어느 쪽을
// 고르는 중인지 알 수 없었습니다.
function menu(e, items, onPick, title) {
  const shown = items.map(i => i.tip ? `${i.ko}  —  ${i.tip}` : i.ko);
  new LiteGraph.ContextMenu(shown, {
    event: e, scale: 1.05, title: title || undefined,
    callback: picked => {
      const idx = shown.indexOf(picked);
      if (idx >= 0) onPick(items[idx].v);
    },
  });
}

// 글자 수가 아니라 실제 폭으로 자릅니다. 한글은 5.6px 가정의 두 배 가까이 넓어서
// 글자 수로 자르면 레퍼런스 칸끼리 글자가 겹쳐 찍힙니다.
const clip = (ctx, s, px) => {
  s = String(s ?? "");
  if (px <= 0 || !s) return "";
  if (ctx.measureText(s).width <= px) return s;
  let lo = 0, hi = s.length;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (ctx.measureText(s.slice(0, mid) + "…").width <= px) lo = mid; else hi = mid - 1;
  }
  return lo ? s.slice(0, lo) + "…" : "";
};

// ---------------------------------------------------------------- 인라인 편집
function editInline(node, wx, wy, w, h, value, multiline, onDone) {
  let sx = null, sy = null, sw = Math.max(220, w), sh = Math.max(26, h), fs = 13;
  try {
    const cv = app.canvas?.canvas, ds = app.canvas?.ds;
    if (cv && ds && ds.offset && typeof ds.scale === "number") {
      const rect = cv.getBoundingClientRect();
      // ds 는 캔버스 백버퍼 좌표를 줍니다. 디스플레이 배율이 100% 가 아니면
      // 백버퍼가 CSS 픽셀보다 크므로 그 비율만큼 되돌려야 제자리에 뜹니다.
      const dpr = (cv.width && rect.width) ? (rect.width / cv.width) : 1;
      const k = (ds.scale || 1) * dpr;
      sx = rect.left + (node.pos[0] + wx + ds.offset[0]) * k;
      sy = rect.top + (node.pos[1] + wy + ds.offset[1]) * k;
      sw = Math.max(220, w * k); sh = Math.max(26, h * k);
      fs = Math.min(20, Math.max(12, 12 * k));
    }
  } catch (err) { console.warn("[MMH3] inline editor transform failed", err); }

  const vw = window.innerWidth, vh = window.innerHeight;
  if (sx === null || !isFinite(sx) || !isFinite(sy) ||
      sx < 0 || sy < 0 || sx > vw - 40 || sy > vh - 40) {
    sw = Math.min(560, vw - 80);
    sh = Math.max(sh, multiline ? 120 : 32);
    sx = (vw - sw) / 2; sy = Math.max(60, vh * 0.3);
  }
  sw = Math.min(sw, vw - sx - 16);
  sh = Math.min(sh, vh - sy - 16);

  const el = document.createElement(multiline ? "textarea" : "input");
  el.value = value || "";
  el.spellcheck = false;
  Object.assign(el.style, {
    position: "fixed", left: `${sx}px`, top: `${sy}px`,
    width: `${sw}px`, height: `${sh}px`, zIndex: 99999,
    background: "#0d0d0d", color: "#f0f0f0", border: "2px solid #00FFCC",
    borderRadius: "4px", outline: "none", boxShadow: "0 6px 24px #000c",
    font: `${fs}px sans-serif`, padding: "4px 6px",
    resize: multiline ? "vertical" : "none", lineHeight: "1.4",
  });
  document.body.appendChild(el);

  let closed = false, armed = false;
  const close = commit => {
    if (closed) return;
    closed = true;
    const v = el.value;
    el.remove();
    if (commit) onDone(v);
  };
  // 이 클릭을 만든 pointer 이벤트가 아직 흐르는 중이라 캔버스가 포커스를 도로 가져갑니다.
  setTimeout(() => {
    el.focus({ preventScroll: true });
    el.select?.();
    setTimeout(() => { armed = true; }, 120);
  }, 0);
  el.addEventListener("blur", () => { armed ? close(true) : setTimeout(() => el.focus(), 0); });
  el.addEventListener("keydown", ev => {
    ev.stopPropagation();
    if (ev.key === "Escape") { ev.preventDefault(); armed = true; close(false); }
    if (ev.key === "Enter" && (!multiline || ev.ctrlKey || ev.metaKey)) {
      ev.preventDefault(); armed = true; close(true);
    }
  });
  ["pointerdown", "mousedown", "click", "wheel"].forEach(t =>
    el.addEventListener(t, ev => ev.stopPropagation()));
}

// ---------------------------------------------------------------- 커스텀 위젯
class ShotCardsWidget {
  constructor() {
    this.type = "custom";
    this.name = "shot_cards";
    this.options = { serialize: false };
    this.last_y = 0;
    this.tip = "";
    this.tipAt = null;
  }

  computeSize(width) {
    const node = this.node;
    if (!node) return [width, 120];
    const d = readData(node);
    return [width, refsH(d.refs.length) + ADD + cardsH(d.shots) + 8];
  }

  // 그리기와 클릭이 같은 함수를 쓰므로 위치가 어긋나지 않습니다.
  hit(node, x, ly) {
    const { shots, refs } = readData(node);
    // draw() 가 받는 값은 노드 폭이 아니라 위젯 폭입니다. 여기서 node.size[0] 을 쓰면
    // 여백만큼 어긋나 클릭이 옆 칸으로 떨어집니다.
    const W = this.lastW || node.size[0];
    const rh = refsH(refs.length);
    if (ly < rh) {
      if (ly < REF_LABEL_H) {
        if (x > W - PAD - 22) return { zone: "refbtn", which: "del" };
        if (x > W - PAD - 44) return { zone: "refbtn", which: "add" };
        return { zone: "refbar" };
      }
      const r = Math.floor((ly - REF_LABEL_H) / REF_ROW_H);
      const perRow = Math.min(Math.max(1, refs.length), REF_PER_ROW);
      const cw = (W - PAD * 2) / perRow;
      const c = Math.floor((x - PAD) / cw);
      const i = r * perRow + c;
      if (c >= 0 && c < perRow && i >= 0 && i < refs.length) return { zone: "ref", i };
      return { zone: "refbar" };
    }
    const TOP = rh + ADD;
    if (ly < TOP) return (x > PAD && x < PAD + 100) ? { zone: "add" } : { zone: "addbar" };
    let top = TOP;
    for (let i = 0; i < shots.length; i++) {
      const h = cardH(shots[i]);
      if (ly < top || ly > top + h) { top += h; continue; }
      const ry = ly - top;
      if (ry < HEAD) return { zone: "head", i, top };
      if (ry < HEAD + ROW * 2) {
        const r = Math.floor((ry - HEAD) / ROW);
        const cw = (W - PAD * 2) / COLS;
        const c = Math.min(COLS - 1, Math.max(0, Math.floor((x - PAD) / cw)));
        return { zone: "grid", i, r, c, idx: r * COLS + c, top };
      }
      if (ry < HEAD + ROW * 2 + TEXT) {
        const tr = ry - (HEAD + ROW * 2);
        return { zone: tr < TEXT_ROW ? "text" : "extra", i, top };
      }

      const ay = ry - (HEAD + ROW * 2 + TEXT);
      const acts = actsOf(shots[i]);
      if (ay < actsH(shots[i])) {
        if (ay < ACT_BAR)
          return (x > PAD && x < PAD + 78) ? { zone: "actadd", i, top }
                                           : { zone: "actbar", i, top };
        const ai = Math.floor((ay - ACT_BAR) / ACT_H);
        if (ai >= 0 && ai < acts.length) {
          let part = "act";
          if (x < PAD + AT_W) part = "at";
          else if (x < PAD + AT_W + ACT_W) part = "act";
          else if (x < PAD + AT_W + ACT_W + SLOT_W) part = "a";
          else if (x < PAD + AT_W + ACT_W + SLOT_W * 2) part = "b";
          else if (x > W - PAD - 16) part = "del";
          else part = "mover";
          return { zone: "actline", i, ai, part, top };
        }
        return { zone: "actbar", i, top };
      }

      const dy = ry - (HEAD + ROW * 2 + TEXT + actsH(shots[i]));
      if (dy < DLG_BAR)
        return (x > PAD && x < PAD + 78) ? { zone: "dlgadd", i, top }
                                         : { zone: "dlgbar", i, top };
      const li = Math.floor((dy - DLG_BAR) / LINE_H);
      if (li >= 0 && li < linesOf(shots[i]).length) {
        const part = x < PAD + AT_W ? "at"
                   : x < PAD + AT_W + SPK_W ? "who"
                   : (x > W - PAD - 16 ? "del" : "text");
        return { zone: "dlgline", i, li, part, top };
      }
      return { zone: "dlgbar", i, top };
    }
    return null;
  }

  draw(ctx, node, W, posY, _H) {
    this.node = node;
    this.last_y = posY;
    this.lastW = W;
    const { shots, refs } = readData(node);
    const y0 = posY;

    // ---- 레퍼런스 용도
    ctx.fillStyle = "#6a6a6a";
    ctx.font = "9px sans-serif";
    ctx.fillText("레퍼런스 이미지 용도", PAD, y0 + 10);
    ctx.font = "bold 13px 'Courier New',monospace";
    ctx.textAlign = "center";
    ctx.fillStyle = refs.length < REF_MAX ? "#00FFCC" : "#333";
    ctx.fillText("+", W - PAD - 33, y0 + 12);
    ctx.fillStyle = refs.length > 1 ? "#f4433699" : "#333";
    ctx.fillText("−", W - PAD - 11, y0 + 12);
    ctx.textAlign = "left";

    const perRow = Math.min(Math.max(1, refs.length), REF_PER_ROW);
    const rw = (W - PAD * 2) / perRow;
    refs.forEach((r, i) => {
      const row = Math.floor(i / perRow), col = i % perRow;
      const isFrame = r.role === "first_frame" || r.role === "last_frame";
      ctx.fillStyle = isFrame ? "#FF9800" : (r.role ? "#00FFCC" : "#4a4a4a");
      ctx.font = "10px sans-serif";
      ctx.fillText(clip(ctx, `${r.n}: ${labelOf("ref_role", r.role)}`, rw - 8),
                   PAD + col * rw, y0 + REF_LABEL_H + row * REF_ROW_H + 13);
    });

    // ---- [+ 샷 추가]
    const rh = refsH(refs.length);
    ctx.fillStyle = "#2a2a2a";
    ctx.strokeStyle = "#00FFCC66";
    ctx.lineWidth = 0.6;
    ctx.beginPath(); ctx.roundRect(PAD, y0 + rh + 3, 100, 19, 3); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#00FFCC";
    ctx.font = "bold 11px 'Courier New',monospace";
    ctx.textAlign = "center";
    ctx.fillText("+ 샷 추가", PAD + 50, y0 + rh + 17);
    ctx.textAlign = "left";
    if (!VOCAB) {
      ctx.fillStyle = "#888"; ctx.font = "9px sans-serif";
      ctx.fillText("어휘 불러오는 중…", PAD + 112, y0 + rh + 17);
    }

    // ---- 카드
    const TOP = rh + ADD;
    const cw = (W - PAD * 2) / COLS;
    let cy = y0 + TOP;
    shots.forEach((s, i) => {
      const y = cy, h = cardH(s);
      cy += h;
      ctx.fillStyle = i % 2 ? "#1d1d1d" : "#232323";
      ctx.fillRect(PAD - 4, y, W - PAD * 2 + 8, h - 5);

      ctx.fillStyle = "#00FFCC";
      ctx.font = "bold 11px 'Courier New',monospace";
      ctx.fillText(`샷 ${i + 1}`, PAD, y + 15);
      if (i > 0) {
        ctx.fillStyle = "#F5A623"; ctx.font = "10px 'Courier New',monospace";
        const at = (s.at === null || s.at === undefined || s.at === "") ? "시각?" : `${s.at}초`;
        ctx.fillText(at, PAD + 52, y + 15);
        ctx.fillStyle = "#9aa0a6";
        ctx.fillText(labelOf("transition", s.transition || "cut"), PAD + 110, y + 15);
      }
      if (shots.length > 1) {
        ctx.fillStyle = "#f44336aa"; ctx.font = "bold 13px 'Courier New',monospace";
        ctx.textAlign = "right"; ctx.fillText("×", W - PAD, y + 15); ctx.textAlign = "left";
      }

      FIELDS.forEach((f, idx) => {
        const r = Math.floor(idx / COLS), c = idx % COLS;
        const x = PAD + c * cw, yy = y + HEAD + r * ROW;
        ctx.fillStyle = "#6a6a6a"; ctx.font = "8px sans-serif";
        ctx.fillText(f.label, x, yy + 9);
        ctx.fillStyle = s[f.key] ? "#e2e2e2" : "#555";
        ctx.font = "10px sans-serif";
        ctx.fillText(clip(ctx, labelOf(f.key, s[f.key]), cw), x, yy + 21);
      });

      if (s.viewpoint && s.viewpoint !== "objective") {
        const x = PAD + 3 * cw, yy = y + HEAD + ROW;
        ctx.fillStyle = "#FF9800"; ctx.font = "8px sans-serif";
        ctx.fillText("시점 주인", x, yy + 9);
        const t = targetChoices().find(o => o.v === (s.vp_target || ""));
        ctx.fillStyle = s.vp_target ? "#FF9800" : "#f44336";
        ctx.font = "10px sans-serif";
        ctx.fillText(clip(ctx, t ? t.ko : "— 대상 없음", cw), x, yy + 21);
      }

      const ty = y + HEAD + ROW * 2;
      const drawBox = (byy, lab, col, val, ph) => {
        ctx.fillStyle = "#141414";
        ctx.fillRect(PAD, byy, W - PAD * 2, TEXT_ROW - 4);
        ctx.font = "bold 9px 'Courier New',monospace";
        ctx.fillStyle = col;
        ctx.fillText(lab, PAD + 5, byy + 14);
        ctx.font = "10px sans-serif";
        ctx.fillStyle = val ? "#dcdcdc" : "#555";
        ctx.fillText(clip(ctx, val || ph, W - PAD * 2 - 70), PAD + 62, byy + 14);
      };
      drawBox(ty, "내용", "#8ecbff", s.text,
              "클릭해서 장소·의상·표정·분위기를 한국어로 쓰세요");
      drawBox(ty + TEXT_ROW, "추가동작", "#ff9ec4", s.extra,
              "행위가 안 쓰는 부위로 할 동작 (손·팔·시선·표정 …)");

      // [+ 행위]
      const ay = ty + TEXT;
      ctx.fillStyle = "#E91E6344";
      ctx.beginPath(); ctx.roundRect(PAD, ay + 1, 78, 13, 2); ctx.fill();
      ctx.fillStyle = "#ff9ec4";
      ctx.font = "bold 9px 'Courier New',monospace";
      ctx.textAlign = "center";
      ctx.fillText("+ 행위", PAD + 39, ay + 11);
      ctx.textAlign = "left";
      const al = actsOf(s);
      if (!al.length) {
        ctx.fillStyle = "#3a3a3a"; ctx.font = "9px sans-serif";
        ctx.fillText("같은 시각의 행위는 동시에 일어납니다.", PAD + 86, ay + 11);
      }
      al.forEach((an, ai) => {
        const ry = ay + ACT_BAR + ai * ACT_H;
        ctx.fillStyle = ai % 2 ? "#1a1416" : "#1d171a";
        ctx.fillRect(PAD, ry, W - PAD * 2, ACT_H - 2);
        ctx.font = "9px sans-serif";
        const hasAt = an.at !== undefined && an.at !== null && an.at !== "";
        ctx.fillStyle = hasAt ? "#00FFCC" : "#3a3a3a";
        ctx.fillText(clip(ctx, hasAt ? `${an.at}s` : `${ai + 1})`, AT_W - 6), PAD + 4, ry + 12);
        const ar = actRow(an.act);
        ctx.fillStyle = "#E91E63";
        ctx.fillText(clip(ctx, ar.ko || "행위?", ACT_W - 6), PAD + AT_W, ry + 12);
        const x1 = PAD + AT_W + ACT_W, x2 = x1 + SLOT_W;
        // 채워지면 주황, 비어 있으면 흐린 회색으로 칸 이름을 보여줍니다. 빨강으로
        // 비명을 지르는 것보다, 그 자리가 무엇인지 읽히는 편이 실제로 도움이 됩니다.
        ctx.fillStyle = an.a ? "#FF9800" : "#6b5b62";
        ctx.fillText(clip(ctx, slotText(an.a, an.a_pos, ar.slot_a), SLOT_W - 6), x1, ry + 12);
        if (ar.slot_b) {
          ctx.fillStyle = an.b ? "#FF9800" : "#6b5b62";
          ctx.fillText(clip(ctx, slotText(an.b, an.b_pos, ar.slot_b), SLOT_W - 6), x2, ry + 12);
        }
        ctx.fillStyle = an.mover ? "#8ecbff" : "#3a3a3a";
        ctx.fillText(clip(ctx, an.mover ? labelOf("mover", an.mover) : "기본",
                          MOVER_W - 6), x2 + SLOT_W, ry + 12);
        ctx.fillStyle = "#f4433699";
        ctx.font = "bold 11px 'Courier New',monospace";
        ctx.textAlign = "right"; ctx.fillText("×", W - PAD - 3, ry + 12); ctx.textAlign = "left";
      });

      // [+ 대사]
      const by = ty + TEXT + actsH(s);
      ctx.fillStyle = "#2196F344";
      ctx.beginPath(); ctx.roundRect(PAD, by + 1, 78, 13, 2); ctx.fill();
      ctx.fillStyle = "#8ecbff";
      ctx.font = "bold 9px 'Courier New',monospace";
      ctx.textAlign = "center";
      ctx.fillText("+ 대사", PAD + 39, by + 11);
      ctx.textAlign = "left";
      const dl = linesOf(s);
      if (!dl.length) {
        ctx.fillStyle = "#3a3a3a"; ctx.font = "9px sans-serif";
        ctx.fillText("대사가 없습니다. 화자마다 한 줄씩 추가하세요.", PAD + 86, by + 11);
      }

      // 대사 줄: [화자 ▾] [대사] [×]
      dl.forEach((ln, li) => {
        const ry = by + DLG_BAR + li * LINE_H;
        ctx.fillStyle = li % 2 ? "#161616" : "#191919";
        ctx.fillRect(PAD, ry, W - PAD * 2, LINE_H - 2);
        ctx.font = "9px sans-serif";
        const hasAt = ln.at !== undefined && ln.at !== null && ln.at !== "";
        ctx.fillStyle = hasAt ? "#00FFCC" : "#3a3a3a";
        ctx.fillText(clip(ctx, hasAt ? `${ln.at}s` : `${li + 1})`, AT_W - 6), PAD + 4, ry + 12);
        const t = targetChoices().find(o => o.v === (ln.who || ""));
        ctx.fillStyle = ln.who ? "#FF9800" : "#f44336";
        ctx.fillText(clip(ctx, t ? t.ko : "화자?", SPK_W - 6), PAD + AT_W, ry + 12);
        ctx.fillStyle = ln.text ? "#2196F3" : "#3a3a3a";
        ctx.fillText(clip(ctx, ln.text || "클릭해서 대사를 쓰세요",
                          W - PAD * 2 - AT_W - SPK_W - 22), PAD + AT_W + SPK_W, ry + 12);
        ctx.fillStyle = "#f4433699";
        ctx.font = "bold 11px 'Courier New',monospace";
        ctx.textAlign = "right"; ctx.fillText("×", W - PAD - 3, ry + 12); ctx.textAlign = "left";
      });
    });

    // ---- 커서 옆 설명
    if (this.tip && this.tipAt) {
      const [tx, tyy] = this.tipAt;
      ctx.font = "10px sans-serif";
      const lines = [];
      let cur = "";
      for (const ch of this.tip) {
        cur += ch;
        if (ctx.measureText(cur).width > 240) { lines.push(cur); cur = ""; }
      }
      if (cur) lines.push(cur);
      const bh = lines.length * 14 + 8;
      const bx = Math.min(tx + 14, W - 260), by = tyy + 14;
      ctx.fillStyle = "#000000ee";
      ctx.strokeStyle = "#00FFCC55"; ctx.lineWidth = 0.6;
      ctx.beginPath(); ctx.roundRect(bx, by, 252, bh, 4); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#d8f8f0";
      lines.forEach((ln, k) => ctx.fillText(ln, bx + 7, by + 15 + k * 14));
    }
  }

  mouse(event, pos, node) {
    if (event.type !== "pointerdown" && event.type !== "mousedown") {
      if (event.type === "pointermove" || event.type === "mousemove") {
        const c = this.hit(node, pos[0], pos[1] - this.last_y);
        const t = this.tipFor(node, c);
        if (t !== this.tip) { this.tip = t; node.setDirtyCanvas(true); }
        this.tipAt = [pos[0], pos[1] - this.last_y];
      }
      return false;
    }
    const ly = pos[1] - this.last_y;
    const cell = this.hit(node, pos[0], ly);
    if (!cell) return false;
    const { shots, refs } = readData(node);
    const W = this.lastW || node.size[0];   // draw() 와 같은 위젯 폭을 써야 어긋나지 않습니다

    if (cell.zone === "refbtn") {
      if (cell.which === "add" && refs.length < REF_MAX) {
        refs.push({ n: refs.length + 1, role: "" }); writeData(node, shots, refs);
      } else if (cell.which === "del" && refs.length > 1) {
        refs.pop(); writeData(node, shots, refs);
      }
      return true;
    }
    if (cell.zone === "ref") {
      loadVocab().then(() => menu(event, menuFor("ref_role"),
        v => { refs[cell.i].role = v; writeData(node, shots, refs); }));
      return true;
    }
    if (cell.zone === "add") { shots.push(blankShot()); writeData(node, shots, refs); return true; }
    if (cell.zone === "refbar" || cell.zone === "addbar") return true;

    const s = shots[cell.i];
    if (cell.zone === "head") {
      if (shots.length > 1 && pos[0] > W - PAD - 16) {
        shots.splice(cell.i, 1); writeData(node, shots, refs); return true;
      }
      if (cell.i > 0 && pos[0] > PAD + 48 && pos[0] < PAD + 104) {
        editInline(node, PAD + 48, this.last_y + cell.top + 3, 52, 16, s.at ?? "", false,
          v => { s.at = v.trim() === "" ? null : parseFloat(v); writeData(node, shots, refs); });
      } else if (cell.i > 0 && pos[0] >= PAD + 104) {
        loadVocab().then(() => menu(event, menuFor("transition"),
          v => { s.transition = v; writeData(node, shots, refs); }));
      }
      return true;
    }
    if (cell.zone === "grid") {
      if (cell.r === 1 && cell.c === 3 && s.viewpoint && s.viewpoint !== "objective") {
        menu(event, targetChoices(), v => { s.vp_target = v; writeData(node, shots, refs); });
        return true;
      }
      const f = FIELDS[cell.idx];
      if (f) {
        loadVocab().then(() => menu(event, menuFor(f.key), v => {
          s[f.key] = v;
          if (f.key === "viewpoint" && (!v || v === "objective")) s.vp_target = "";
          writeData(node, shots, refs);
        }));
      }
      return true;
    }
    const ty = this.last_y + cell.top + HEAD + ROW * 2;

    if (cell.zone === "actadd") {
      s.acts = actsOf(s).slice();
      // 참가자를 비운 채로 시작하면 브리프에 <사람 A>/<사람 B> 라는 신원 없는
      // 자리표시자가 나갑니다. 모델은 그걸 순번대로 배정해서, 실제로 남녀가 통째로
      // 뒤집힌 결과가 나왔습니다. 직전 줄에서 물려받으면 첫 줄만 고르면 됩니다.
      const prev = s.acts.length ? s.acts[s.acts.length - 1] : null;
      // 이 샷의 다른 줄도 비어 있으면, 앞 샷에서라도 물려받습니다.
      let seed = prev;
      if (!seed || (!seed.a && !seed.b)) {
        for (let k = shots.indexOf(s) - 1; k >= 0 && (!seed || (!seed.a && !seed.b)); k--) {
          const pl = actsOf(shots[k]);
          if (pl.length) seed = pl[pl.length - 1];
        }
      }
      s.acts.push({ at: null, act: "missionary",
                    a: (seed && seed.a) || "", a_pos: "",
                    b: (seed && seed.b) || "", b_pos: "", mover: "" });
      writeData(node, shots, refs);
      return true;
    }
    if (cell.zone === "actbar") return true;

    if (cell.zone === "actline") {
      s.acts = actsOf(s).slice();
      const an = s.acts[cell.ai];
      if (!an) return true;
      const ry = ty + TEXT + ACT_BAR + cell.ai * ACT_H;
      if (cell.part === "del") {
        s.acts.splice(cell.ai, 1); writeData(node, shots, refs);
      } else if (cell.part === "at") {
        editInline(node, PAD, ry, AT_W + 40, ACT_H, an.at ?? "", false, v => {
          const f = parseFloat(String(v).trim());
          an.at = (String(v).trim() === "" || !isFinite(f) || f < 0) ? null : f;
          writeData(node, shots, refs);
        });
      } else if (cell.part === "act") {
        loadVocab().then(() => menu(event, menuFor("act").filter(o => o.v), v => {
          an.act = v; writeData(node, shots, refs);
        }));
      } else if (cell.part === "mover") {
        loadVocab().then(() => menu(event, menuFor("mover"), v => {
          an.mover = v; writeData(node, shots, refs);
        }));
      } else {
        // 참여자 → 고른 뒤 곧바로 화면 위치를 묻습니다 (칸 하나, 2단 선택)
        const kw = cell.part === "a" ? "a" : "b";
        const ar = actRow(an.act);
        if (kw === "b" && !ar.slot_b) return true;
        const slotName = (kw === "a" ? ar.slot_a : ar.slot_b) || "참여자";
        menu(event, targetChoices(), v => {
          an[kw] = v;
          writeData(node, shots, refs);
          if (!v) { an[kw + "_pos"] = ""; writeData(node, shots, refs); return; }
          loadVocab().then(() => menu(event, menuFor("act_pos"), p => {
            an[kw + "_pos"] = p; writeData(node, shots, refs);
          }, `${ar.ko || "행위"} · ${slotName} 의 화면 위치`));
        }, `${ar.ko || "행위"} · ${slotName} 은 누구?`);
      }
      return true;
    }

    if (cell.zone === "actadd")
      return "이 샷에 행위를 한 줄 추가합니다. 같은 시각을 적은 줄은 동시에 일어납니다 — "
           + "3명 이상은 줄 두 개로 표현하세요.";
    if (cell.zone === "actline") {
      if (cell.part === "at") return "이 행위가 시작하는 시각(초). 같은 시각끼리는 동시입니다.";
      if (cell.part === "act") return "행위를 고릅니다. 이름과 함께 두 사람의 자세·누가 "
                                    + "움직이는지·방향이 영어 지시문으로 나갑니다.";
      if (cell.part === "mover") return "기본 무버를 바꿉니다. 비워두면 행위에 정해진 쪽이 "
                                      + "움직입니다.";
      if (cell.part === "del") return "이 행위 줄을 지웁니다.";
      return "참여자를 고르고, 이어서 화면 위치를 고릅니다. 몸의 위·아래는 행위가 이미 "
           + "정하므로 여기서는 프레임 안 위치만 정합니다.";
    }
    if (cell.zone === "actbar") return "";
    if (cell.zone === "dlgadd") {
      s.lines = linesOf(s).slice();
      s.lines.push({ who: "", text: "" });
      delete s.dialogue;                     // 옛 단일 문자열은 lines 로 흡수됩니다
      writeData(node, shots, refs);
      return true;
    }
    if (cell.zone === "dlgbar") return true;

    if (cell.zone === "dlgline") {
      s.lines = linesOf(s).slice();
      delete s.dialogue;
      const dlgTop = ty + TEXT + actsH(s);
      const ln = s.lines[cell.li];
      if (!ln) return true;
      if (cell.part === "del") {
        s.lines.splice(cell.li, 1);
        writeData(node, shots, refs);
      } else if (cell.part === "at") {
        const ry = dlgTop + DLG_BAR + cell.li * LINE_H;
        editInline(node, PAD, ry, AT_W + 40, LINE_H, ln.at ?? "", false, v => {
          const f = parseFloat(String(v).trim());
          ln.at = (String(v).trim() === "" || !isFinite(f) || f < 0) ? null : f;
          writeData(node, shots, refs);
        });
      } else if (cell.part === "who") {
        menu(event, targetChoices(), v => { ln.who = v; writeData(node, shots, refs); });
      } else {
        const ry = dlgTop + DLG_BAR + cell.li * LINE_H;
        editInline(node, PAD + AT_W + SPK_W, ry,
                   W - PAD * 2 - AT_W - SPK_W - 20, LINE_H, ln.text, false,
          v => { ln.text = v; writeData(node, shots, refs); });
      }
      return true;
    }

    if (cell.zone === "extra") {
      editInline(node, PAD, ty + TEXT_ROW, W - PAD * 2, TEXT_ROW - 4, s.extra || "", true,
        v => { s.extra = v; writeData(node, shots, refs); });
      return true;
    }
    editInline(node, PAD, ty, W - PAD * 2, TEXT_ROW - 4, s.text, true,
      v => { s.text = v; writeData(node, shots, refs); });
    return true;
  }

  tipFor(node, cell) {
    if (!cell) return "";
    const { shots, refs } = readData(node);
    if (cell.zone === "refbtn")
      return cell.which === "add"
        ? `레퍼런스 이미지를 하나 더 추가합니다 (최대 ${REF_MAX}장).`
        : "마지막 레퍼런스 이미지를 제거합니다.";
    if (cell.zone === "ref") {
      const r = refs[cell.i];
      return `이미지 ${r.n} 의 용도. ` + (tipOf("ref_role", r.role)
        || "클릭해서 고르세요. ★ 첫 프레임을 고르면 그 이미지가 0초 프레임이 됩니다.");
    }
    if (cell.zone === "add") return "샷을 하나 더 추가합니다. 2번째부터 전환 시각이 생깁니다.";
    const s = shots[cell.i];
    if (cell.zone === "head")
      return cell.i === 0 ? "첫 샷입니다. 전환 시각이 없습니다."
                          : "전환 시각과 전환 방식. × 는 이 샷을 지웁니다.";
    if (cell.zone === "grid") {
      if (cell.r === 1 && cell.c === 3 && s.viewpoint && s.viewpoint !== "objective")
        return "이 시점이 누구의 것인지 고릅니다.";
      const f = FIELDS[cell.idx];
      return f ? `${f.label} — ` + (tipOf(f.key, s[f.key]) || "클릭해서 고르세요.") : "";
    }
    if (cell.zone === "dlgadd")
      return "이 샷에 대사를 한 줄 더 추가합니다. 화자마다 한 줄씩 쓰세요 — "
           + "한 칸에 두 사람을 몰아넣으면 모델이 순서를 지어내고 동시 발화로 나옵니다.";
    if (cell.zone === "dlgline") {
      if (cell.part === "at")
        return "이 대사가 시작하는 시각(초)입니다. 비워두면 순서만 지킵니다. "
             + "값을 넣으면 컷 없이 같은 화면 안에서 그 시각에 말이 시작됩니다 — "
             + "컷을 넣으면 화면이 새로 그려지지만 이건 안 그렇습니다.";
      if (cell.part === "who") return "이 대사를 말하는 사람을 고릅니다. 오디오 레퍼런스와 "
                                    + "같은 이미지 번호를 고르면 목소리가 그 인물에 묶입니다.";
      if (cell.part === "del") return "이 대사 줄을 지웁니다.";
      return "대사 내용입니다. 번역되지 않고 그대로 들어갑니다. 언어는 위의 "
           + "dialogue_language 를 따릅니다.";
    }
    if (cell.zone === "dlgbar") return "";
    if (cell.zone === "text")
      return "장소·의상·표정·분위기. 이 칸은 행위·카메라보다 우선합니다. "
           + "여러 줄은 Ctrl+Enter 로 확정, Esc 는 취소.";
    if (cell.zone === "extra")
      return "행위 위에 겹치는 동작. 행위가 이미 쓰고 있는 신체 부위는 못 씁니다 — "
           + "기승위라면 손·팔·시선·표정이 비어 있습니다. 자세를 바꾸는 내용은 버려집니다.";
    return "";
  }
}

app.registerExtension({
  name: "MMH3.ShotBuilder",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "MMH3_ShotBuilder") return;

    // 폭을 기억하고 되살립니다. 프로토타입에 한 번만 감습니다 — onNodeCreated 안에서
    // 감으면 노드를 두 개 만들었을 때 자기 자신을 다시 감아 무한 재귀가 됩니다.
    const onRes = nodeType.prototype.onResize;
    nodeType.prototype.onResize = function (size) {
      onRes?.apply(this, arguments);
      this.properties = this.properties || {};
      if (size && size[0] > MIN_W) this.properties.mmh3_width = size[0];
    };

    // computeSize 는 "이 노드가 가질 수 있는 최소 크기" 로도 쓰입니다 — LiteGraph 가
    // 드래그 리사이즈를 여기에 대고 자릅니다. 그래서 기억한 폭을 여기에 섞으면 한 번
    // 키운 노드를 다시 줄일 수 없게 됩니다. 기억한 폭은 최소값이 아니라 복원값이므로,
    // 되살리는 일은 writeData 와 onConfigure 에서 명시적으로만 합니다.
    // 여기서는 카드 칸이 뭉개지지 않는 하한(MIN_W)만 지킵니다.
    const onComputeSize = nodeType.prototype.computeSize;
    nodeType.prototype.computeSize = function () {
      const sz = onComputeSize ? onComputeSize.apply(this, arguments) : [MIN_W, 200];
      sz[0] = Math.max(sz[0], MIN_W);
      return sz;
    };

    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      onCreated?.apply(this, arguments);
      loadVocab();
      const w = dataWidget(this);
      if (w) { w.draw = () => {}; w.computeSize = () => [0, -4]; }
      const cards = new ShotCardsWidget();
      cards.node = this;
      this.addCustomWidget(cards);
      this._cards = cards;
      this.size = this.computeSize();
      this.size[0] = Math.max(this.size[0], 640);
    };

    const onConf = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      onConf?.apply(this, arguments);
      if (this._cards) this._cards.node = this;
      // 저장돼 있던 폭을 기억값으로 삼습니다. 이게 없으면 이 기능이 생기기 전에 저장한
      // 워크플로우는 열 때마다 최소 폭으로 되돌아갑니다 — computeSize 가 기억값을 못 찾고
      // 위젯 최소 폭을 돌려주기 때문입니다.
      // 불러올 때는 저장된 폭이 무조건 이깁니다. 조건부로 두면 안 됩니다 — 노드가 만들어질
      // 때 onResize 가 자동 크기를 한 번 기록해 두기 때문에, 그 값이 저장본을 이겨버립니다.
      this.properties = this.properties || {};
      const savedW = (arguments[0] && arguments[0].size && arguments[0].size[0])
                     || (this.size && this.size[0]) || 0;
      if (savedW > MIN_W) this.properties.mmh3_width = savedW;
      const sz = this.computeSize();
      this.setSize([Math.max(sz[0], savedW || 0), sz[1]]);
    };

    nodeType.prototype.onMouseLeave = function () {
      if (this._cards?.tip) { this._cards.tip = ""; this.setDirtyCanvas(true); }
    };
  },
});
