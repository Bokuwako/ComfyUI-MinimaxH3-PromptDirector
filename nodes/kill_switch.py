# -*- coding: utf-8 -*-
"""Kill Switch — 재시작 직후에 가장 가까운 상태로 되돌립니다.

ComfyUI 의 "Clear cache" / "Clear VRAM" 버튼은 **이 프로세스가 붙들고 있는 모델**만
건드립니다. 그래서 이런 것들이 그대로 남습니다:

  * comfy-env 격리 워커 — SAM3 처럼 자기 파이썬 환경이 필요한 노드팩은 **별도
    프로세스**에서 돕니다. ComfyUI 의 모델 목록에 없으니 Clear VRAM 이 못 봅니다.
    한 번 뜨면 ComfyUI 가 살아 있는 동안 계속 VRAM 을 붙들고 있습니다.
  * 지난 실행에서 남은 고아 워커 — ComfyUI 가 죽어도 살아남을 수 있습니다.
  * Ollama 가 물고 있는 LLM — 아예 다른 서버라 ComfyUI 는 모릅니다.
  * 실행 노드 캐시 — 모델이 아니라 노드 출력이라 Clear VRAM 과 무관합니다.

H3 본체가 16GB 카드에서 19,995MB 를 staged 로 잡기 때문에, 남아 있는 수백 MB 가
그대로 PCIe 스트리밍 압박으로 돌아옵니다. 그래서 "대충 비우기" 가 아니라 "전부
내리기" 가 필요합니다.

노드가 하는 일은 전부 되돌릴 수 있습니다 — 죽인 워커는 해당 노드를 다시 쓰면
자동으로 다시 뜨고(기동 시간은 다시 듭니다), 언로드한 모델은 다시 로드됩니다.
"""

import gc
import time


class _Any(str):
    """어떤 타입과도 연결되는 와일드카드. 순서를 강제할 때만 씁니다."""

    def __ne__(self, other):
        return False


ANY = _Any("*")

CATEGORY = "MiniMax H3/Utils"


def _vram():
    """(free_MB, total_MB) — torch 할당자가 아니라 GPU 전체 기준."""
    try:
        import torch
        if not torch.cuda.is_available():
            return None
        free, total = torch.cuda.mem_get_info()
        return free // (1024 * 1024), total // (1024 * 1024)
    except Exception:
        return None


def _unload_comfy_models(log):
    import comfy.model_management as mm
    try:
        before = len(getattr(mm, "current_loaded_models", []) or [])
    except Exception:
        before = -1
    mm.unload_all_models()
    for fn in ("cleanup_models_gc", "cleanup_models"):
        f = getattr(mm, fn, None)
        if callable(f):
            try:
                f()
            except TypeError:
                try:
                    f(False)
                except Exception:
                    pass
            except Exception:
                pass
    try:
        after = len(getattr(mm, "current_loaded_models", []) or [])
    except Exception:
        after = -1
    log("ComfyUI 모델: {} → {} 개".format(
        before if before >= 0 else "?", after if after >= 0 else "?"))


def _clear_node_cache(log):
    """실행 노드 캐시. 실행 중에 직접 reset() 하면 지금 돌고 있는 그래프가 깨지므로,
    ComfyUI 자신이 쓰는 플래그를 세워 이 프롬프트가 끝난 뒤에 비우게 합니다."""
    try:
        from server import PromptServer
        q = PromptServer.instance.prompt_queue
        q.set_flag("free_memory", True)
        q.set_flag("unload_models", True)
        log("노드 캐시: 이 실행이 끝난 직후 비워지도록 예약")
    except Exception as exc:
        log("노드 캐시: 실패 ({})".format(exc))


def _shutdown_workers(log):
    """comfy-env 격리 워커 (SAM3 등)."""
    try:
        from comfy_env.isolation import wrap
    except Exception as exc:
        log("격리 워커: comfy-env 없음 ({})".format(exc))
        return
    try:
        pool = dict(getattr(wrap, "_WORKER_POOL", {}) or {})
    except Exception:
        pool = {}
    if not pool:
        log("격리 워커: 떠 있는 워커 없음")
        return
    names = [str(k).rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for k in pool]
    try:
        wrap._shutdown_all_workers()
        log("격리 워커 종료: {}".format(", ".join(names) or "?"))
    except Exception as exc:
        log("격리 워커: 종료 실패 ({})".format(exc))


def _kill_orphans(log):
    """지난 실행에서 남은 comfy-env 워커. 명령줄이 정확히 이 서명일 때만 죽입니다."""
    killed, mine = [], None
    try:
        import os
        mine = os.getpid()
    except Exception:
        pass
    try:
        import subprocess
        # WMIC 없이도 되도록 PowerShell 로 명령줄까지 읽습니다.
        ps = ("Get-CimInstance Win32_Process | "
              "Where-Object { $_.CommandLine -like '*comfyui_pvenv_*' -and "
              "$_.CommandLine -like '*persistent_worker.py*' } | "
              "ForEach-Object { $_.ProcessId }")
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                             capture_output=True, text=True, timeout=30)
        pids = [int(x) for x in out.stdout.split() if x.strip().isdigit()]
    except Exception as exc:
        log("고아 워커: 조회 실패 ({})".format(exc))
        return
    for pid in pids:
        if pid == mine:
            continue
        try:
            import subprocess
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, timeout=15)
            killed.append(pid)
        except Exception:
            pass
    log("고아 워커: {}".format(
        "PID " + ", ".join(str(p) for p in killed) + " 종료" if killed else "없음"))


def _unload_ollama(url, log):
    try:
        from ..mmh3 import ollama_client
    except ImportError:
        from mmh3 import ollama_client
    try:
        resident = ollama_client.loaded_models(url) or []
    except Exception as exc:
        log("Ollama: 조회 실패 ({})".format(exc))
        return
    if not resident:
        log("Ollama: 올라온 모델 없음")
        return
    done = []
    for name in resident:
        try:
            ok, _detail = ollama_client.unload(url, name)
        except Exception:
            ok = False
        done.append("{}{}".format(name, "" if ok else " (실패)"))
    log("Ollama 언로드: {}".format(", ".join(done)))


def _empty_torch(log):
    freed = []
    try:
        gc.collect()
        freed.append("gc")
    except Exception:
        pass
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            freed.append("empty_cache")
            try:
                torch.cuda.ipc_collect()
                freed.append("ipc_collect")
            except Exception:
                pass
    except Exception:
        pass
    try:
        import comfy.model_management as mm
        mm.soft_empty_cache(True)
        freed.append("soft_empty_cache")
    except Exception:
        pass
    log("torch/캐시: {}".format(", ".join(freed) or "없음"))


class MMH3_KillSwitch:
    """올라온 것을 전부 내립니다 — ComfyUI 모델, 격리 워커, Ollama, torch 캐시."""

    DESCRIPTION = (
        "Unloads everything: ComfyUI's models, the comfy-env isolation workers that "
        "Clear VRAM cannot see (SAM3 and friends run in their own process), leftover "
        "orphan workers from a previous run, whatever Ollama is holding, and the torch "
        "allocator. Closest thing to a fresh restart without restarting. Everything it "
        "kills comes back on demand."
    )

    @classmethod
    def INPUT_TYPES(cls):
        try:
            from ..mmh3 import ollama_client
        except ImportError:
            from mmh3 import ollama_client
        return {
            "required": {
                "comfy_models": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "ComfyUI 가 붙들고 있는 모델을 전부 내립니다 "
                               "(Clear VRAM 과 같은 범위)."}),
                "isolated_workers": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "comfy-env 격리 워커를 종료합니다. SAM3 처럼 자기 파이썬 "
                               "환경에서 도는 노드팩은 별도 프로세스라 Clear VRAM 이 "
                               "못 봅니다. 다시 쓰면 자동으로 재기동되지만 기동 시간이 "
                               "다시 듭니다."}),
                "orphan_workers": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "지난 실행에서 남은 격리 워커까지 죽입니다. ComfyUI 를 "
                               "재시작해도 살아남는 경우가 있습니다. 명령줄이 "
                               "comfyui_pvenv_ + persistent_worker.py 인 프로세스만 "
                               "대상입니다."}),
                "ollama": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Ollama 가 물고 있는 모델을 전부 내립니다. 다른 서버라 "
                               "ComfyUI 는 존재조차 모릅니다."}),
                "ollama_url": ("STRING", {"default": ollama_client.DEFAULT_URL}),
                "node_cache": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "실행 노드 출력 캐시를 비웁니다. 지금 돌고 있는 그래프를 "
                               "깨지 않도록, 이 실행이 끝난 직후에 비워지게 예약합니다."}),
                "torch_cache": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "gc + torch.cuda.empty_cache + ipc_collect."}),
            },
            "optional": {
                "passthrough": (ANY, {
                    "tooltip": "순서를 강제하고 싶을 때만 연결하세요. 무엇을 연결하든 "
                               "그대로 통과시킵니다 — 이 노드가 그 앞이 끝난 뒤에 "
                               "돌게 만드는 용도입니다."}),
            },
        }

    RETURN_TYPES = (ANY, "STRING")
    RETURN_NAMES = ("passthrough", "report")
    FUNCTION = "run"
    CATEGORY = CATEGORY
    OUTPUT_NODE = True          # 아무것도 연결하지 않아도 단독 실행됩니다

    @classmethod
    def IS_CHANGED(cls, **kw):
        return time.time()      # 킬 스위치가 캐시되면 아무 의미가 없습니다

    def run(self, comfy_models, isolated_workers, orphan_workers, ollama,
            ollama_url, node_cache, torch_cache, passthrough=None):
        notes = []
        log = notes.append
        t0 = time.time()
        v0 = _vram()

        # 순서가 있습니다: 남의 프로세스를 먼저 내보내고, 우리 것을 내리고,
        # 마지막에 할당자를 비워야 방금 놓인 것까지 회수됩니다.
        if isolated_workers:
            _shutdown_workers(log)
        if orphan_workers:
            _kill_orphans(log)
        if ollama:
            _unload_ollama(ollama_url, log)
        if comfy_models:
            _unload_comfy_models(log)
        if node_cache:
            _clear_node_cache(log)
        if torch_cache:
            _empty_torch(log)

        v1 = _vram()
        head = []
        if v0 and v1:
            head.append("VRAM 여유 {}MB → {}MB  (+{}MB / 전체 {}MB)".format(
                v0[0], v1[0], v1[0] - v0[0], v1[1]))
        head.append("{:.2f}초".format(time.time() - t0))
        report = "\n".join(["=== KILL SWITCH ==="] + head + [""] + ["  " + n for n in notes])
        print("[MMH3 KillSwitch]\n" + report)
        return (passthrough, report)
