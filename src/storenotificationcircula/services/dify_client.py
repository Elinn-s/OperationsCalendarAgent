import os
import requests
from dotenv import load_dotenv

load_dotenv()


def _secret(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key, "")
        except Exception:
            pass
    return val


def _get_api_key() -> str:
    return _secret("DIFY_API_KEY")


def _get_base_url() -> str:
    return _secret("DIFY_BASE_URL").rstrip("/")


# 映射标准名称
_FIELD_ALIASES: dict[str, list[str]] = {
    "doc_ref": ["doc_ref", "档案编号", "archive_number"],
    "system_no": ["system_no", "单号", "system_number"],
    "issuer": ["issuer", "发布人", "發怖人", "发布部门", "发文部门", "department", "dept"],
    "owner": ["owner", "负责人", "責任人", "责任人", "联系人", "拟稿人", "drafter"],
    "owner_role": ["owner_role", "负责人角色", "角色", "role"],
    "impact_store": ["impact_store", "影响门店", "适用门店", "门店", "store"],
    "impact_region": ["impact_region", "影响区域", "适用区域", "区域", "region"],
    "impact_role": ["impact_role", "影响角色", "适用角色", "适用对象", "role", "target_role"],
    "deadline": ["deadline", "截止日期", "回执截止", "完成截止", "执行截止时间", "截止时间"],
    "department": ["department", "发文部门", "dept"],
    "drafter": ["drafter", "拟稿人"],
    "reviewer": ["reviewer", "复核人"],
    "approver": ["approver", "审核人"],
    "title": ["title", "通告标题", "标题"],
    "description": ["description", "描述", "通告描述", "说明", "内容摘要", "通告目的", "目的"],
    "purpose": ["purpose", "通告目的", "目的"],
    "target_scope": ["target_scope", "适用范围", "scope"],
    "effective_start": ["effective_start", "执行开始时间", "start_date", "开始时间"],
    "effective_end": [
        "effective_end",
        "执行截止时间",
        "end_date",
        "截止时间",
        "deadline",
    ],
    "archive_until": ["archive_until", "电子存档截至", "archive_date"],
    "contacts": ["contacts", "联系人", "contact_list"],
}


def _unwrap(outputs: dict) -> dict:
    """Dify 有时把所有字段塞进 outputs['text'] 的 JSON 字符串里（含 markdown 代码块），解开它。"""
    import json, re

    text = outputs.get("text", "")
    if not text:
        return outputs
    # 去掉 ```json ... ``` 包裹
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return {**outputs, **parsed}
    except (json.JSONDecodeError, ValueError):
        pass
    return outputs


def _resolve(outputs: dict) -> dict:
    outputs = _unwrap(outputs)
    result = {}
    for canonical, aliases in _FIELD_ALIASES.items():
        for key in aliases:
            val = outputs.get(key)
            if val and str(val).lower() not in ("null", "none", ""):
                if isinstance(val, list):
                    result[canonical] = "、".join(
                        v if isinstance(v, str) else str(v) for v in val
                    )
                else:
                    result[canonical] = str(val)
                break
        else:
            result[canonical] = ""
    result["_raw"] = outputs
    return result


_MAX_TEXT_LEN = 4000  # Dify 对输入变量有大小限制，截断保险起见


def extract_fields(pdf_text: str) -> dict:
    truncated = pdf_text[:_MAX_TEXT_LEN]
    resp = requests.post(
        f"{_get_base_url()}/workflows/run",
        headers={
            "Authorization": f"Bearer {_get_api_key()}",
            "Content-Type": "application/json",
        },
        json={
            "inputs": {"pdf_text": truncated},
            "response_mode": "blocking",
            "user": "demo-user",
        },
        timeout=90,
    )
    if not resp.ok:
        raise RuntimeError(f"Dify {resp.status_code}：{resp.text}")
    outputs = resp.json().get("data", {}).get("outputs", {})
    return _resolve(outputs)
