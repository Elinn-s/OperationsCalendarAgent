from __future__ import annotations

import json
import re
from typing import Any

FIELD_ALIASES: dict[str, list[str]] = {
    "doc_ref": ["doc_ref", "档案编号", "檔案編號", "archive_number"],
    "system_no": ["system_no", "单号", "system_number"],
    "issuer": ["issuer", "发布人", "發佈人", "發怖人", "发布部门", "发文部门", "發文部門", "department", "dept"],
    "owner": ["owner", "负责人", "責任人", "责任人", "联系人", "聯絡人", "拟稿人", "擬稿人", "drafter"],
    "owner_role": ["owner_role", "负责人角色", "責任人角色", "角色", "role"],
    "impact_store": ["impact_store", "影响门店", "影響門店", "适用门店", "適用門店", "门店", "門店", "store"],
    "impact_region": ["impact_region", "影响区域", "影響區域", "适用区域", "適用區域", "区域", "區域", "region"],
    "impact_role": ["impact_role", "影响角色", "影響角色", "适用角色", "適用角色", "适用对象", "適用對象", "role", "target_role"],
    "deadline": ["deadline", "截止日期", "回执截止", "回執截止", "完成截止", "执行截止时间", "執行截止時間", "截止时间", "截止時間"],
    "department": ["department", "发文部门", "發文部門", "dept"],
    "drafter": ["drafter", "拟稿人", "擬稿人"],
    "reviewer": ["reviewer", "复核人", "覆核人"],
    "approver": ["approver", "审核人", "審核人"],
    "title": ["title", "通告标题", "通告標題", "标题", "標題"],
    "description": ["description", "描述", "通告描述", "说明", "說明", "内容摘要", "內容摘要", "通告目的", "目的"],
    "purpose": ["purpose", "通告目的", "目的"],
    "target_scope": ["target_scope", "适用范围", "適用範圍", "scope"],
    "effective_start": ["effective_start", "执行开始时间", "執行開始時間", "start_date", "开始时间", "開始時間"],
    "effective_end": ["effective_end", "执行截止时间", "執行截止時間", "end_date", "截止时间", "截止時間", "deadline"],
    "archive_until": ["archive_until", "电子存档截至", "電子存檔截至", "archive_date"],
    "contacts": ["contacts", "联系人", "聯絡人", "contact_list"],
}

CANONICAL_FIELDS = list(FIELD_ALIASES)


def unwrap_json_payload(outputs: dict[str, Any]) -> dict[str, Any]:
    text = outputs.get("text", "")
    if not text:
        return outputs
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", str(text).strip())
    cleaned = re.sub(r"\n?\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return {**outputs, **parsed}
    except (json.JSONDecodeError, ValueError):
        pass
    return outputs


def parse_json_object(raw_text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
    cleaned = re.sub(r"\n?\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("LLM response is not a JSON object")
    return parsed


def normalize_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    outputs = unwrap_json_payload(outputs)
    result: dict[str, Any] = {}
    for canonical, aliases in FIELD_ALIASES.items():
        for key in aliases:
            val = outputs.get(key)
            if val and str(val).lower() not in ("null", "none", ""):
                if isinstance(val, list):
                    result[canonical] = "、".join(v if isinstance(v, str) else str(v) for v in val)
                else:
                    result[canonical] = str(val)
                break
        else:
            result[canonical] = ""
    result["_raw"] = outputs
    return result
