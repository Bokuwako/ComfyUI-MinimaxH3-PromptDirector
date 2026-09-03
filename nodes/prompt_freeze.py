# -*- coding: utf-8 -*-
"""Prompt Hold — 받은 프롬프트를 칸에 담아두고, 위쪽이 꺼지면 그걸 그대로 씁니다.

프롬프트가 확정된 뒤에도 Writer 가 계속 도는 게 문제였습니다. 시드를 고정해도 소용이
없습니다 — 시드는 "어떤 결과가 나오는가" 를 정할 뿐이고, 노드 캐시는 메모리에만 있어서
ComfyUI 를 재시작하면 사라집니다. 그러면 26B 모델이 매번 20초 넘게 다시 돕니다.

모드 같은 건 없습니다. 규칙 하나뿐입니다:

    위쪽에서 프롬프트가 오면  →  통과시키고 그 텍스트를 칸에 적어 둔다
    안 오면                 →  칸에 있는 것을 그대로 내보낸다

그래서 Writer 를 뮤트(Ctrl+M)하면 자동으로 저장된 프롬프트가 쓰입니다. `live` 가
optional 이라 링크가 끊겨도 이 노드는 그대로 실행됩니다. 다시 켜면 새 프롬프트가
들어오고 칸도 갱신됩니다.

    Writer.prompt ──live──► Prompt Hold ──prompt──► StringFunction ──► Director
                     (뮤트하면 칸의 내용이 나감)
"""

CATEGORY = "MiniMax H3/Utils"


class MMH3_PromptFreeze:
    """Pass a prompt through and remember it; emit the remembered one when none arrives."""

    DESCRIPTION = (
        "Remembers the last prompt that came through and emits it whenever nothing new "
        "arrives — so muting the writer is all it takes to stop the LLM running. There "
        "is no mode to set. Fixing the seed does not achieve this: a seed decides what "
        "comes out, not whether the node runs, and the node cache is memory-only so a "
        "restart re-runs everything anyway. The text is stored in the workflow, so it "
        "survives a restart, and you can edit it by hand."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_text": ("STRING", {
                    "multiline": True, "default": "",
                    "placeholder": "한 번 돌리면 여기가 자동으로 채워집니다.\n"
                                   "위쪽 노드를 뮤트(Ctrl+M)하면 이 텍스트가 그대로 나갑니다.",
                    "tooltip": "받은 프롬프트가 실행 때마다 여기 갱신됩니다. 워크플로우에 "
                               "저장되므로 재시작해도 남습니다. 직접 고쳐 써도 되고, 그 "
                               "상태로 위쪽을 뮤트해두면 고친 내용이 쓰입니다.",
                }),
            },
            "optional": {
                # optional 이라야 위쪽을 뮤트했을 때 링크가 사라져도 이 노드가 실행됩니다.
                # required 였다면 "입력이 없다" 로 검증에서 막힙니다.
                "live": ("STRING", {"forceInput": True,
                                    "tooltip": "MiniMax H3 Prompt Writer 의 prompt 출력을 "
                                               "연결하세요. 이 노드를 뮤트하면 아래 칸의 "
                                               "텍스트가 대신 쓰입니다."}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "source")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, prompt_text, live=None):
        saved = (prompt_text or "").strip()
        fresh = live.strip() if isinstance(live, str) else ""

        if fresh:
            # UI 가 이 값을 받아 prompt_text 위젯에 써 넣습니다 (web/…_freeze.js).
            return {"ui": {"captured": [fresh]},
                    "result": (fresh, "새 프롬프트 ({}자) — 칸에 저장했습니다".format(len(fresh)))}

        if saved:
            return (saved, "위쪽이 꺼져 있어 저장된 것을 사용했습니다 ({}자)".format(len(saved)))

        # 둘 다 비었으면 조용히 빈 문자열을 흘려보내지 않습니다. 빈 프롬프트는 훨씬
        # 하류에서 훨씬 알아보기 어려운 형태로 터집니다.
        raise RuntimeError(
            "Prompt Hold: 내보낼 프롬프트가 없습니다.\n"
            "위쪽 Prompt Writer 를 켜고 한 번 실행하거나, prompt_text 칸에 직접 "
            "붙여넣으세요.")
