"PII 自动检测与脱敏"

from __future__ import annotations
import re

PHONE_PATTERN = re.compile(r"(1[3-9]\d{9})")
EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
ID_CARD_PATTERN = re.compile(r"(\d{17}[\dXx])")
BANK_CARD_PATTERN = re.compile(r"(\d{16,19})")


def mask_phone(phone: str) -> str:
    if len(phone) >= 7:
        return phone[:3] + "****" + phone[-4:]
    return phone


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def mask_id_card(id_num: str) -> str:
    if len(id_num) >= 8:
        return id_num[:4] + "****" + id_num[-4:]
    return id_num


def mask_bank_card(card: str) -> str:
    if len(card) >= 8:
        return card[:4] + "****" + card[-4:]
    return card


def scan_and_mask(text: str) -> str:
    """扫描文本，自动脱敏所有 PII"""
    text = PHONE_PATTERN.sub(lambda m: mask_phone(m.group(1)), text)
    text = EMAIL_PATTERN.sub(lambda m: mask_email(m.group(1)), text)
    text = ID_CARD_PATTERN.sub(lambda m: mask_id_card(m.group(1)), text)
    text = BANK_CARD_PATTERN.sub(lambda m: mask_bank_card(m.group(1)), text)
    return text


class PIIMasker:
    """PII 脱敏过滤器 — 用于日志和追踪输出"""

    @staticmethod
    def mask_dict(data: dict) -> dict:
        masked = {}
        sensitive_keys = {"phone", "email", "id_card", "bank_card", "api_key", "password", "secret", "token", "address"}
        for k, v in data.items():
            if any(s in k.lower() for s in sensitive_keys):
                masked[k] = "***REDACTED***"
            elif isinstance(v, str):
                masked[k] = scan_and_mask(v)
            elif isinstance(v, dict):
                masked[k] = PIIMasker.mask_dict(v)
            elif isinstance(v, list):
                masked[k] = [
                    PIIMasker.mask_dict(item) if isinstance(item, dict) else item
                    for item in v
                ]
            else:
                masked[k] = v
        return masked

    @staticmethod
    def mask_text(text: str) -> str:
        return scan_and_mask(text)
