#streamlit首页 overview数据查询 指标整理 明细展示
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import streamlit as st

from storenotificationcircula.db.database import get_conn, init_db
from storenotificationcircula.ui.overview_dashboard import render_dashboard_html
from storenotificationcircula.ui.streamlit_ui import apply_backend_style, top_nav

init_db()

st.set_page_config(
    page_title="营运概况",
    page_icon="📢",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _get(row: Any, key: str, default: str = "") -> Any:
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


def _safe_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _short_date(value: str | None) -> str:
    parsed = _safe_date(value)
    return parsed.strftime("%m-%d") if parsed else "未设置"


def _notice_name(row: Any) -> str:
    return _get(row, "title") or _get(row, "doc_ref") or "(无标题)"


def _notice_table(rows: list[Any]) -> list[dict[str, str]]:
    return [
        {
            "系统编号": _get(row, "system_no") or "未编号",
            "档案编号": _get(row, "doc_ref") or "无",
            "标题": _notice_name(row),
            "类型": _get(row, "notice_type") or "其他",
            "部门": _get(row, "department") or "未填",
            "状态": _get(row, "status") or "未填",
            "执行截止": _short_date(_get(row, "effective_end")),
        }
        for row in rows
    ]


today = date.today()
week_days = [today + timedelta(days=offset) for offset in range(7)]
three_days_later = today + timedelta(days=3)

with get_conn() as conn:
    notices = conn.execute(
        """
        SELECT title, doc_ref, system_no, notice_type, department, status, effective_end, created_at
        FROM notifications
        ORDER BY created_at DESC
        """
    ).fetchall()
    plans = conn.execute(
        """
        SELECT activity_name, owner, status, make_reminder_date, publish_reminder_date, planned_publish_date
        FROM plans
        WHERE status NOT IN ('已发布', '已取消')
        ORDER BY COALESCE(publish_reminder_date, make_reminder_date, planned_publish_date)
        """
    ).fetchall()

running = [row for row in notices if _get(row, "status") == "执行中"]
overdue = [row for row in notices if _get(row, "status") == "已截止"]
due_soon = [
    row
    for row in running
    if (end_date := _safe_date(_get(row, "effective_end"))) and today <= end_date <= three_days_later
]

kpi_data = [
    (
        "通告总数",
        len(notices),
        "数据库实时统计",
        "#1a1c2e",
    ),
    (
        "执行中",
        len(running),
        "邮箱回执待接入",
        "#16a34a",
    ),
    (
        "3天内截止",
        len(due_soon),
        "需跟进",
        "#b45309",
    ),
    (
        "已截止",
        len(overdue),
        "按执行截止自动更新",
        "#dc2626",
    ),
]

week_events: dict[str, list[tuple[str, str, str]]] = {day.isoformat(): [] for day in week_days}
for row in running:
    end_date = _get(row, "effective_end")
    if end_date in week_events:
        week_events[end_date].append(
            (
                "deadline",
                f"截止｜{_notice_name(row)}｜{_get(row, 'department') or '未填'}",
                "",
            )
        )
for row in plans:
    make_date = _get(row, "make_reminder_date")
    publish_date = _get(row, "publish_reminder_date")
    activity = _get(row, "activity_name") or "预录"
    if make_date in week_events:
        week_events[make_date].append(
            (
                "draft",
                f"制定｜{activity}｜{_get(row, 'owner') or '未填'}",
                "",
            )
        )
    if publish_date in week_events:
        week_events[publish_date].append(
            (
                "send",
                f"发布｜{activity}｜{_get(row, 'owner') or '未填'}",
                "",
            )
        )

todo_items: list[tuple[str, str, str]] = []
for row in due_soon[:2]:
    todo_items.append(
        (
            "high",
            f"{_notice_name(row)}未发布",
            f"截止 {_short_date(_get(row, 'effective_end'))} · 责任部门：{_get(row, 'department') or '未填'}",
        )
    )
for row in overdue[:1]:
    todo_items.append(
        (
            "high",
            f"{_notice_name(row)}未回执",
            f"已逾期 · 部门：{_get(row, 'department') or '未填'}",
        )
    )
for row in plans[:2]:
    todo_items.append(
        (
            "mid",
            f"{_get(row, 'activity_name') or '预录通告'}需草拟",
            f"预计发布 {_short_date(_get(row, 'planned_publish_date'))} · 负责人：{_get(row, 'owner') or '未填'}",
        )
    )

type_counts: dict[str, int] = {}
for row in notices:
    notice_type = _get(row, "notice_type") or "其他"
    type_counts[notice_type] = type_counts.get(notice_type, 0) + 1
type_colors = {
    "安全合规": "#fef2f2",
    "日常营运": "#eff6ff",
    "活动通知": "#fffbeb",
    "人事行政": "#f0fdf4",
    "其他": "#f0f1f6",
}
type_stats = [
    (label, round(count / len(notices) * 100), type_colors.get(label, "#e8e3da"))
    for label, count in sorted(type_counts.items(), key=lambda item: item[1], reverse=True)
] if notices else []
health_stats = [
    ("按时发布率", "待接入", 0, "#f0fdf4"),
    ("整体回执率", "待接入", 0, "#f0fdf4"),
    ("平均响应天数", "待接入", 0, "#fffbeb"),
    ("逾期通告比", "待接入", 0, "#fef2f2"),
]

apply_backend_style()

top_nav()

dashboard_html = render_dashboard_html(
    today=today,
    week_days=week_days,
    kpi_data=kpi_data,
    week_events=week_events,
    todo_items=todo_items,
    type_stats=type_stats,
    health_stats=health_stats,
)

st.html(dashboard_html)

st.markdown("#### 当前选中")
detail_tabs = st.tabs(["通告总数", "执行中", "3天内截止", "已截止", "本周日历事件", "待处理事项", "通告类型分布", "健康度"])

with detail_tabs[0]:
    st.caption(f"共 {len(notices)} 条")
    if notices:
        st.dataframe(_notice_table(notices), width="stretch", hide_index=True)
    else:
        st.info("暂无通告记录。")

with detail_tabs[1]:
    st.caption(f"共 {len(running)} 条")
    if running:
        st.dataframe(_notice_table(running), width="stretch", hide_index=True)
    else:
        st.info("暂无执行中通告。")

with detail_tabs[2]:
    st.caption(f"共 {len(due_soon)} 条")
    if due_soon:
        st.dataframe(_notice_table(due_soon), width="stretch", hide_index=True)
    else:
        st.info("暂无 3 天内截止通告。")

with detail_tabs[3]:
    st.caption(f"共 {len(overdue)} 条")
    if overdue:
        st.dataframe(_notice_table(overdue), width="stretch", hide_index=True)
    else:
        st.info("暂无已截止通告。")

with detail_tabs[4]:
    event_rows = []
    for day in week_days:
        for event_type, label, _detail in week_events.get(day.isoformat(), []):
            event_rows.append(
                {
                    "日期": day.strftime("%m-%d"),
                    "类型": {"deadline": "截止", "draft": "制定", "send": "发布", "done": "完成"}.get(event_type, event_type),
                    "事件": label,
                }
            )
    if event_rows:
        st.dataframe(event_rows, width="stretch", hide_index=True)
    else:
        st.info("本周暂无日历事件。")

with detail_tabs[5]:
    if todo_items:
        st.dataframe(
            [{"优先级": priority, "事项": title, "说明": meta} for priority, title, meta in todo_items],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("暂无待处理事项。")

with detail_tabs[6]:
    if type_stats:
        st.dataframe(
            [{"类型": label, "占比": f"{percent}%"} for label, percent, _color in type_stats],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("暂无通告类型数据。")

with detail_tabs[7]:
    st.info("回执率、按时发布率和响应天数待邮箱回执接入后统计。")
