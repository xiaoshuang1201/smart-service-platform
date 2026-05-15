"输入守卫 — 提示注入检测、越狱防御"

from __future__ import annotations
import re
from dataclasses import dataclass

from src.config import config
from src.observability import logger
from src.observability.metrics import input_guard_blocks_total


INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+instructions?",
    r"(?i)you\s+are\s+now\s+(DAN|jailbreak|GPT|free)",
    r"(?i)pretend\s+(you\s+are|to\s+be)",
    r"(?i)disregard\s+(all\s+)?(previous|prior|earlier)",
    r"(?i)forget\s+(everything|all)\s+(you|about)",
    r"(?i)system\s*prompt\s*:",
    r"(?i)<\|im_start\|>",
    r"(?i)<\|im_end\|>",
    r"(?i)你是一个.*新的.*角色",
    r"(?i)从现在开始.*你是",
    r"(?i)忘记.*之前.*所有",
    r"(?i)忽略.*系统.*提示",
]

ZERO_WIDTH_CHARS = re.compile(r"[​‌‍‎‏⁠⁡⁢⁣⁤﻿]")
UNICODE_HOMOGLYPH_DETECT = re.compile(
    r"[аеорсухіј]",  # Cyrillic lookalikes
)


@dataclass
class InputCheckResult:
    allowed: bool
    reason: str = ""
    sanitized: str = ""


class InputGuard:
    """输入安全检查"""

    def check(self, text: str, user_id: str | None = None) -> InputCheckResult:
        if not config.security.input_guard_enabled:
            return InputCheckResult(allowed=True, sanitized=text)

        # 1. Length check
        if len(text) > config.security.input_guard_max_length:
            input_guard_blocks_total.labels(reason="length_exceeded").inc()
            return InputCheckResult(allowed=False, reason="message_too_long")

        # 2. Empty check
        if not text or not text.strip():
            input_guard_blocks_total.labels(reason="empty").inc()
            return InputCheckResult(allowed=False, reason="empty_message")

        # 3. Zero-width character check
        if ZERO_WIDTH_CHARS.search(text):
            input_guard_blocks_total.labels(reason="hidden_chars").inc()
            logger.warning("Hidden characters detected in input", user_id=user_id)
            text = ZERO_WIDTH_CHARS.sub("", text)

        # 4. Prompt injection check
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, text):
                input_guard_blocks_total.labels(reason="injection_detected").inc()
                logger.warning(
                    "Prompt injection detected",
                    user_id=user_id,
                    pattern=pattern,
                )
                return InputCheckResult(
                    allowed=False,
                    reason="injection_detected",
                )

        # 5. Unicode homoglyph check
        if UNICODE_HOMOGLYPH_DETECT.search(text):
            input_guard_blocks_total.labels(reason="homoglyph_detected").inc()
            logger.warning("Unicode homoglyphs detected", user_id=user_id)

        return InputCheckResult(allowed=True, sanitized=text)
