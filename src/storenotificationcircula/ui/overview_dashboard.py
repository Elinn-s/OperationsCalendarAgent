# HTML/CSS 仪表盘
from __future__ import annotations

from datetime import date
from html import escape
from typing import Any


def _bar(percent: int, color: str) -> str:
    percent = max(0, min(percent, 100))
    return f"<div class='bar'><i style='width:{percent}%;background:{color}'></i></div>"


def render_dashboard_html(
    *,
    today: date,
    week_days: list[date],
    kpi_data: list[tuple[str, Any, str, str]],
    week_events: dict[str, list[tuple[str, str, str]]],
    todo_items: list[tuple[str, str, str]],
    type_stats: list[tuple[str, int, str]],
    health_stats: list[tuple[str, str, int, str]],
) -> str:
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
            for event_type, label, _detail in week_events.get(day.isoformat(), [])
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

    return f"""
<style>
    .ops-dashboard,
    .ops-dashboard * {{
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", "Microsoft YaHei", sans-serif;
    }}
    .ops-dashboard {{
      width: 100%;
      min-height: 840px;
      padding: 8px 6px 0 6px;
      background: #f7f8fa;
      color: #1a1c2e;
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
  <main class="ops-dashboard">
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
"""
