from __future__ import annotations

from html import escape

import streamlit as st

# ─── Linear-inspired design tokens ────────────────────────────────────────────
_CSS = """
<style>
/* ── reset ─────────────────────────────────────────────────── */
#MainMenu, header, footer { display: none !important; }
[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none !important; }

[data-testid="stAppViewContainer"] { background: #f7f8fa; }
.block-container {
    max-width: none;
    padding: 0 1.5rem 2.5rem;
}

/* ── CSS custom properties ──────────────────────────────────── */
:root {
  --bg:           #f7f8fa;
  --surface:      #ffffff;
  --border:       #e3e5ec;
  --border-s:     #cdd0de;
  --text:         #1a1c2e;
  --text-2:       #454964;
  --text-3:       #8a8ea8;
  --accent:       #5e6ad2;
  --accent-h:     #4f5bc4;
  --accent-sub:   #eef0fc;
  --accent-bdr:   #c5c9ec;
  --green:        #16a34a;
  --green-sub:    #f0fdf4;
  --amber:        #b45309;
  --amber-sub:    #fffbeb;
  --red:          #dc2626;
  --red-sub:      #fef2f2;
  --blue:         #2563eb;
  --blue-sub:     #eff6ff;
  --r:            8px;
  --r-lg:         12px;
  --r-xl:         16px;
  --shadow-sm:    0 1px 2px rgba(0,0,0,0.04);
}

/* ── typography ─────────────────────────────────────────────── */
* {
    font-family: -apple-system, BlinkMacSystemFont, "Inter",
                 "Segoe UI", "Microsoft YaHei", sans-serif;
}
h1, h2, h3 { color: var(--text); letter-spacing: -0.02em; }

/* ── nav brand label ─────────────────────────────────────────── */
.lnr-brand {
    display: inline-block;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: .12em;
    color: var(--accent);
    text-transform: uppercase;
    padding: 5px 4px;
    white-space: nowrap;
}
.lnr-nav-divider {
    height: 1px;
    background: var(--border);
    margin: 0 0 1.1rem;
}

/* ── page link (nav) styling ─────────────────────────────────── */
[data-testid="stPageLink"] {
    background: none !important;
    padding: 2px 0 !important;
}
[data-testid="stPageLink"] a {
    display: inline-flex !important;
    align-items: center !important;
    gap: 4px !important;
    padding: 5px 10px !important;
    border-radius: 7px !important;
    color: #454964 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    transition: background .12s, color .12s !important;
    white-space: nowrap !important;
}
[data-testid="stPageLink"] a:hover {
    background: var(--accent-sub) !important;
    color: #3d4ab8 !important;
}

/* ── Streamlit component overrides ──────────────────────────── */
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    padding: 1rem 1.1rem;
    box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] { color: var(--text-2); font-size: .83rem; }
[data-testid="stMetricValue"] { color: var(--text); font-weight: 700; }

[data-testid="stForm"],
[data-testid="stExpander"] details {
    border: 1px solid var(--border) !important;
    border-radius: var(--r-lg) !important;
    background: var(--surface) !important;
    box-shadow: var(--shadow-sm) !important;
}

[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    overflow: hidden;
}

div.stButton > button,
div.stDownloadButton > button,
div[data-testid="stPopover"] button {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r);
    color: var(--text);
    font-size: .875rem;
    font-weight: 500;
    box-shadow: var(--shadow-sm);
    transition: background .12s, border-color .12s, box-shadow .12s;
}
div.stButton > button:hover,
div.stDownloadButton > button:hover {
    border-color: var(--border-s);
    background: #f0f1f8;
    box-shadow: 0 2px 6px rgba(94,106,210,.1);
}
div.stButton > button[kind="primary"] {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
    box-shadow: 0 1px 3px rgba(94,106,210,.35);
}
div.stButton > button[kind="primary"]:hover {
    background: var(--accent-h);
    border-color: var(--accent-h);
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    border-radius: var(--r) !important;
    border: 1px solid var(--border) !important;
    background: #f7f8fa !important;
    transition: border-color .12s, box-shadow .12s;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important;
    background: var(--surface) !important;
    box-shadow: 0 0 0 3px rgba(94,106,210,.12) !important;
}

/* ── page header ────────────────────────────────────────────── */
.lnr-page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    padding: .5rem 0 .9rem;
    margin-bottom: 1.25rem;
    border-bottom: 1px solid var(--border);
}
.lnr-eyebrow {
    color: var(--accent);
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    margin-bottom: .28rem;
}
.lnr-page-title {
    color: var(--text);
    font-size: 1.42rem;
    font-weight: 700;
    letter-spacing: -.02em;
    line-height: 1.2;
}
.lnr-page-desc { color: var(--text-3); font-size: .875rem; margin-top: .3rem; }
.lnr-badge {
    background: var(--accent-sub);
    border: 1px solid var(--accent-bdr);
    border-radius: 999px;
    color: var(--accent);
    font-size: .77rem;
    font-weight: 600;
    padding: .38rem .75rem;
    white-space: nowrap;
}

/* ── section title ──────────────────────────────────────────── */
.lnr-section-title {
    display: flex;
    align-items: center;
    gap: .5rem;
    color: var(--text);
    font-size: .93rem;
    font-weight: 700;
    letter-spacing: -.01em;
    margin: .5rem 0 .75rem;
}
.lnr-section-title::before {
    content: "";
    display: inline-block;
    width: 3px;
    height: .9em;
    border-radius: 2px;
    background: var(--accent);
    flex-shrink: 0;
}

/* ── cards ──────────────────────────────────────────────────── */
.lnr-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow-sm);
    padding: 1rem 1.1rem 1.1rem;
    margin-bottom: 1rem;
}
.lnr-card-muted {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--r);
    color: var(--text-2);
    font-size: .875rem;
    padding: .8rem .9rem;
}

/* ── status badges ──────────────────────────────────────────── */
.lnr-status {
    border-radius: 999px;
    display: inline-block;
    font-size: .75rem;
    font-weight: 600;
    padding: .28rem .6rem;
    white-space: nowrap;
}
.lnr-status-running   { background: var(--green-sub);  color: var(--green); }
.lnr-status-overdue   { background: var(--red-sub);    color: var(--red);   }
.lnr-status-pending   { background: var(--blue-sub);   color: var(--blue);  }
.lnr-status-cancelled { background: var(--amber-sub);  color: var(--amber); }

/* ── field grid ─────────────────────────────────────────────── */
.lnr-field-grid {
    display: grid;
    gap: .65rem 1rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin: .6rem 0 .8rem;
}
.lnr-field {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: .65rem .8rem;
}
.lnr-field-label { color: var(--text-3); font-size: .75rem; font-weight: 500; margin-bottom: .22rem; }
.lnr-field-value { color: var(--text); font-size: .9rem; font-weight: 600; overflow-wrap: anywhere; }

/* ── responsive ─────────────────────────────────────────────── */
@media (max-width: 900px) {
    .lnr-page-header { align-items: flex-start; flex-direction: column; }
    .lnr-field-grid  { grid-template-columns: 1fr; }
}
</style>
"""

def apply_backend_style() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def top_nav() -> None:
    # Brand label + nav links in a single row
    cols = st.columns([1.1, 1, 1, 1, 8])
    cols[0].markdown('<span class="lnr-brand">OPS AGENT</span>', unsafe_allow_html=True)
    cols[1].page_link("streamlit_app.py", label="营运概况", icon="📊")
    cols[2].page_link("pages/1_Import_Notification.py", label="导入通告", icon="📋")
    cols[3].page_link("pages/2_Pre_Registration.py", label="预录信息", icon="📅")
    # Divider line below nav
    st.markdown('<div class="lnr-nav-divider"></div>', unsafe_allow_html=True)


def page_header(title: str, description: str, badge: str | None = None) -> None:
    badge_html = f'<span class="lnr-badge">{escape(badge)}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="lnr-page-header">
          <div>
            <div class="lnr-eyebrow">OPERATIONS AGENT</div>
            <div class="lnr-page-title">{escape(title)}</div>
            <div class="lnr-page-desc">{escape(description)}</div>
          </div>
          {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str) -> None:
    st.markdown(f'<div class="lnr-section-title">{escape(title)}</div>', unsafe_allow_html=True)


def card_start() -> None:
    st.markdown('<div class="lnr-card">', unsafe_allow_html=True)


def card_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def muted_note(text: str) -> None:
    st.markdown(f'<div class="lnr-card-muted">{escape(text)}</div>', unsafe_allow_html=True)


def status_badge(status: str | None) -> str:
    status_text = status or "未填写"
    class_name = {
        "草稿": "lnr-status-pending",
        "已发送": "lnr-status-running",
        "已回执": "lnr-status-running",
        "已完成": "lnr-status-running",
        "已逾期": "lnr-status-overdue",
        "执行中": "lnr-status-running",
        "已截止": "lnr-status-overdue",
        "待发布": "lnr-status-pending",
        "已发布": "lnr-status-running",
        "已取消": "lnr-status-cancelled",
    }.get(status_text, "lnr-status-cancelled")
    return f'<span class="lnr-status {class_name}">{escape(status_text)}</span>'


def field_grid(fields: list[tuple[str, str | None]]) -> None:
    items = "".join(
        f"""<div class="lnr-field">
              <div class="lnr-field-label">{escape(label)}</div>
              <div class="lnr-field-value">{escape(value or "—")}</div>
            </div>"""
        for label, value in fields
    )
    st.markdown(f'<div class="lnr-field-grid">{items}</div>', unsafe_allow_html=True)
