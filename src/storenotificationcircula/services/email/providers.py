from __future__ import annotations

from typing import Any

EMAIL_PRESETS: dict[str, dict[str, Any]] = {
    "163.com": {
        "provider": "网易 163 邮箱",
        "host": "smtp.163.com",
        "port": 465,
        "use_ssl": 1,
        "use_tls": 0,
    },
    "126.com": {
        "provider": "网易 126 邮箱",
        "host": "smtp.126.com",
        "port": 465,
        "use_ssl": 1,
        "use_tls": 0,
    },
    "yeah.net": {
        "provider": "网易 Yeah 邮箱",
        "host": "smtp.yeah.net",
        "port": 465,
        "use_ssl": 1,
        "use_tls": 0,
    },
    "qq.com": {
        "provider": "QQ 邮箱",
        "host": "smtp.qq.com",
        "port": 465,
        "use_ssl": 1,
        "use_tls": 0,
    },
    "foxmail.com": {
        "provider": "Foxmail",
        "host": "smtp.qq.com",
        "port": 465,
        "use_ssl": 1,
        "use_tls": 0,
    },
    "exmail.qq.com": {
        "provider": "腾讯企业邮",
        "host": "smtp.exmail.qq.com",
        "port": 465,
        "use_ssl": 1,
        "use_tls": 0,
    },
    "outlook.com": {
        "provider": "Outlook",
        "host": "smtp.office365.com",
        "port": 587,
        "use_ssl": 0,
        "use_tls": 1,
    },
    "hotmail.com": {
        "provider": "Hotmail",
        "host": "smtp.office365.com",
        "port": 587,
        "use_ssl": 0,
        "use_tls": 1,
    },
    "live.com": {
        "provider": "Microsoft 邮箱",
        "host": "smtp.office365.com",
        "port": 587,
        "use_ssl": 0,
        "use_tls": 1,
    },
    "office365.com": {
        "provider": "Office 365",
        "host": "smtp.office365.com",
        "port": 587,
        "use_ssl": 0,
        "use_tls": 1,
    },
    "gmail.com": {
        "provider": "Gmail",
        "host": "smtp.gmail.com",
        "port": 465,
        "use_ssl": 1,
        "use_tls": 0,
    },
}


def _email_domain(email: str) -> str:
    value = (email or "").strip().lower()
    if "@" not in value:
        return ""
    return value.rsplit("@", 1)[1]


def detect_email_provider(email: str) -> dict[str, Any]:
    domain = _email_domain(email)
    preset = EMAIL_PRESETS.get(domain)
    if not preset:
        return {
            "matched": False,
            "email": (email or "").strip().lower(),
            "domain": domain,
            "message": "无法自动识别邮箱服务商，请手动填写 SMTP 配置。",
        }
    return {
        "matched": True,
        "email": (email or "").strip().lower(),
        "domain": domain,
        **preset,
        "message": f"已识别为 {preset['provider']}，SMTP 配置已自动填充。",
    }
