# -*- coding: utf-8 -*-
"""프레임 수가 모델 격자에 맞는지 로드 직후에 확인하고, 틀리면 바로 멈춘다.

비디오 모델의 VAE 는 프레임을 묶어서 압축하므로 격자 위의 길이만 온전히 왕복한다.
나머지는 조용히 버려진다 — Wan 에 192 프레임을 넣으면 189 프레임이 돌아온다.
그 사실은 원본과 결과를 다시 맞춰 보는 노드(SEGSPaste 등)에서 처음 드러나는데,
그 앞의 감지·샘플링은 개수가 틀려도 그냥 돌아가서 수십 분 뒤에야 터진다.

ComfyUI 는 실행 전에 연결과 타입만 검사하고 프레임 수 같은 내용물은 보지 않는다.
그래서 이 노드를 로더 바로 뒤에 통과 노드로 두어, 영상을 읽자마자 검사하게 한다.
아래 노드가 전부 이 노드의 출력을 받으므로 감지·샘플링보다 먼저 실행된다.
"""

CATEGORY = "MiniMax H3/Utils"

# 이름 -> (주기, 나머지). 격자 위의 길이 n 은 n % 주기 == 나머지.
GRIDS = {
    "Wan (4n+1)": (4, 1),
    "MiniMax H3 (17k+5)": (17, 5),
    "Wan + H3 둘 다 (68k+5)": (68, 5),
    "LTX (8n+1)": (8, 1),
}


def _neighbours(n, period, rem):
    """n 아래·위로 가장 가까운 격자 길이."""
    below = n - ((n - rem) % period)
    above = below if below == n else below + period
    return max(below, rem), above


class MMH3_FrameGridGuard:
    DESCRIPTION = (
        "영상 프레임 수가 모델 격자에 맞는지 로드 직후에 검사합니다. 맞으면 그대로 "
        "통과시키고, 틀리면 가까운 올바른 길이를 알려주며 즉시 멈춥니다. 로더 바로 "
        "뒤에 두고 아래 노드들이 이 노드의 출력을 받게 연결하세요.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "로더에서 나온 영상 프레임."}),
                "grid": (list(GRIDS), {
                    "default": "Wan (4n+1)",
                    "tooltip": "영상을 받을 모델의 프레임 격자. H3 로 뽑은 영상을 Wan 에 "
                               "넣을 거면 'Wan + H3 둘 다' 에 맞춰 뽑는 게 가장 편합니다 "
                               "(73 · 141 · 209 · 277 프레임)."}),
                "on_mismatch": (["stop", "warn"], {
                    "default": "stop",
                    "tooltip": "stop: 틀리면 즉시 에러로 멈춤.\n"
                               "warn: 콘솔에 경고만 남기고 계속 진행."}),
                "fps": ("FLOAT", {"default": 24.0, "min": 1.0, "max": 240.0, "step": 1.0,
                                  "tooltip": "메시지에 초 단위를 함께 적기 위해서만 씁니다."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "STRING")
    RETURN_NAMES = ("images", "frame_count", "report")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, images, grid, on_mismatch, fps):
        n = int(images.shape[0])
        period, rem = GRIDS[grid]
        sec = lambda k: "%.2f초" % (k / float(fps))

        if n % period == rem:
            report = "[FrameGridGuard] %d프레임 (%s) — %s 격자에 맞음" % (n, sec(n), grid)
            print(report)
            return (images, n, report)

        below, above = _neighbours(n, period, rem)
        report = (
            "[FrameGridGuard] %d프레임 (%s) 은 %s 격자에 맞지 않습니다.\n"
            "  이대로 진행하면 VAE 를 거치며 끝 프레임이 조용히 버려지고, 원본과 결과를 "
            "맞추는 노드에서 한참 뒤에 터집니다.\n"
            "  가까운 올바른 길이: %d프레임 (%s) 로 자르기  또는  %d프레임 (%s) 로 채우기"
            % (n, sec(n), grid, below, sec(below), above, sec(above)))
        print(report)
        if on_mismatch == "stop":
            raise ValueError(report)
        return (images, n, report)
