from __future__ import annotations

from datetime import date, timedelta
from html import escape
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from app.db import get_conn, init_db
from app.ui import apply_backend_style, top_nav

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


def _bar(percent: int, color: str) -> str:
    percent = max(0, min(percent, 100))
    return f"<div class='bar'><i style='width:{percent}%;background:{color}'></i></div>"


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

event_meta = {
    "deadline": ("⚠", "#fef2f2", "#dc2626"),
    "draft": ("✎", "#fffbeb", "#b45309"),
    "send": ("↑", "#eff6ff", "#2563eb"),
    "done": ("✓", "#f0fdf4", "#16a34a"),
}
weekday_text = "一二三四五六日"

kpi_html = "".join(
    f"""
    <article class="kpi-card">
      <div class="kpi-title">{escape(label)}</div>
      <div class="kpi-value" style="color:{color}">{value}</div>
      <div class="kpi-sub">{escape(subtitle)}</div>
    </article>
    """
    for label, value, subtitle, color in kpi_data
)

calendar_html = ""
for day in week_days:
    is_today = day == today
    events = "".join(
        f"""
        <span class="event-pill" style="background:{event_meta[event_type][1]};color:{event_meta[event_type][2]}">
          {event_meta[event_type][0]} {escape(label)}
        </span>
        """
        for event_type, label, detail in week_events.get(day.isoformat(), [])
    )
    calendar_html += f"""
    <div class="day-col">
      <div class="weekday {'today' if is_today else ''}">{'今天' if is_today else '周' + weekday_text[day.weekday()]}</div>
      <div class="day-num">{day.day}</div>
      <div class="events">{events}</div>
    </div>
    """

todo_colors = {"high": "#dc2626", "mid": "#b45309", "low": "#16a34a"}
todo_html = "".join(
    f"""
    <article class="todo-item">
      <i style="background:{todo_colors[priority]}"></i>
      <div>
        <div class="todo-title">{escape(title)}</div>
        <div class="todo-meta">{escape(meta)}</div>
      </div>
    </article>
    """
    for priority, title, meta in todo_items[:4]
)
if not todo_html:
    todo_html = "<div class='empty-state'>暂无待处理事项</div>"

dept_html = """
    <div class="empty-state">
      回执率将通过邮箱回执/确认邮件接入后统计，目前不展示模拟数据。
    </div>
"""

type_html = "".join(
    f"""
    <div class="metric-row type-row">
      <span>{escape(label)}</span>
      {_bar(percent, color)}
      <strong>{percent}%</strong>
    </div>
    """
    for label, percent, color in type_stats
)
if not type_html:
    type_html = "<div class='empty-state'>暂无通告类型数据</div>"

health_html = "".join(
    f"""
    <div class="metric-row health-row">
      <span>{escape(label)}</span>
      {_bar(percent, color)}
      <strong>{escape(value)}</strong>
    </div>
    """
    for label, value, percent, color in health_stats
)

apply_backend_style()

top_nav()

dashboard_html = f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      background: #f7f8fa;
      color: #1a1c2e;
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", "Microsoft YaHei", sans-serif;
    }}
    .dashboard {{
      width: 100%;
      min-height: 840px;
      padding: 8px 6px 0 6px;
      background: #f7f8fa;
    }}
    .page-title {{
      margin: 0 0 14px 0;
      color: #8a8ea8;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
    }}
    .kpi-card {{
      height: 112px;
      padding: 18px 20px 16px;
      border-radius: 12px;
      background: #ffffff;
      border: 1px solid #e3e5ec;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .kpi-title {{
      color: #454964;
      font-size: 12.5px;
      line-height: 1;
    }}
    .kpi-value {{
      margin-top: 9px;
      font-size: 24px;
      font-weight: 700;
      line-height: 1;
    }}
    .kpi-sub {{
      margin-top: 10px;
      color: #8a8ea8;
      font-size: 11.5px;
      line-height: 1;
    }}
    .mid-grid {{
      display: grid;
      grid-template-columns: 1.33fr 0.95fr;
      gap: 16px;
      margin-top: 18px;
    }}
    .bottom-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-top: 16px;
    }}
    .panel {{
      background: #ffffff;
      border: 1px solid #e3e5ec;
      border-radius: 14px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .calendar-panel {{ height: 330px; padding: 22px 24px 20px; }}
    .todo-panel     {{ height: 330px; padding: 22px 24px 18px; }}
    .small-panel    {{ height: 246px; padding: 22px 24px 18px; }}
    .panel-title {{
      color: #1a1c2e;
      font-size: 13px;
      font-weight: 700;
      line-height: 1;
      letter-spacing: -.01em;
    }}
    .calendar {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 8px;
      margin-top: 20px;
    }}
    .day-col {{ min-width: 0; text-align: center; }}
    .weekday {{
      color: #8a8ea8;
      font-size: 11.5px;
      font-weight: 500;
      line-height: 1;
    }}
    .weekday.today {{
      color: #5e6ad2;
      font-weight: 700;
    }}
    .day-num {{
      margin-top: 6px;
      color: #6c6f8a;
      font-size: 12px;
      line-height: 1;
    }}
    .events {{ margin-top: 11px; min-height: 78px; }}
    .event-pill {{
      display: block;
      max-width: 100%;
      margin-top: 7px;
      padding: 4px 6px;
      border-radius: 5px;
      overflow: hidden;
      font-size: 10.5px;
      line-height: 1.3;
      text-overflow: ellipsis;
      white-space: normal;
      text-align: left;
    }}
    .legend {{
      display: flex;
      gap: 10px;
      margin-top: 28px;
      flex-wrap: wrap;
    }}
    .legend span {{
      padding: 5px 9px;
      border-radius: 6px;
      font-size: 11.5px;
      line-height: 1;
      white-space: nowrap;
    }}
    .todo-list {{ margin-top: 17px; }}
    .todo-item {{
      display: flex;
      gap: 10px;
      align-items: flex-start;
      margin-top: 9px;
      padding: 11px 10px 10px;
      border-radius: 10px;
      background: #f0f1f8;
      border: 1px solid #e3e5ec;
    }}
    .todo-item:first-child {{ margin-top: 0; }}
    .todo-item i {{
      width: 7px;
      height: 7px;
      flex: 0 0 auto;
      margin-top: 5px;
      border-radius: 50%;
    }}
    .todo-title {{
      color: #1a1c2e;
      font-size: 13.5px;
      font-weight: 600;
      line-height: 1.2;
    }}
    .todo-meta {{
      margin-top: 5px;
      color: #8a8ea8;
      font-size: 11.5px;
      line-height: 1;
    }}
    .empty-state {{
      margin-top: 18px;
      padding: 14px;
      border-radius: 10px;
      background: #f7f8fa;
      border: 1px solid #e3e5ec;
      color: #8a8ea8;
      font-size: 12.5px;
      line-height: 1.5;
    }}
    .metrics {{ margin-top: 18px; }}
    .metric-row {{
      display: grid;
      grid-template-columns: 70px 1fr 40px;
      gap: 10px;
      align-items: center;
      margin-top: 13px;
    }}
    .metric-row:first-child {{ margin-top: 0; }}
    .type-row {{ grid-template-columns: 68px 1fr 40px; }}
    .health-row {{
      grid-template-columns: 92px 1fr 48px;
      margin-top: 0;
      padding: 11px 0;
      border-bottom: 1px solid #e3e5ec;
    }}
    .health-row:first-child {{ padding-top: 0; }}
    .health-row:last-child  {{ border-bottom: 0; padding-bottom: 0; }}
    .metric-row span {{
      color: #454964;
      font-size: 12.5px;
      line-height: 1;
      white-space: nowrap;
    }}
    .metric-row strong {{
      color: #1a1c2e;
      font-size: 12.5px;
      font-weight: 600;
      line-height: 1;
      text-align: right;
      white-space: nowrap;
    }}
    .bar {{
      height: 5px;
      overflow: hidden;
      border-radius: 999px;
      background: #e8eaef;
    }}
    .bar i {{ display: block; height: 100%; border-radius: 999px; }}
    .type-panel {{ position: relative; }}
    @media (max-width: 960px) {{
      .kpi-grid, .bottom-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .mid-grid {{ grid-template-columns: 1fr; }}
      .calendar-panel, .todo-panel, .small-panel {{ height: auto; }}
    }}
  </style>
</head>
<body>
  <main class="dashboard">
    <h1 class="page-title">营运概况</h1>
    <section class="kpi-grid">{kpi_html}</section>

    <section class="mid-grid">
      <div class="panel calendar-panel">
        <div class="panel-title">本周通告日历</div>
        <div class="calendar">{calendar_html}</div>
        <div class="legend">
          <span style="background:#f0fdf4;color:#16a34a">✓ 已完成</span>
          <span style="background:#eff6ff;color:#2563eb">↑ 待发布</span>
          <span style="background:#fffbeb;color:#b45309">✎ 草稿中</span>
          <span style="background:#fef2f2;color:#dc2626">⚠ 截止提醒</span>
        </div>
      </div>

      <div class="panel todo-panel">
        <div class="panel-title">待处理事项</div>
        <div class="todo-list">{todo_html}</div>
      </div>
    </section>

    <section class="bottom-grid">
      <div class="panel small-panel">
        <div class="panel-title">回执率 — 按部门</div>
        <div class="metrics">{dept_html}</div>
      </div>

      <div class="panel small-panel type-panel">
        <div class="panel-title">通告类型分布</div>
        <div class="metrics">{type_html}</div>
      </div>

      <div class="panel small-panel">
        <div class="panel-title">近30天通告执行健康度</div>
        <div class="metrics">{health_html}</div>
      </div>
    </section>

  </main>
</body>
</html>
"""

components.html(dashboard_html, height=760, scrolling=False)

st.markdown("#### 当前选中")
detail_option = st.segmented_control(
    "选择明细",
    ["通告总数", "执行中", "3天内截止", "已截止", "本周日历事件", "待处理事项", "通告类型分布", "健康度"],
    default="通告总数",
    label_visibility="collapsed",
)

with st.container(height=300, border=True):
    if detail_option == "通告总数":
        st.caption(f"共 {len(notices)} 条")
        if notices:
            st.dataframe(_notice_table(notices), use_container_width=True, hide_index=True)
        else:
            st.info("暂无通告记录。")
    elif detail_option == "执行中":
        st.caption(f"共 {len(running)} 条")
        if running:
            st.dataframe(_notice_table(running), use_container_width=True, hide_index=True)
        else:
            st.info("暂无执行中通告。")
    elif detail_option == "3天内截止":
        st.caption(f"共 {len(due_soon)} 条")
        if due_soon:
            st.dataframe(_notice_table(due_soon), use_container_width=True, hide_index=True)
        else:
            st.info("暂无 3 天内截止通告。")
    elif detail_option == "已截止":
        st.caption(f"共 {len(overdue)} 条")
        if overdue:
            st.dataframe(_notice_table(overdue), use_container_width=True, hide_index=True)
        else:
            st.info("暂无已截止通告。")
    elif detail_option == "本周日历事件":
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
            st.dataframe(event_rows, use_container_width=True, hide_index=True)
        else:
            st.info("本周暂无日历事件。")
    elif detail_option == "待处理事项":
        if todo_items:
            st.dataframe(
                [{"优先级": priority, "事项": title, "说明": meta} for priority, title, meta in todo_items],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("暂无待处理事项。")
    elif detail_option == "通告类型分布":
        if type_stats:
            st.dataframe(
                [{"类型": label, "占比": f"{percent}%"} for label, percent, _color in type_stats],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("暂无通告类型数据。")
    else:
        st.info("回执率、按时发布率和响应天数待邮箱回执接入后统计。")
