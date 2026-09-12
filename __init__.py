# -*- coding: utf-8 -*-
"""
ComfyUI-MinimaxH3-PromptDirector
--------------------------------
Ollama-backed prompt generator for the MiniMax H3 video model / DaSiWa MiniMaxH3Director.

Wire `prompt` into MiniMaxH3Director -> external_prompt_overwrite.
"""

from .nodes.prompt_writer import (
    MMH3_OllamaPromptWriter,
    MMH3_PromptValidator,
    MMH3_ImageDescribe,
    MMH3_StyleDirective,
)
from .nodes.shot_builder import MMH3_ShotBuilder
from .nodes.shot_settings import MMH3_ShotSettings
from .nodes.kill_switch import MMH3_KillSwitch
from .nodes.prompt_freeze import MMH3_PromptFreeze
from .nodes.assets import MMH3_AssetSave, MMH3_AssetLoad

NODE_CLASS_MAPPINGS = {
    "MMH3_ShotSettings": MMH3_ShotSettings,
    "MMH3_ShotBuilder": MMH3_ShotBuilder,
    "MMH3_OllamaPromptWriter": MMH3_OllamaPromptWriter,
    "MMH3_PromptValidator": MMH3_PromptValidator,
    "MMH3_ImageDescribe": MMH3_ImageDescribe,
    "MMH3_StyleDirective": MMH3_StyleDirective,
    "MMH3_KillSwitch": MMH3_KillSwitch,
    "MMH3_PromptFreeze": MMH3_PromptFreeze,
    "MMH3_AssetSave": MMH3_AssetSave,
    "MMH3_AssetLoad": MMH3_AssetLoad,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MMH3_ShotSettings": "🎬 MiniMax H3 Shot Settings",
    "MMH3_ShotBuilder": "🎬 MiniMax H3 Shot Builder",
    "MMH3_OllamaPromptWriter": "🎬 MiniMax H3 Prompt Writer (Ollama)",
    "MMH3_PromptValidator": "🎬 MiniMax H3 Prompt Validator",
    "MMH3_ImageDescribe": "🎬 MiniMax H3 Image Describe (Ollama)",
    "MMH3_StyleDirective": "🎬 MiniMax H3 Style Directive",
    "MMH3_KillSwitch": "☠️ Unload Everything (Kill Switch)",
    "MMH3_PromptFreeze": "🔒 MiniMax H3 Prompt Freeze",
    "MMH3_AssetSave": "📚 MiniMax H3 Asset Save",
    "MMH3_AssetLoad": "📚 MiniMax H3 Asset Load",
}

# 라이브러리 패널이 쓰는 HTTP 라우트. ComfyUI 서버가 없으면 조용히 아무 일도
# 하지 않으므로 테스트에서 import 해도 안전하다.
from . import routes  # noqa: E402,F401

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
