// MiniMax H3 — 에셋 라이브러리 패널.
//
// 노드에는 버튼과 작은 미리보기만 둡니다. 실제 화면은 전체를 덮는 모달이고,
// 거기서 배우·의상·장소·소품·레이아웃을 썸네일로 훑어보고, 클릭 한 번으로
// 노드에 꽂고, 이름과 영어 설명을 그 자리에서 고칩니다.
//
// window.prompt / confirm 은 쓰지 않습니다 — 이름 짓기도 삭제 확인도 전부
// 화면 안에서 합니다.
//
// asset.json 이 유일한 사실입니다. 모든 동작은 /mmh3_library/ 로 POST 하고
// 새로 받아온 목록으로 다시 그립니다.

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

/* ------------------------------------------------------------------ CSS */

const CSS = `
.mmh3l-overlay{position:fixed;inset:0;z-index:10000;background:rgba(8,10,14,.66);
  display:flex;align-items:center;justify-content:center;backdrop-filter:blur(2px);}
.mmh3l-card{width:min(1180px,94vw);height:min(780px,90vh);background:#181a20;
  color:#e6e8ee;border:1px solid #2c303a;border-radius:12px;display:flex;
  flex-direction:column;overflow:hidden;box-shadow:0 24px 60px rgba(0,0,0,.55);
  font:13px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;}
.mmh3l-head{display:flex;align-items:center;gap:12px;padding:12px 16px;
  border-bottom:1px solid #2c303a;flex:none;}
.mmh3l-head h2{margin:0;font-size:15px;font-weight:600;letter-spacing:.2px;}
.mmh3l-head .sp{flex:1;}
.mmh3l-body{flex:1;display:flex;min-height:0;}
.mmh3l-side{width:150px;flex:none;border-right:1px solid #2c303a;padding:10px 0;
  overflow:auto;}
.mmh3l-kind{padding:7px 16px;cursor:pointer;color:#aab0bd;border-left:2px solid transparent;}
.mmh3l-kind:hover{background:#1f222a;color:#e6e8ee;}
.mmh3l-kind.on{background:#20242e;color:#fff;border-left-color:#5b8cff;}
.mmh3l-kind .n{float:right;color:#697084;font-size:11px;}
.mmh3l-main{flex:1;display:flex;min-width:0;}
.mmh3l-grid{flex:1;overflow:auto;padding:12px;display:grid;gap:10px;
  grid-template-columns:repeat(auto-fill,minmax(148px,1fr));align-content:start;}
.mmh3l-item{background:#20232b;border:1px solid #2c303a;border-radius:8px;
  overflow:hidden;cursor:pointer;position:relative;}
.mmh3l-item:hover{border-color:#5b8cff;}
.mmh3l-item.on{border-color:#5b8cff;box-shadow:0 0 0 1px #5b8cff inset;}
.mmh3l-item .th{width:100%;aspect-ratio:1;object-fit:cover;display:block;background:#12141a;}
.mmh3l-item .no{width:100%;aspect-ratio:1;display:flex;align-items:center;
  justify-content:center;color:#5a6070;font-size:11px;background:#12141a;}
.mmh3l-item .nm{padding:6px 8px;font-size:12px;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;}
.mmh3l-item .fav{position:absolute;top:5px;right:6px;font-size:13px;
  text-shadow:0 1px 3px #000;}
.mmh3l-item .kd{position:absolute;top:5px;left:6px;font-size:10px;padding:1px 5px;
  border-radius:4px;background:rgba(10,12,18,.75);color:#9aa2b4;}
.mmh3l-detail{width:330px;flex:none;border-left:1px solid #2c303a;padding:14px;
  overflow:auto;display:flex;flex-direction:column;gap:10px;}
.mmh3l-detail.empty{align-items:center;justify-content:center;color:#697084;}
.mmh3l-detail label{display:block;font-size:11px;color:#8890a2;margin-bottom:3px;}
.mmh3l-detail input[type=text],.mmh3l-detail textarea{width:100%;box-sizing:border-box;
  background:#12141a;color:#e6e8ee;border:1px solid #2c303a;border-radius:6px;
  padding:6px 8px;font:12px/1.45 inherit;resize:vertical;}
.mmh3l-detail textarea{min-height:92px;}
.mmh3l-keys{display:flex;flex-wrap:wrap;gap:4px;}
.mmh3l-keys button{background:#20232b;border:1px solid #2c303a;color:#aab0bd;
  border-radius:5px;padding:3px 7px;font-size:11px;cursor:pointer;}
.mmh3l-keys button.on{border-color:#5b8cff;color:#fff;}
.mmh3l-btn{background:#2a2f3a;border:1px solid #39404e;color:#e6e8ee;border-radius:6px;
  padding:6px 12px;font-size:12px;cursor:pointer;}
.mmh3l-btn:hover{background:#333947;}
.mmh3l-btn.pri{background:#3860d0;border-color:#4a72e6;}
.mmh3l-btn.pri:hover{background:#4570e8;}
.mmh3l-btn.dgr{background:#3a2126;border-color:#5c2f38;color:#ff9aa8;}
.mmh3l-btn.dgr:hover{background:#4d2a31;}
.mmh3l-search{background:#12141a;color:#e6e8ee;border:1px solid #2c303a;
  border-radius:6px;padding:5px 10px;font-size:12px;width:220px;}
.mmh3l-row{display:flex;gap:6px;align-items:center;}
.mmh3l-foot{flex:none;padding:9px 16px;border-top:1px solid #2c303a;color:#697084;
  font-size:11px;display:flex;align-items:center;gap:10px;}
.mmh3l-confirm{background:#3a2126;border:1px solid #5c2f38;border-radius:6px;
  padding:8px;font-size:12px;color:#ffc2cb;}
.mmh3l-empty{grid-column:1/-1;color:#697084;padding:40px 10px;text-align:center;}
.mmh3l-sum{font-size:11px;line-height:1.5;color:#aab0bd;padding:2px 0;}
.mmh3l-sum b{color:#e6e8ee;}
.mmh3l-sum .miss{color:#8890a2;font-style:italic;}
`;

let cssDone = false;
function injectCSS() {
  if (cssDone) return;
  cssDone = true;
  const s = document.createElement("style");
  s.textContent = CSS;
  document.head.appendChild(s);
}

/* ------------------------------------------------------------- helpers */

function el(tag, opts = {}, kids = []) {
  const n = document.createElement(tag);
  if (opts.class) n.className = opts.class;
  if (opts.text != null) n.textContent = opts.text;
  if (opts.html != null) n.innerHTML = opts.html;
  for (const [k, v] of Object.entries(opts.attr || {})) n.setAttribute(k, v);
  for (const [k, v] of Object.entries(opts.on || {})) n.addEventListener(k, v);
  Object.assign(n.style, opts.style || {});
  for (const c of kids) if (c) n.appendChild(c);
  return n;
}

async function jsonPost(path, body) {
  const r = await api.fetchApi(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `${r.status}`);
  return data;
}

async function fetchList() {
  const r = await api.fetchApi("/mmh3_library/list");
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `${r.status}`);
  return data;
}

function imgURL(item, key, thumb) {
  const q = new URLSearchParams({ kind: item.kind, id: item.id });
  if (key) q.set("key", key);
  if (thumb) q.set("thumb", "1");
  q.set("v", String(item._v || 0));
  return api.apiURL("/mmh3_library/image?" + q.toString());
}

const KIND_KO = {
  actors: "배우", costumes: "의상", scenes: "장소",
  props: "소품", layouts: "레이아웃", voices: "음성",
};

/* --------------------------------------------------------------- modal */

class LibraryModal {
  constructor(node) {
    this.node = node;
    this.kind = "";            // "" = 전체
    this.q = "";
    this.items = [];
    this.sel = null;
    this.fileKey = "";
    this.root = "";
    this.overlay = null;
  }

  async open() {
    injectCSS();
    if (this.overlay) return;
    this.overlay = el("div", {
      class: "mmh3l-overlay",
      on: { mousedown: (e) => { if (e.target === this.overlay) this.close(); } },
    });
    this.card = el("div", { class: "mmh3l-card" });
    this.overlay.appendChild(this.card);
    document.body.appendChild(this.overlay);
    this._esc = (e) => { if (e.key === "Escape") this.close(); };
    window.addEventListener("keydown", this._esc);
    await this.reload();
  }

  close() {
    window.removeEventListener("keydown", this._esc);
    this.overlay?.remove();
    this.overlay = null;
  }

  async reload(keepSel = true) {
    const prev = keepSel && this.sel ? this.sel.id : null;
    try {
      const data = await fetchList();
      this.items = data.items || [];
      this.root = data.root || "";
    } catch (e) {
      this.items = [];
      this.root = "";
      this.err = String(e.message || e);
    }
    const stamp = Date.now();
    for (const it of this.items) it._v = stamp;
    this.sel = prev ? this.items.find((x) => x.id === prev) || null : null;
    if (this.sel && !this.sel.files.includes(this.fileKey)) this.fileKey = "";
    this.render();
  }

  filtered() {
    const q = this.q.trim().toLowerCase();
    return this.items.filter((it) => {
      if (this.kind && it.kind !== this.kind) return false;
      if (!q) return true;
      return (it.name + " " + it.description + " " + (it.tags || []).join(" "))
        .toLowerCase().includes(q);
    });
  }

  render() {
    this.card.innerHTML = "";
    const list = this.filtered();

    /* head */
    const search = el("input", {
      class: "mmh3l-search",
      attr: { type: "text", placeholder: "이름 · 설명 · 태그 검색" },
    });
    search.value = this.q;
    search.addEventListener("input", () => {
      this.q = search.value;
      const g = this.card.querySelector(".mmh3l-grid");
      if (g) this.paintGrid(g);
    });
    this.card.appendChild(el("div", { class: "mmh3l-head" }, [
      el("h2", { text: "📚 에셋 라이브러리" }),
      search,
      el("div", { class: "sp" }),
      el("button", {
        class: "mmh3l-btn", text: "폴더 열기",
        on: { click: () => jsonPost("/mmh3_library/open_folder", {}).catch(() => {}) },
      }),
      el("button", { class: "mmh3l-btn", text: "새로고침",
                     on: { click: () => this.reload() } }),
      el("button", { class: "mmh3l-btn", text: "✕", on: { click: () => this.close() } }),
    ]));

    /* body */
    const side = el("div", { class: "mmh3l-side" });
    const counts = {};
    for (const it of this.items) counts[it.kind] = (counts[it.kind] || 0) + 1;
    const mkKind = (k, label) => {
      const n = el("div", { class: "mmh3l-kind" + (this.kind === k ? " on" : "") },
                   [el("span", { text: label })]);
      n.appendChild(el("span", { class: "n",
                                 text: String(k ? counts[k] || 0 : this.items.length) }));
      n.addEventListener("click", () => { this.kind = k; this.render(); });
      return n;
    };
    side.appendChild(mkKind("", "전체"));
    for (const k of Object.keys(KIND_KO)) side.appendChild(mkKind(k, KIND_KO[k]));

    const grid = el("div", { class: "mmh3l-grid" });
    const detail = el("div", { class: "mmh3l-detail" });
    this.detailEl = detail;
    this.card.appendChild(el("div", { class: "mmh3l-body" }, [
      side, el("div", { class: "mmh3l-main" }, [grid, detail]),
    ]));
    this.paintGrid(grid);
    this.paintDetail();

    /* foot */
    this.card.appendChild(el("div", { class: "mmh3l-foot" }, [
      el("span", { text: `${list.length} / ${this.items.length}개` }),
      el("span", { text: this.root ? "· " + this.root : "" }),
    ]));
  }

  paintGrid(grid) {
    grid.innerHTML = "";
    const list = this.filtered();
    if (!list.length) {
      grid.appendChild(el("div", {
        class: "mmh3l-empty",
        text: this.items.length
          ? "조건에 맞는 에셋이 없습니다."
          : "아직 저장된 에셋이 없습니다 — Asset Save 노드로 먼저 저장하세요.",
      }));
      return;
    }
    for (const it of list) {
      const node = el("div", {
        class: "mmh3l-item" + (this.sel && this.sel.id === it.id ? " on" : ""),
        on: {
          click: () => { this.sel = it; this.fileKey = ""; this.render(); },
          dblclick: () => { this.apply(it); this.close(); },
        },
      });
      if (it.cover) {
        node.appendChild(el("img", {
          class: "th", attr: { src: imgURL(it, it.cover, true), loading: "lazy" },
        }));
      } else {
        node.appendChild(el("div", { class: "no", text: "이미지 없음" }));
      }
      node.appendChild(el("div", { class: "kd", text: KIND_KO[it.kind] || it.kind }));
      if (it.favorite) node.appendChild(el("div", { class: "fav", text: "★" }));
      node.appendChild(el("div", { class: "nm", text: it.name }));
      grid.appendChild(node);
    }
  }

  paintDetail() {
    const d = this.detailEl;
    d.innerHTML = "";
    d.classList.toggle("empty", !this.sel);
    if (!this.sel) {
      d.appendChild(el("div", { text: "왼쪽에서 에셋을 고르세요" }));
      return;
    }
    const it = this.sel;

    const big = el("img", {
      attr: { src: imgURL(it, this.fileKey || it.cover, false) },
      style: { width: "100%", borderRadius: "8px", background: "#12141a" },
    });
    if (it.cover) d.appendChild(big);

    const name = el("input", { attr: { type: "text" } });
    name.value = it.name;
    d.appendChild(el("div", {}, [el("label", { text: "이름" }), name]));

    const desc = el("textarea", {
      attr: { placeholder: "영어로. H3 의 <Subject N> 정의문으로 그대로 나갑니다." },
    });
    desc.value = it.description;
    d.appendChild(el("div", {}, [el("label", { text: "설명 (영어)" }), desc]));

    const tags = el("input", { attr: { type: "text", placeholder: "쉼표로 구분" } });
    tags.value = (it.tags || []).join(", ");
    d.appendChild(el("div", {}, [el("label", { text: "태그" }), tags]));

    if (it.files.length) {
      const keys = el("div", { class: "mmh3l-keys" });
      const mk = (k, label) => {
        const b = el("button", {
          class: (this.fileKey === k ? "on" : ""), text: label,
          on: { click: () => { this.fileKey = k; this.paintDetail(); } },
        });
        return b;
      };
      keys.appendChild(mk("", "자동"));
      for (const k of it.files) keys.appendChild(mk(k, k));
      d.appendChild(el("div", {}, [el("label", { text: "파일" }), keys]));
    }

    const fav = el("input", { attr: { type: "checkbox" } });
    fav.checked = !!it.favorite;
    d.appendChild(el("label", { class: "mmh3l-row" }, [
      fav, el("span", { text: "즐겨찾기 (목록 맨 위로)" }),
    ]));

    const save = el("button", {
      class: "mmh3l-btn", text: "저장",
      on: {
        click: async () => {
          save.disabled = true;
          try {
            await jsonPost("/mmh3_library/update", {
              kind: it.kind, id: it.id, name: name.value,
              description: desc.value, tags: tags.value, favorite: fav.checked,
            });
            await this.reload();
          } catch (e) {
            save.disabled = false;
            d.appendChild(el("div", { class: "mmh3l-confirm", text: String(e.message || e) }));
          }
        },
      },
    });
    const use = el("button", {
      class: "mmh3l-btn pri", text: "이 에셋 쓰기",
      on: { click: () => { this.apply(it); this.close(); } },
    });
    d.appendChild(el("div", { class: "mmh3l-row" }, [use, save]));

    const delBtn = el("button", {
      class: "mmh3l-btn dgr", text: "삭제",
      on: {
        click: () => {
          delBtn.style.display = "none";
          const box = el("div", { class: "mmh3l-confirm" }, [
            el("div", { text: `"${it.name}" 을 영구 삭제합니다. 되돌릴 수 없습니다.` }),
            el("div", { class: "mmh3l-row", style: { marginTop: "8px" } }, [
              el("button", {
                class: "mmh3l-btn dgr", text: "삭제",
                on: {
                  click: async () => {
                    await jsonPost("/mmh3_library/delete",
                                   { kind: it.kind, id: it.id });
                    this.sel = null;
                    await this.reload(false);
                  },
                },
              }),
              el("button", {
                class: "mmh3l-btn", text: "취소",
                on: { click: () => this.paintDetail() },
              }),
            ]),
          ]);
          d.appendChild(box);
        },
      },
    });
    d.appendChild(delBtn);

    d.appendChild(el("div", {
      class: "mmh3l-sum",
      html: `<b>${it.id}</b><br>보유: ${it.files.join(", ") || "—"}`,
    }));
  }

  /** 고른 에셋을 노드 위젯에 꽂는다. 목록에 없던 항목이면 선택지에 넣어 준다. */
  apply(it) {
    const node = this.node;
    if (!node) return;
    const w = node.widgets?.find((x) => x.name === "asset");
    if (w) {
      const vals = w.options?.values || [];
      const labels = ["(없음)", ...this.items.map((x) => x.label)];
      if (w.options) w.options.values = labels;
      else w.options = { values: labels };
      if (!labels.includes(it.label)) labels.push(it.label);
      w.value = it.label;
      w.callback?.(it.label);
    }
    const k = node.widgets?.find((x) => x.name === "file_key");
    if (k) { k.value = this.fileKey || ""; k.callback?.(k.value); }
    node._mmh3RefreshSummary?.();
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, true);
  }
}

/* -------------------------------------------------- node registration */

app.registerExtension({
  name: "mmh3.asset_panel",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "MMH3_AssetLoad" && nodeData.name !== "MMH3_AssetSave") return;
    const isLoad = nodeData.name === "MMH3_AssetLoad";
    const orig = nodeType.prototype.onNodeCreated;

    nodeType.prototype.onNodeCreated = function () {
      orig?.apply(this, arguments);
      injectCSS();
      const modal = new LibraryModal(isLoad ? this : null);
      this.addWidget("button", "라이브러리 열기…", null, () => modal.open());
      if (!isLoad) return;

      const sum = el("div", { class: "mmh3l-sum", text: "…" });
      this.addDOMWidget("mmh3_summary", "div", sum,
                        { serialize: false, getMinHeight: () => 54 });

      this._mmh3RefreshSummary = async () => {
        const label = this.widgets?.find((w) => w.name === "asset")?.value;
        if (!label || label === "(없음)") {
          sum.innerHTML = `<span class="miss">에셋을 고르세요 — 버튼으로 열거나 드롭다운에서</span>`;
          return;
        }
        const id = String(label).split("  ·  ").pop();
        try {
          const data = await fetchList();
          const it = (data.items || []).find((x) => x.id === id);
          if (!it) {
            sum.innerHTML = `<span class="miss">${label} — 찾을 수 없음</span>`;
            return;
          }
          const key = this.widgets?.find((w) => w.name === "file_key")?.value || "";
          const desc = it.description
            ? it.description.slice(0, 90) + (it.description.length > 90 ? "…" : "")
            : `<span class="miss">설명 없음 — &lt;Subject N&gt; 정의문이 비어 나갑니다</span>`;
          sum.innerHTML = `<b>${it.name}</b> · ${KIND_KO[it.kind] || it.kind}` +
            ` · ${key || "자동"} → ${key || it.cover || "—"}<br>${desc}`;
        } catch {
          sum.innerHTML = `<span class="miss">목록을 못 읽었습니다</span>`;
        }
      };
      setTimeout(() => this._mmh3RefreshSummary(), 60);

      const aw = this.widgets?.find((w) => w.name === "asset");
      if (aw) {
        const cb = aw.callback;
        aw.callback = (...a) => { cb?.apply(this, a); this._mmh3RefreshSummary(); };
      }
    };
  },
});
