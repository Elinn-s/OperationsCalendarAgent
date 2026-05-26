import calendar
import json
import re
import uuid
from datetime import date, datetime, timedelta

import streamlit as st
import streamlit.components.v1 as components

from app.db import generate_system_no, get_conn, init_db
from app.ui import apply_backend_style, page_header, section_title, top_nav

init_db()
st.set_page_config(page_title="预录信息", page_icon="📅", layout="wide")
apply_backend_style()
top_nav()
page_header(
    "预录信息",
    "预录已知活动、责任人和通告内容，在制定与发布节点到达前进行提醒。",
    "计划提醒 / 发布通告",
)

STATUSES = ["已预录", "待发布", "已取消"]
NOTICE_TYPE_OPTIONS = ["安全合规", "日常营运", "活动通知", "人事行政", "其他"]


def _parse_date(raw: str | None, fallback: date) -> date:
    if not raw:
        return fallback
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日", "%Y.%m.%d"):
        try:
            return datetime.strptime(str(raw)[:10], fmt).date()
        except ValueError:
            continue
    return fallback


def _extract_labeled_value(text: str, labels: list[str]) -> str:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?:{label_pattern})\s*[:：]\s*([^\n，,；;]+)", text)
    return match.group(1).strip() if match else ""


def _extract_date(text: str) -> date | None:
    for pattern, fmt in [
        (r"\d{4}-\d{1,2}-\d{1,2}", "%Y-%m-%d"),
        (r"\d{4}/\d{1,2}/\d{1,2}", "%Y/%m/%d"),
        (r"\d{4}年\d{1,2}月\d{1,2}日", "%Y年%m月%d日"),
    ]:
        match = re.search(pattern, text)
        if match:
            return datetime.strptime(match.group(0), fmt).date()

    match = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if match:
        return date(date.today().year, int(match.group(1)), int(match.group(2)))
    return None


def _extract_plan_fields(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    activity_name = _extract_labeled_value(text, ["活动名称", "活动", "主题", "标题"])
    if not activity_name and lines:
        activity_name = re.sub(r"^(关于|请|需|计划)", "", lines[0]).strip(" ：:，,。")

    owner = _extract_labeled_value(text, ["责任人", "负责人", "owner", "联系人"])
    publish_date_text = _extract_labeled_value(text, ["发布日期", "计划发布日期", "发布时间", "发出时间", "发出日期"])
    planned_publish_date = _extract_date(publish_date_text or text) or (date.today() + timedelta(days=14))

    return {
        "activity_name": activity_name,
        "owner": owner,
        "notification_content": text.strip(),
        "planned_publish_date": planned_publish_date,
        "make_reminder_date": planned_publish_date - timedelta(days=14),
        "publish_reminder_date": planned_publish_date - timedelta(days=7),
        "status": "已预录",
    }


def _status_index(status: str | None) -> int:
    return STATUSES.index(status) if status in STATUSES else 0


def _infer_notice_type(*values: str | None) -> str:
    text = " ".join(value or "" for value in values)
    rules = [
        ("安全合规", ["安全", "消防", "防火", "卫生", "检查", "合规", "演练", "风险"]),
        ("活动通知", ["活动", "促销", "节日", "会员", "营销", "陈列"]),
        ("人事行政", ["员工", "培训", "排班", "考勤", "人事", "行政", "入职"]),
        ("日常营运", ["盘点", "营运", "门店", "库存", "物料", "配送", "营业"]),
    ]
    for notice_type, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return notice_type
    return "其他"


def _reminder_status(plan: dict, today: date) -> str:
    if plan["status"] in ("已发布", "已取消"):
        return "已结束"
    if plan["status"] == "待发布":
        return "待发布"
    if plan["status"] == "已预录":
        return "已预录"
    publish_date = _parse_date(plan["publish_reminder_date"], today + timedelta(days=14))
    make_date = _parse_date(plan["make_reminder_date"], today + timedelta(days=14))
    if publish_date <= today:
        return "待发布"
    if make_date <= today:
        return "待制定"
    return "未到提醒"


def _add_calendar_event(
    events: dict[str, list[dict]],
    raw_date: str | None,
    label: str,
    plan_id: int,
    activity_name: str,
    owner: str | None,
) -> None:
    if not raw_date:
        return
    try:
        event_date = date.fromisoformat(str(raw_date)[:10]).isoformat()
    except ValueError:
        return
    events.setdefault(event_date, []).append(
        {"plan_id": plan_id, "label": label, "activity_name": activity_name, "owner": owner or "未填写"}
    )


def _event_display_label(event: dict) -> str:
    color_prefix = {
        "制定": "🟡 制定",
        "发布": "🔴 发布",
        "发出": "🔵 发出",
    }
    return f"{color_prefix.get(event['label'], event['label'])} {event['activity_name']}|{event['owner']}"


def _show_plan_summary(label: str, rows: list[dict]) -> None:
    with st.popover(f"{label}：{len(rows)}", use_container_width=True):
        st.metric(label, len(rows))
        if not rows:
            st.info("暂无记录。")
            return
        for row in rows:
            button_label = f"{row['activity_name']} | {row['owner'] or '未填写'}"
            if st.button(
                button_label,
                key=f"summary_{label}_{row['id']}",
                use_container_width=True,
            ):
                st.session_state["selected_plan_id"] = row["id"]
                st.session_state["pre_reg_detail_notice"] = f"已打开「{row['activity_name']}」的详情。"
                st.session_state.pop("pending_delete_plan_id", None)
                st.rerun()


section_title("预录总览")
today = date.today()
with get_conn() as conn:
    summary_plans = conn.execute(
        "SELECT * FROM plans WHERE status NOT IN ('已发布', '已取消')"
        " ORDER BY planned_publish_date IS NULL, planned_publish_date, created_at DESC"
    ).fetchall()

summary_records = [dict(plan) for plan in summary_plans]
summary_pre_registered = [plan for plan in summary_records if plan["status"] == "已预录"]
summary_pending_publish = [
    plan for plan in summary_records
    if plan["status"] == "待发布"
]

sum1, sum2 = st.columns(2)
with sum1:
    _show_plan_summary("已预录", summary_pre_registered)
with sum2:
    _show_plan_summary("待发布", summary_pending_publish)

raw_text = st.text_area(
    "粘贴活动/通告内容",
    placeholder="例：活动名称：春节物料配货\n责任人：张三\n发布日期：2026-01-20\n通告内容：提醒各门店完成物料盘点与配货准备。",
    height=140,
)

if st.button("智能识别"):
    if not raw_text.strip():
        st.error("请先粘贴内容。")
    else:
        st.session_state["pre_reg_fields"] = _extract_plan_fields(raw_text)
        st.session_state["pre_reg_form_version"] = st.session_state.get("pre_reg_form_version", 0) + 1
        st.rerun()

fields = st.session_state.get(
    "pre_reg_fields",
    _extract_plan_fields(raw_text) if raw_text.strip() else _extract_plan_fields(""),
)
form_version = st.session_state.get("pre_reg_form_version", 0)

section_title("新增预录")
with st.form("pre_registration_form"):
    c1, c2 = st.columns(2)
    activity_name = c1.text_input("活动名称 *", value=fields["activity_name"], key=f"activity_{form_version}")
    owner = c2.text_input("责任人", value=fields["owner"], key=f"owner_{form_version}")
    content = st.text_area(
        "通告内容 / 备忘",
        value=fields["notification_content"],
        height=120,
        key=f"content_{form_version}",
    )

    d1, d2, d3 = st.columns(3)
    planned_publish_date = d1.date_input("计划发布日期", value=fields["planned_publish_date"], key=f"publish_{form_version}")
    make_reminder_date = d2.date_input("制定提醒日（默认提前 2 周）", value=fields["make_reminder_date"], key=f"make_{form_version}")
    publish_reminder_date = d3.date_input("发布提醒日（默认提前 1 周）", value=fields["publish_reminder_date"], key=f"pub_remind_{form_version}")

    save_pre_col, save_draft_col = st.columns(2)
    saved_pre_reg = save_pre_col.form_submit_button("保存预录", type="primary", use_container_width=True)
    saved_draft = save_draft_col.form_submit_button("保存草稿（待发布）", use_container_width=True)

if saved_pre_reg or saved_draft:
    if not activity_name.strip():
        st.error("活动名称不能为空。")
    else:
        status = "已预录" if saved_pre_reg else "待发布"
        now = datetime.now().isoformat()
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO plans
                   (activity_name, notification_content, planned_publish_date,
                    make_reminder_date, publish_reminder_date, owner, status,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    activity_name.strip(),
                    content.strip(),
                    planned_publish_date.isoformat(),
                    make_reminder_date.isoformat(),
                    publish_reminder_date.isoformat(),
                    owner.strip(),
                    status,
                    now,
                    now,
                ),
            )
        st.session_state.pop("pre_reg_fields", None)
        st.session_state["pre_reg_form_version"] = st.session_state.get("pre_reg_form_version", 0) + 1
        st.success("预录信息已保存。" if status == "已预录" else "草稿已保存为待发布。")
        st.rerun()

st.divider()
section_title("可视化日历")

year_col, month_col = st.columns(2)
calendar_year = year_col.selectbox("年份", list(range(today.year - 2, today.year + 3)), index=2)
calendar_month = month_col.selectbox(
    "月份",
    list(range(1, 13)),
    index=today.month - 1,
    format_func=lambda month: f"{month} 月",
)

with get_conn() as conn:
    plans = conn.execute(
        "SELECT * FROM plans WHERE status NOT IN ('已发布', '已取消')"
        " ORDER BY planned_publish_date IS NULL, planned_publish_date, created_at DESC"
    ).fetchall()

plan_records = [dict(plan) for plan in plans]
plans_by_id = {plan["id"]: plan for plan in plan_records}
calendar_events: dict[str, list[dict]] = {}
for plan in plan_records:
    _add_calendar_event(
        calendar_events,
        plan["make_reminder_date"],
        "制定",
        plan["id"],
        plan["activity_name"],
        plan["owner"],
    )
    _add_calendar_event(
        calendar_events,
        plan["publish_reminder_date"],
        "发布",
        plan["id"],
        plan["activity_name"],
        plan["owner"],
    )
    _add_calendar_event(
        calendar_events,
        plan["planned_publish_date"],
        "发出",
        plan["id"],
        plan["activity_name"],
        plan["owner"],
    )

weekday_cols = st.columns(7)
for col, weekday in zip(weekday_cols, ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]):
    col.markdown(f"**{weekday}**")

st.caption("🟡 待制定 / 制定提醒　🔴 待发布 / 发布提醒　🔵 计划发出")

for week in calendar.Calendar(firstweekday=0).monthdatescalendar(calendar_year, calendar_month):
    cols = st.columns(7)
    for col, day in zip(cols, week):
        day_key = day.isoformat()
        in_month = day.month == calendar_month
        events = calendar_events.get(day_key, [])
        col.markdown(f"**{day.day}**" if in_month else f"_{day.day}_")
        for index, event in enumerate(events[:3]):
            if col.button(
                _event_display_label(event),
                key=f"calendar_event_{day_key}_{event['plan_id']}_{event['label']}_{index}",
                use_container_width=True,
            ):
                st.session_state["selected_plan_id"] = event["plan_id"]
                st.session_state.pop("pending_delete_plan_id", None)
                st.rerun()
        if len(events) > 3:
            col.caption(f"还有 {len(events) - 3} 项")

st.divider()
st.markdown('<div id="pre-reg-detail-anchor"></div>', unsafe_allow_html=True)
section_title("预录信息详情")
detail_notice = st.session_state.pop("pre_reg_detail_notice", None)
if detail_notice:
    st.success(detail_notice)
    components.html(
        """
        <script>
        const anchor = window.parent.document.getElementById("pre-reg-detail-anchor");
        if (anchor) {
            anchor.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        </script>
        """,
        height=0,
    )
selected_plan_id = st.session_state.get("selected_plan_id")
selected_plan = plans_by_id.get(selected_plan_id)

if not plan_records:
    st.info("暂无预录信息。")
    st.stop()

if not selected_plan:
    st.info("点击日历上的活动名称后，可在这里查看、修改或删除预录信息。")
    st.stop()

detail_cols = st.columns(3)
detail_cols[0].metric("活动名称", selected_plan["activity_name"])
detail_cols[1].metric("责任人", selected_plan["owner"] or "未填写")
detail_cols[2].metric("提醒状态", _reminder_status(selected_plan, today))
date_cols = st.columns(3)
date_cols[0].markdown(f"**计划发布日期** {selected_plan['planned_publish_date'] or '—'}")
date_cols[1].markdown(f"**制定提醒日** {selected_plan['make_reminder_date'] or '—'}")
date_cols[2].markdown(f"**发布提醒日** {selected_plan['publish_reminder_date'] or '—'}")
st.markdown(f"**通告内容 / 备忘** {selected_plan['notification_content'] or '—'}")

with st.expander("发布为正式通告"):
    if selected_plan["status"] == "已发布":
        st.info("此预录信息已发布。")
    elif selected_plan["status"] == "已取消":
        st.info("已取消的预录信息不能发布。")
    else:
        publish_default = _parse_date(selected_plan["planned_publish_date"], today)
        inferred_notice_type = _infer_notice_type(selected_plan["activity_name"], selected_plan["notification_content"])
        with st.form(f"publish_plan_{selected_plan['id']}"):
            p1, p2 = st.columns(2)
            publish_system_no = p1.text_input("系统编号", value=generate_system_no(), disabled=True)
            publish_doc_ref = p2.text_input("档案编号（原始文件编号，可为空）")
            publish_type = p1.selectbox(
                "通告类型",
                NOTICE_TYPE_OPTIONS,
                index=NOTICE_TYPE_OPTIONS.index(inferred_notice_type),
            )
            publish_department = p2.text_input("发文部门")
            publish_title = st.text_input("通告标题 *", value=selected_plan["activity_name"])
            publish_target_scope = st.text_input("适用对象 / 范围")
            publish_content = st.text_area(
                "通告内容",
                value=selected_plan["notification_content"] or "",
                height=160,
            )

            d1, d2 = st.columns(2)
            publish_effective_start = d1.date_input("执行开始时间", value=publish_default)
            no_effective_end = d2.checkbox("无执行截止日期")
            publish_effective_end = None
            if not no_effective_end:
                publish_effective_end = d2.date_input("执行截止时间", value=publish_default + timedelta(days=30))

            published = st.form_submit_button("发布通告", type="primary")

        if published:
            if not publish_title.strip():
                st.error("通告标题不能为空。")
            else:
                nid = str(uuid.uuid4())
                now = datetime.now().isoformat()
                doc_ref = publish_doc_ref.strip()
                with get_conn() as conn:
                    conn.execute(
                        """INSERT INTO notifications
                           (notification_id, doc_ref, system_no, notice_type, department, drafter, reviewer, approver,
                            title, purpose, target_scope, effective_start, effective_end,
                            status, tags, file_path, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            nid,
                            doc_ref,
                            publish_system_no,
                            publish_type,
                            publish_department.strip(),
                            selected_plan["owner"] or "",
                            "",
                            "",
                            publish_title.strip(),
                            publish_content.strip(),
                            publish_target_scope.strip(),
                            publish_effective_start.isoformat(),
                            publish_effective_end.isoformat() if publish_effective_end else None,
                            "执行中",
                            json.dumps(["预录发布"], ensure_ascii=False),
                            "",
                            now,
                            now,
                        ),
                    )
                    conn.execute(
                        "UPDATE plans SET status = '已发布', linked_notification_id = ?, updated_at = ? WHERE id = ?",
                        (nid, now, selected_plan["id"]),
                    )
                    conn.execute(
                        "INSERT INTO audit_log (notification_id, action, detail, timestamp) VALUES (?, ?, ?, ?)",
                        (nid, "预录发布", f"预录活动: {selected_plan['activity_name']}", now),
                    )
                st.success(f"已发布为正式通告，系统编号：`{publish_system_no}`")
                st.session_state.pop("selected_plan_id", None)
                st.session_state.pop("pending_delete_plan_id", None)
                st.session_state["pre_reg_detail_notice"] = f"已发布为正式通告，系统编号：{publish_system_no}。"
                st.rerun()

with st.expander("修改预录信息"):
    publish_default = _parse_date(selected_plan["planned_publish_date"], today + timedelta(days=14))
    make_default = _parse_date(selected_plan["make_reminder_date"], publish_default - timedelta(days=14))
    publish_reminder_default = _parse_date(selected_plan["publish_reminder_date"], publish_default - timedelta(days=7))

    with st.form(f"edit_plan_{selected_plan['id']}"):
        e1, e2 = st.columns(2)
        edit_activity_name = e1.text_input("活动名称 *", value=selected_plan["activity_name"])
        edit_owner = e2.text_input("责任人", value=selected_plan["owner"] or "")
        edit_content = st.text_area("通告内容 / 备忘", value=selected_plan["notification_content"] or "", height=120)

        date1, date2, date3 = st.columns(3)
        edit_planned_publish_date = date1.date_input("计划发布日期", value=publish_default)
        edit_make_reminder_date = date2.date_input("制定提醒日", value=make_default)
        edit_publish_reminder_date = date3.date_input("发布提醒日", value=publish_reminder_default)
        edit_status = st.selectbox("状态", STATUSES, index=_status_index(selected_plan["status"]))

        updated = st.form_submit_button("保存修改", type="primary")

    if updated:
        if not edit_activity_name.strip():
            st.error("活动名称不能为空。")
        else:
            now = datetime.now().isoformat()
            with get_conn() as conn:
                conn.execute(
                    """UPDATE plans
                       SET activity_name = ?, notification_content = ?, planned_publish_date = ?,
                           make_reminder_date = ?, publish_reminder_date = ?, owner = ?,
                           status = ?, updated_at = ?
                       WHERE id = ?""",
                    (
                        edit_activity_name.strip(),
                        edit_content.strip(),
                        edit_planned_publish_date.isoformat(),
                        edit_make_reminder_date.isoformat(),
                        edit_publish_reminder_date.isoformat(),
                        edit_owner.strip(),
                        edit_status,
                        now,
                        selected_plan["id"],
                    ),
                )
            st.session_state["pre_reg_detail_notice"] = "预录信息已更新。"
            st.rerun()

with st.expander("删除预录信息"):
    if st.session_state.get("pending_delete_plan_id") == selected_plan["id"]:
        st.warning(f"确认删除「{selected_plan['activity_name']}」吗？")
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button("确认删除"):
            with get_conn() as conn:
                conn.execute("DELETE FROM plans WHERE id = ?", (selected_plan["id"],))
            st.session_state.pop("pending_delete_plan_id", None)
            st.success("预录信息已删除。")
            st.rerun()
        if cancel_col.button("取消"):
            st.session_state.pop("pending_delete_plan_id", None)
            st.rerun()
    elif st.button("删除当前预录信息"):
        st.session_state["pending_delete_plan_id"] = selected_plan["id"]
        st.rerun()
