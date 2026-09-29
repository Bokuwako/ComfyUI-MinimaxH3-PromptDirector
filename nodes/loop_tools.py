# -*- coding: utf-8 -*-
"""클립 이어붙이기(H3 Project Suite 체인)를 받치는 노드 두 개.

둘 다 ethanfel/ComfyUI-MiniMaxH3-Context-Loop 의 설계를 이 워크플로우에 맞게 옮긴 것이다.
코드를 가져온 것이 아니라 발상을 가져왔고, 차이는 각 클래스 설명에 적었다.

MMH3_HeadMaskTaper
    H3 Context 가 붙이는 head 고정 마스크를 (1) 영상·오디오 두 장짜리 중첩 마스크로
    바꾸고 (2) 고정 강도를 경계로 갈수록 단단해지게 테이퍼한다.

MMH3_ColorCarry
    이어붙인 클립의 밝기·채도를 첫 클립(앵커)에 맞춘다. 출력 영상과, 다음 클립이
    이어받을 chain latent 양쪽에 같은 보정을 준다.
"""

import json
import math
import os

CATEGORY = "MiniMax H3/Loop"


# ------------------------------------------------------------------ 공통

def _nested(t):
    return getattr(t, "is_nested", False)


def _nested_tensor(parts):
    import comfy.nested_tensor
    return comfy.nested_tensor.NestedTensor(tuple(parts))


def h3_frames_to_steps(frames):
    """H3 의 시간 토큰 수. 프레임은 17개씩 묶이고 한 묶음은 (1,4,4,4,4) 프레임을 덮는
    5 토큰이다. 22 프레임 -> 7 토큰, 56 -> 17."""
    frames = max(0, int(frames))
    groups, r = divmod(frames, 17)
    steps = groups * 5
    if r:
        steps += 1 + int(math.ceil((r - 1) / 4.0))
    return steps


# ------------------------------------------------------------------ 1. head 마스크

class MMH3_HeadMaskTaper:
    """Context-Loop 의 Drift-Control AV 에서 가져온 발상.

    원본의 관찰: 이어받은 앞부분을 매 스텝 깨끗하게 고정하면 대비와 질감 오차가 클립마다
    쌓인다. 원본은 그 앞부분에 샘플러 스케줄에 맞춘 약간의 노이즈를 주고, 그 양을 경계로
    갈수록 줄여 마지막 이어받은 스텝만 정확하게 남긴다 (4 스텝이면 .75 .50 .25 .00).

    여기서는 노이즈를 직접 넣는 대신 H3 의 per-token 디노이즈 마스크 값을 쓴다. 마스크 값
    m 은 그 행을 sigma * m 에서 돌리므로, 고정값에 max_freedom * 가중치를 더하면 같은
    방향의 효과가 난다. 모델 패치가 필요 없는 근사다.

    그리고 H3 Context 가 붙이는 마스크는 영상 한 장짜리 평범한 텐서인데, 코어의
    LTXVSeparateAVLatent 는 영상·오디오 두 장짜리 중첩 마스크를 가정해서 masks[1] 에서
    터진다 (이어붙이기 + 업스케일 조합). 이 노드를 거치면 항상 중첩 마스크가 되므로 그
    충돌이 없어진다. 꺼 두어도 이 변환은 한다.

    업스케일러는 마스크를 버리고 새 latent 를 돌려준다. 업스케일 리파인 패스에도 앞부분을
    고정하려면 Concat 뒤에 이 노드를 하나 더 두고 trim_frames 를 연결하면, 업스케일된
    latent 크기에 맞춰 마스크를 새로 만든다.
    """

    DESCRIPTION = (
        "H3 Context 의 head 고정 마스크를 영상·오디오 중첩 마스크로 바꾸고, 경계로 갈수록 "
        "단단해지게 테이퍼합니다. 이어붙이기와 업스케일을 같이 쓸 때 나는 LTXVSeparateAVLatent "
        "크래시도 이 변환으로 막힙니다. 마스크가 없는 latent(예: 업스케일 직후)에는 "
        "trim_frames 를 연결하면 그 길이만큼 새로 만듭니다.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
                "enabled": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "끄면 테이퍼 없이 중첩 마스크 변환만 합니다 (크래시 방지는 유지)."}),
                "max_freedom": ("FLOAT", {
                    "default": 0.15, "min": 0.0, "max": 1.0, "step": 0.01,
                    "tooltip": "가장 앞 스텝에 더하는 디노이즈 여유. 경계 스텝으로 갈수록 0 이 됩니다. "
                               "0 이면 H3 Context 원래 동작과 같습니다."}),
            },
            "optional": {
                "trim_frames": ("INT", {
                    "forceInput": True,
                    "tooltip": "latent 에 마스크가 없을 때 앞부분 길이를 여기서 가져옵니다 "
                               "(H3 Context 의 trim_frames)."}),
            },
        }

    RETURN_TYPES = ("LATENT", "STRING")
    RETURN_NAMES = ("latent", "report")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, latent, enabled, max_freedom, trim_frames=0):
        import torch

        samples = latent.get("samples")
        if samples is None or not _nested(samples):
            return (latent, "[HeadMaskTaper] 중첩 AV latent 가 아니라 그대로 통과")

        video, audio = samples.unbind()[:2]
        B, _, T, H, W = video.shape
        mask = latent.get("noise_mask")

        base = None
        if mask is not None:
            vmask = mask.unbind()[0] if _nested(mask) else mask
            vmask = vmask.to(torch.float32)
            if vmask.ndim == 5 and vmask.shape[2] == T:
                base = vmask.mean(dim=(0, 1, 3, 4))          # 스텝별 평균값 [T]

        steps = 0
        if base is not None:
            while steps < T and float(base[steps]) < 0.999:
                steps += 1
        source = "기존 마스크"
        if steps == 0 and trim_frames:
            steps = min(T, h3_frames_to_steps(trim_frames))
            base = torch.zeros(T)
            source = "trim_frames %d" % int(trim_frames)

        if steps == 0:
            if mask is not None and not _nested(mask):
                out = dict(latent)
                out["noise_mask"] = _nested_tensor((mask.to(torch.float32), torch.ones_like(audio, dtype=torch.float32)))
                return (out, "[HeadMaskTaper] 고정할 앞부분 없음 — 마스크만 중첩으로 변환")
            return (latent, "[HeadMaskTaper] 고정할 앞부분 없음 — 그대로 통과")

        vm = torch.ones((B, 1, T, H, W), dtype=torch.float32)
        values = []
        for k in range(steps):
            w = (steps - 1 - k) / float(steps)                # .75 .50 .25 .00 식
            m = float(base[k]) + (float(max_freedom) * w if enabled else 0.0)
            m = max(0.0, min(1.0, m))
            vm[:, :, k] = m
            values.append(m)

        out = dict(latent)
        out["noise_mask"] = _nested_tensor((vm, torch.ones_like(audio, dtype=torch.float32)))
        report = ("[HeadMaskTaper] 앞 %d 스텝 고정 (%s)%s — 마스크 값 %s"
                  % (steps, source, "" if enabled else ", 테이퍼 꺼짐",
                     " ".join("%.2f" % v for v in values)))
        print(report)
        return (out, report)


# ------------------------------------------------------------------ 체크포인트 복구

class MMH3_AVLatentFromCheckpoint:
    """H3 Context Load Latent 의 출력을 디코드 가능한 AV latent 로.

    그 로더는 일부러 NestedTensor 가 아닌 평범한 리스트를 돌려준다 — context_latent 입력
    말고 다른 곳에 잘못 꽂히면 바로 실패하게. 체크포인트에서 영상을 복구할 때는 반대로
    디코드가 필요하므로 여기서 중첩 텐서로 감싼다.
    """

    DESCRIPTION = ("H3 Context Load Latent 의 [video, audio] 리스트를 VAEDecode / "
                   "Separate AV Latent 가 받는 중첩 AV latent 로 바꿉니다. 체크포인트 복구용.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"latent": ("LATENT",)}}

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, latent):
        samples = latent.get("samples")
        if _nested(samples):
            return (latent,)
        if not isinstance(samples, (list, tuple)) or len(samples) < 2:
            raise ValueError("[AVLatentFromCheckpoint] [video, audio] 형태의 latent 가 아닙니다.")
        out = {k: v for k, v in latent.items() if k != "samples"}
        out["samples"] = _nested_tensor(samples[:2])
        return (out,)


# ------------------------------------------------------------------ 2. 색 이월

_ANCHOR_NAME = "mmh3_color_anchor.json"


def _luma(x):
    return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]


def _stats(frames):
    """[T,H,W,C] 0..1 -> 밝기 p10/50/90, 채도 p25/50/75. 가운데 80% 만, 극단 픽셀 제외."""
    import torch

    T = frames.shape[0]
    f = frames[:: max(1, T // 24), :, :, :3].float()
    h, w = f.shape[1], f.shape[2]
    sy, sx = max(1, h // 160), max(1, w // 160)
    f = f[:, int(h * 0.1):int(h * 0.9):sy, int(w * 0.1):int(w * 0.9):sx]
    y = _luma(f)
    mx = f.max(dim=-1).values
    mn = f.min(dim=-1).values
    s = (mx - mn) / mx.clamp(min=1e-4)
    keep = (y > 0.03) & (y < 0.97)
    if int(keep.sum()) < 64:
        keep = torch.ones_like(y, dtype=torch.bool)
    y, s = y[keep], s[keep]
    q = lambda v, ps: [float(x) for x in torch.quantile(v, torch.tensor(ps, dtype=v.dtype))]
    ly = q(y, [0.10, 0.50, 0.90])
    ls = q(s, [0.25, 0.50, 0.75])
    return {"luma": ly, "sat": ls}


def _apply(frames, weights, offset, sat_mul):
    """weights [T] 만큼 밝기 오프셋과 채도 배율을 준다. 전역 변환이라 국소 대비는 그대로."""
    import torch

    rgb = frames[..., :3].float()
    w = weights.to(rgb).view(-1, 1, 1, 1)
    y = _luma(rgb).unsqueeze(-1)
    out = y + (rgb - y) * (1.0 + (sat_mul - 1.0) * w) + offset * w
    out = out.clamp(0.0, 1.0)
    if frames.shape[-1] > 3:
        out = torch.cat([out, frames[..., 3:].to(out)], dim=-1)
    return out.to(frames.dtype)


def _smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


class MMH3_ColorCarry:
    """Context-Loop 의 latent_color_carry 에서 가져온 발상.

    원본에서 가져온 것:
      * 밝기 퍼센타일(10/50/90)과 채도 퍼센타일(25/50/75)을 가운데 영역에서, 극단 픽셀을
        빼고 잰다. 이 워크플로우의 드리프트는 밝기·대비가 아니라 채도가 클립마다 빠지는
        형태였고, Suite 의 level_match 는 밝기만 본다.
      * 직전 클립이 아니라 **앵커**(체인의 첫 클립)에 맞춘다. 직전 클립에 맞추면 오차가
        그대로 누적된다.
      * latent 에는 재인코딩본을 넣지 않고 E(보정본) - E(원본) 차이만 더한다. 두 인코딩이
        같은 VAE 왕복 편향을 가져서 차이에서 상쇄된다.
      * 그 차이를 공간적으로 저역통과한다. 색보정이 화면 번짐을 만드는 경로를 막는다.
      * 이어받은 구간에서 새 구간으로 smoothstep 으로 점점 세게.
      * 밝기 이동량과 채도 배율에 상한.

    이 워크플로우에 맞춘 것:
      * 체인 latent 는 베이스(저해상도) latent 이고, 다음 클립은 그 끝부분만 이어받는다.
        그래서 latent 보정은 끝 tail_steps 스텝만 디코드·인코드해 싸게 한다. 시작점을
        H3 토큰 묶음(5 스텝) 경계에 맞춰 시간 묶음이 어긋나지 않게 한다.
      * 앵커는 프로젝트 폴더에 통계 JSON 으로 남긴다. 체인이 비활성(첫 클립)일 때 기록하고,
        활성일 때 읽어서 보정한다. 재시작해도 유지된다.
      * latent 보정은 실패해도 멈추지 않는다. 영상 보정만 적용하고 리포트에 이유를 남긴다.
    """

    DESCRIPTION = (
        "이어붙인 클립의 밝기·채도를 체인 첫 클립(앵커)에 맞춥니다. 출력 영상과 다음 클립이 "
        "이어받을 chain latent 양쪽에 적용합니다. 체인이 비활성일 때 현재 클립을 앵커로 "
        "기록하고, 활성일 때 보정합니다.")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "서브그래프의 최종 영상."}),
                "latent": ("LATENT", {"tooltip": "chain_latent (베이스 AV latent)."}),
                "vae": ("VAE", {"tooltip": "영상 VAE."}),
                "enabled": ("BOOLEAN", {"default": True}),
                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05}),
                "max_luma_shift": ("FLOAT", {
                    "default": 0.02, "min": 0.0, "max": 0.2, "step": 0.005,
                    "tooltip": "밝기 이동 상한 (0..1 스케일, 0.02 ≈ 5/255)."}),
                "max_saturation_change": ("FLOAT", {
                    "default": 0.15, "min": 0.0, "max": 0.5, "step": 0.01,
                    "tooltip": "채도 배율 상한. 0.15 면 0.85~1.15 배."}),
                "lowpass_kernel": ("INT", {
                    "default": 5, "min": 1, "max": 15, "step": 2,
                    "tooltip": "latent 보정 차이를 퍼뜨리는 공간 커널 (latent 칸 단위)."}),
                "tail_steps": ("INT", {
                    "default": 17, "min": 0, "max": 400,
                    "tooltip": "chain latent 에서 보정할 끝 스텝 수. 0 이면 전체. "
                               "17 스텝 ≈ 56 프레임으로 context_length 22~56 을 덮습니다."}),
                "reset_anchor": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "켜면 이번 클립을 새 앵커로 기록하고 보정하지 않습니다."}),
            },
            "optional": {
                "project": ("H3_PROJECT", {"tooltip": "H3 Project Hub 의 project. 앵커 저장 위치."}),
                "chain_active": ("BOOLEAN", {"forceInput": True}),
                "trim_frames": ("INT", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "LATENT", "STRING")
    RETURN_NAMES = ("images", "latent", "report")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    # -------------------------------------------------------------- 앵커 저장
    @staticmethod
    def _anchor_path(project):
        root = getattr(project, "root", None) if project is not None else None
        if not root:
            import folder_paths
            root = os.path.join(folder_paths.get_output_directory(), "mmh3_color")
        os.makedirs(root, exist_ok=True)
        return os.path.join(root, _ANCHOR_NAME)

    def run(self, images, latent, vae, enabled, strength, max_luma_shift,
            max_saturation_change, lowpass_kernel, tail_steps, reset_anchor,
            project=None, chain_active=None, trim_frames=0):
        import torch

        if not enabled:
            return (images, latent, "[ColorCarry] 꺼짐 — 그대로 통과")

        trim = max(0, int(trim_frames or 0))
        T = int(images.shape[0])
        new_part = images[trim:] if trim < T else images
        path = self._anchor_path(project)
        cur = _stats(new_part)

        chain_on = bool(chain_active) if chain_active is not None else os.path.exists(path)
        if reset_anchor or not chain_on or not os.path.exists(path):
            why = ("reset_anchor" if reset_anchor else
                   "체인 비활성(첫 클립)" if not chain_on else "앵커 파일 없음")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"stats": cur, "frames": T}, f, ensure_ascii=False, indent=2)
            report = ("[ColorCarry] 앵커 기록 (%s) — 밝기 p50 %.3f, 채도 p50 %.3f → %s"
                      % (why, cur["luma"][1], cur["sat"][1], path))
            print(report)
            return (images, latent, report)

        with open(path, encoding="utf-8") as f:
            anchor = json.load(f)["stats"]

        offset = anchor["luma"][1] - cur["luma"][1]
        offset = max(-max_luma_shift, min(max_luma_shift, offset)) * strength
        ratio = anchor["sat"][1] / max(1e-4, cur["sat"][1])
        ratio = max(1.0 - max_saturation_change, min(1.0 + max_saturation_change, ratio))
        sat_mul = 1.0 + (ratio - 1.0) * strength

        weights = torch.ones(T)
        for k in range(min(trim, T)):
            weights[k] = _smoothstep((k + 0.5) / float(trim))
        out_images = _apply(images, weights, offset, sat_mul)

        lines = ["[ColorCarry] 보정 — 밝기 %+.4f, 채도 ×%.3f  (앵커 채도 %.3f / 현재 %.3f)"
                 % (offset, sat_mul, anchor["sat"][1], cur["sat"][1])]

        out_latent = latent
        try:
            out_latent, note = self._carry_latent(latent, vae, offset, sat_mul,
                                                  int(lowpass_kernel), int(tail_steps))
            lines.append("  latent: " + note)
        except Exception as e:  # latent 보정 실패는 치명적이지 않다
            lines.append("  latent: 건너뜀 — %s: %s" % (type(e).__name__, e))

        report = "\n".join(lines)
        print(report)
        return (out_images, out_latent, report)

    # -------------------------------------------------------------- latent 차이 보정
    @staticmethod
    def _carry_latent(latent, vae, offset, sat_mul, kernel, tail_steps):
        import torch
        import torch.nn.functional as F

        samples = latent["samples"]
        if _nested(samples):
            parts = list(samples.unbind())
            video = parts[0]
        else:
            parts, video = None, samples
        if video.ndim != 5:
            raise ValueError("영상 latent 가 5차원이 아님 %s" % (tuple(video.shape),))

        T = video.shape[2]
        start = 0 if tail_steps <= 0 else max(0, ((T - tail_steps) // 5) * 5)
        seg = video[:, :, start:]

        pix = vae.decode(seg)
        if pix.ndim == 5:
            pix = pix.reshape(-1, pix.shape[-3], pix.shape[-2], pix.shape[-1])
        weights = torch.ones(pix.shape[0])
        corr = _apply(pix, weights, offset, sat_mul)

        e_corr = vae.encode(corr[..., :3])
        e_orig = vae.encode(pix[..., :3])
        delta = (e_corr.float() - e_orig.float())
        if tuple(delta.shape) != tuple(seg.shape):
            raise ValueError("재인코딩 크기 %s ≠ 원본 %s" % (tuple(delta.shape), tuple(seg.shape)))

        k = max(1, kernel | 1)
        delta = F.avg_pool3d(delta, kernel_size=(1, k, k), stride=1,
                             padding=(0, k // 2, k // 2), count_include_pad=False)

        new_video = video.clone()
        new_video[:, :, start:] = seg + delta.to(device=seg.device, dtype=seg.dtype)

        out = dict(latent)
        if parts is not None:
            parts[0] = new_video
            out["samples"] = type(samples)(tuple(parts))
        else:
            out["samples"] = new_video
        return out, "스텝 %d~%d 보정 (차이 평균 절댓값 %.4f)" % (start, T - 1, float(delta.abs().mean()))
