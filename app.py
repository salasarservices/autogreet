"""AutoGreet - Streamlit UI."""
from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from PIL import Image

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("template_config.json")
SENT_LOG    = Path("storage/sent_log.jsonl")

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict = {
    "data_source": {
        "mode": "sample_json",
        "sample_url": "",
        "auth_header_name": "",
        "auth_header_value": "",
        "zinghr": {"base_url": "", "client_id": ""},
    },
    "field_mapping": {
        "name": "EmployeeName",
        "designation": "Designation",
        "vertical": "Vertical",
        "department": "Department",
        "location": "Location",
        "dob": "DateOfBirth",
        "doj": "DateOfJoining",
        "photo_url": "EmployeeImage",
    },
    "fonts": {"regular": "", "bold": "", "year": ""},
    "birthday": {
        "template": "assets/templates/birthday.png",
        "text_colour": "#FFFFFF",
        "photo_box": {"x": 40, "y": 120, "w": 300, "h": 400},
        "text_block": {"x": 360, "y": 200, "line_spacing": 48,
                       "font_size_name": 38, "font_size_detail": 26},
    },
    "anniversary": {
        "template": "assets/templates/anniversary.png",
        "text_colour": "#FFFFFF",
        "photo_box": {"x": 40, "y": 100, "w": 280, "h": 320},
        "text_block": {"x": 360, "y": 200, "line_spacing": 48,
                       "font_size_name": 38, "font_size_detail": 26},
        "year_label": {"x": 80, "y": 80, "font_size": 64},
    },
    "recipients": {
        "birthday": {"to": [], "cc": []},
        "anniversary": {"to": [], "cc": []},
    },
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open() as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w") as f:
        json.dump(cfg, f, indent=2)


def get_secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Idempotency helpers
# ---------------------------------------------------------------------------

def already_sent(employee_name: str, event_type: str, run_date: date) -> bool:
    key = f"{run_date.isoformat()}|{event_type}|{employee_name}"
    if not SENT_LOG.exists():
        return False
    return key in SENT_LOG.read_text().splitlines()


def mark_sent(employee_name: str, event_type: str, run_date: date) -> None:
    SENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    key = f"{run_date.isoformat()}|{event_type}|{employee_name}"
    with SENT_LOG.open("a") as f:
        f.write(key + "\n")


def recent_sent_log(n: int = 10) -> list[dict]:
    """Return the last n entries from the sent log as parsed dicts."""
    if not SENT_LOG.exists():
        return []
    lines = [ln.strip() for ln in SENT_LOG.read_text().splitlines() if ln.strip()]
    results = []
    for line in reversed(lines[-n * 2:]):
        parts = line.split("|")
        if len(parts) == 3:
            results.append({"date": parts[0], "type": parts[1], "name": parts[2]})
        if len(results) >= n:
            break
    return results


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_emails(lines: list[str]) -> list[str]:
    return [e for e in lines if e and not EMAIL_RE.match(e)]


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0f172a 0%, #1e293b 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.05);
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: #cbd5e1 !important; }

/* Nav buttons — cyan (#00BCD4) background, dark text */
[data-testid="stSidebar"] .stButton > button {
    background: rgba(0, 188, 212, 1) !important;
    border: 1px solid rgba(0, 160, 180, 1) !important;
    border-radius: 8px !important;
    color: rgba(15, 23, 42, 1) !important;
    font-size: 0.875rem !important;
    font-weight: 700 !important;
    text-align: left !important;
    padding: 9px 14px !important;
    width: 100% !important;
    transition: all 0.15s ease;
    letter-spacing: 0.01em;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(0, 210, 235, 1) !important;
    border-color: rgba(0, 188, 212, 1) !important;
    color: rgba(15, 23, 42, 1) !important;
    box-shadow: 0 3px 10px rgba(0, 188, 212, 0.40) !important;
}
[data-testid="stSidebar"] .stButton > button:active,
[data-testid="stSidebar"] .stButton > button:focus {
    background: rgba(0, 172, 193, 1) !important;
    border-color: rgba(0, 188, 212, 1) !important;
    color: rgba(15, 23, 42, 1) !important;
    box-shadow: 0 0 0 3px rgba(0, 188, 212, 0.35) !important;
}

/* Send Today's Greetings — green (#8BC34A) */
[data-testid="stSidebar"] [data-testid="baseButton-primary"],
[data-testid="stSidebar"] [data-testid="baseButton-primary"] p,
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
    background: #8bc34a !important;
    background-color: #8bc34a !important;
    border: 1px solid rgba(115, 163, 61, 1) !important;
    border-radius: 10px !important;
    color: #0f172a !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 11px 26px !important;
    box-shadow: 0 4px 14px rgba(139, 195, 74, 0.35) !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-primary"]:hover,
[data-testid="stSidebar"] button[kind="primary"]:hover,
[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"]:hover {
    background: #a5d664 !important;
    background-color: #a5d664 !important;
    box-shadow: 0 6px 20px rgba(139, 195, 74, 0.50) !important;
    transform: translateY(-1px) !important;
    color: #0f172a !important;
}

/* ── Page header ── */
.ag-page-header {
    padding: 4px 0 22px 0;
    border-bottom: 1px solid #f1f5f9;
    margin-bottom: 26px;
}
.ag-page-title {
    font-size: 1.55rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
    line-height: 1.2;
}
.ag-page-sub { font-size: 0.875rem; color: #64748b; margin-top: 4px; }

/* ── Stat tile ── */
.ag-stat {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
}
.ag-stat-num   { font-size: 2.2rem; font-weight: 800; line-height: 1; color: #0f172a; }
.ag-stat-label { font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
                 letter-spacing: 0.06em; color: #94a3b8; margin-top: 5px; }
.ag-stat-sub   { font-size: 0.8rem; color: #64748b; margin-top: 4px; }

/* ── Pills ── */
.ag-pill {
    display: inline-block;
    padding: 3px 11px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
    line-height: 1.6;
}
.ag-pill-bd   { background: #fdf2f8; color: #9d174d; border: 1px solid #fbcfe8; }
.ag-pill-ann  { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.ag-pill-sent { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.ag-pill-skip { background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; }

/* ── Person card ── */
.ag-person {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.04);
    transition: box-shadow 0.15s;
}
.ag-person:hover   { box-shadow: 0 4px 12px rgba(15,23,42,0.09); }
.ag-person-name    { font-size: 0.9rem; font-weight: 600; color: #0f172a; }
.ag-person-meta    { font-size: 0.78rem; color: #64748b; margin-top: 2px; }

/* ── Log row ── */
.ag-log-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #f8fafc;
    font-size: 0.82rem;
}
.ag-log-row:last-child { border-bottom: none; }
.ag-log-name { color: #1e293b; font-weight: 500; }
.ag-log-date { color: #94a3b8; font-size: 0.76rem; }

/* ── Checklist step ── */
.ag-step-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
    border-radius: 9px;
    margin-bottom: 2px;
    font-size: 0.8rem;
}
.ag-step-done    { background: #f0fdf4; color: #15803d; }
.ag-step-pending { color: #94a3b8; }

/* ── Sidebar section label ── */
.ag-label {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: none;
    letter-spacing: 0.02em;
    color: #94a3b8 !important;
    padding: 0 4px;
    margin-bottom: 6px;
    display: block;
}

/* ── Colour swatch ── */
.ag-swatch {
    width: 18px; height: 18px;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
    display: inline-block;
    vertical-align: middle;
    margin-right: 5px;
}

/* ── Empty state ── */
.ag-empty { text-align: center; padding: 48px 24px; color: #94a3b8; }
.ag-empty-icon { font-size: 2.2rem; margin-bottom: 10px; }
.ag-empty-text { font-size: 0.88rem; line-height: 1.6; }

/* ── Send CTA button ── */
.ag-send-cta .stButton > button,
.ag-send-cta .stButton > button[data-testid="baseButton-primary"] {
    background: #8bc34a !important;
    background-color: #8bc34a !important;
    color: #0f172a !important;
    border: 1px solid rgba(115, 163, 61, 1) !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 11px 26px !important;
    box-shadow: 0 4px 14px rgba(139, 195, 74, 0.35) !important;
    transition: all 0.2s ease !important;
}
.ag-send-cta .stButton > button:hover {
    background: #a5d664 !important;
    background-color: #a5d664 !important;
    color: #0f172a !important;
    box-shadow: 0 6px 20px rgba(139, 195, 74, 0.50) !important;
    transform: translateY(-1px) !important;
}
</style>
"""

# ---------------------------------------------------------------------------
# Navigation / state
# ---------------------------------------------------------------------------

SETUP_PAGES  = ["Data source", "Field mapping", "Templates & fonts", "Recipients"]
ACTION_PAGES = ["Dashboard", "Preview & Send"]

SETUP_DONE_KEYS = {
    "Data source":       "setup_done_datasource",
    "Field mapping":     "setup_done_fieldmapping",
    "Templates & fonts": "setup_done_templates",
    "Recipients":        "setup_done_recipients",
}


def _init_state() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"
    if "cfg" not in st.session_state:
        st.session_state.cfg = load_config()
    for key in SETUP_DONE_KEYS.values():
        if key not in st.session_state:
            st.session_state[key] = False


def _nav(page: str) -> None:
    st.session_state.page = page
    st.rerun()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div style="padding:20px 8px 6px 8px;">
              <img src="https://ik.imagekit.io/salasarservices/Salasar-Logo-white.png?updatedAt=1773827925808"
                   style="max-width:160px;width:100%;height:auto;display:block;" alt="Salasar Logo" />
              <div style="font-size:1.35rem;font-weight:800;color:#f1f5f9;letter-spacing:-0.01em;margin-top:14px;line-height:1.2;">AutoGreet</div>
              <div style="font-size:0.72rem;color:#64748b;margin-top:8px;line-height:1.6;">
                AutoGreet automates employee birthday and work anniversary celebrations.
              </div>
            </div>
            <hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:14px 0 16px 0;">
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<span class="ag-label">Daily Ops</span>', unsafe_allow_html=True)
        for p in ACTION_PAGES:
            if st.button(p, key=f"nav_{p}", use_container_width=True):
                _nav(p)

        st.markdown(
            '<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:12px 0;">',
            unsafe_allow_html=True,
        )

        st.markdown('<span class="ag-label">Setup</span>', unsafe_allow_html=True)
        for p in SETUP_PAGES:
            done  = st.session_state.get(SETUP_DONE_KEYS.get(p, ""), False)
            label = ("✓ " if done else "") + p
            if st.button(label, key=f"nav_{p}", use_container_width=True):
                _nav(p)

        st.markdown(
            '<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:12px 0;">',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="ag-send-cta">', unsafe_allow_html=True)
        if st.button("Send Today's Greetings", use_container_width=True, type="primary"):
            _nav("Preview & Send")
        st.markdown("</div>", unsafe_allow_html=True)

        done_count = sum(1 for k in SETUP_DONE_KEYS.values() if st.session_state.get(k))
        st.markdown(
            f"""
            <div style="padding:14px 8px 6px 8px;">
              <div style="font-size:0.7rem;font-weight:700;color:#94a3b8;margin-bottom:5px;">Setup Progress</div>
              <div style="background:rgba(255,255,255,0.06);border-radius:999px;height:4px;overflow:hidden;">
                <div style="background:#6366f1;width:{done_count * 25}%;height:100%;border-radius:999px;"></div>
              </div>
              <div style="font-size:0.7rem;color:#475569;margin-top:4px;">{done_count}/4 complete</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state.page


# ---------------------------------------------------------------------------
# Shared: page header
# ---------------------------------------------------------------------------

def _page_header(title: str, subtitle: str = "") -> None:
    sub_html = f'<div class="ag-page-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="ag-page-header"><div class="ag-page-title">{title}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------

def page_dashboard() -> None:
    _page_header("Dashboard", f"Today is {date.today().strftime('%A, %d %B %Y')}")

    cfg     = st.session_state.cfg
    secrets = get_secrets()
    today   = date.today()

    employees: list[dict] = st.session_state.get("employees", [])
    birthdays_today     = [e for e in employees if e.get("dob") and e["dob"].month == today.month and e["dob"].day == today.day]
    anniversaries_today = [e for e in employees if e.get("doj") and e["doj"].month == today.month and e["doj"].day == today.day]

    # ── Stats row ──
    setup_done = sum(1 for k in SETUP_DONE_KEYS.values() if st.session_state.get(k))
    sent_today = len([r for r in recent_sent_log(200) if r["date"] == today.isoformat()])

    c1, c2, c3, c4 = st.columns(4)
    for col, num, label, sub, colour in [
        (c1, len(birthdays_today),     "Birthdays Today",    "Loaded" if employees else "Load data first", "#f472b6"),
        (c2, len(anniversaries_today), "Anniversaries Today","Loaded" if employees else "Load data first", "#fbbf24"),
        (c3, sent_today,               "Sent Today",         "Emails dispatched",                         "#34d399"),
        (c4, setup_done,               "Setup Complete",     "Ready!" if setup_done == 4 else "Finish setup", "#818cf8"),
    ]:
        col.markdown(
            f"""<div class="ag-stat">
  <div class="ag-stat-num" style="color:{colour};">{num}{"/4" if label == "Setup Complete" else ""}</div>
  <div class="ag-stat-label">{label}</div>
  <div class="ag-stat-sub">{sub}</div>
</div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)

    left, right = st.columns([2, 1], gap="large")

    # ── Left: Today's events ──
    with left:
        st.markdown("**Today's Celebrations**")

        if not employees:
            rb, _ = st.columns([1, 3])
            with rb:
                if st.button("Refresh employee data", use_container_width=True):
                    if cfg["data_source"].get("sample_url"):
                        with st.spinner("Fetching..."):
                            try:
                                from data_sources import get_employees, map_employee, invalidate_cache
                                invalidate_cache()
                                raws = get_employees(cfg, secrets)
                                st.session_state["employees"] = [
                                    map_employee(r, cfg.get("field_mapping", {})) for r in raws
                                ]
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Could not fetch: {exc}")
                    else:
                        st.warning("Configure your data source first.")
            st.markdown(
                '<div class="ag-empty"><div class="ag-empty-icon">&#128100;</div>'
                '<div class="ag-empty-text">No employee data loaded.<br>'
                'Click Refresh or complete Data Source setup.</div></div>',
                unsafe_allow_html=True,
            )

        elif not birthdays_today and not anniversaries_today:
            st.markdown(
                '<div class="ag-empty"><div class="ag-empty-icon">&#127774;</div>'
                '<div class="ag-empty-text">No birthdays or anniversaries today.</div></div>',
                unsafe_allow_html=True,
            )
        else:
            if birthdays_today:
                st.markdown(
                    '<div style="margin-bottom:8px;"><span class="ag-pill ag-pill-bd">Birthdays</span></div>',
                    unsafe_allow_html=True,
                )
                for emp in birthdays_today:
                    sent  = already_sent(emp["name"], "birthday", today)
                    badge = '<span class="ag-pill ag-pill-sent">Sent</span>' if sent else '<span class="ag-pill ag-pill-bd">Pending</span>'
                    loc   = f"  &middot;  {emp.get('location', '')}" if emp.get("location") else ""
                    st.markdown(
                        f"""<div class="ag-person" style="margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div class="ag-person-name">{emp['name']}</div>
      <div class="ag-person-meta">{emp.get('designation', '')}{loc}</div>
    </div>
    <div>{badge}</div>
  </div>
</div>""",
                        unsafe_allow_html=True,
                    )

            if anniversaries_today:
                st.markdown(
                    '<div style="margin:12px 0 8px;"><span class="ag-pill ag-pill-ann">Anniversaries</span></div>',
                    unsafe_allow_html=True,
                )
                for emp in anniversaries_today:
                    doj   = emp.get("doj")
                    years = today.year - doj.year if doj else 0
                    sent  = already_sent(emp["name"], "anniversary", today)
                    badge = '<span class="ag-pill ag-pill-sent">Sent</span>' if sent else '<span class="ag-pill ag-pill-ann">Pending</span>'
                    st.markdown(
                        f"""<div class="ag-person" style="margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div class="ag-person-name">{emp['name']}</div>
      <div class="ag-person-meta">{emp.get('designation', '')}  &middot;  {years} yr</div>
    </div>
    <div>{badge}</div>
  </div>
</div>""",
                        unsafe_allow_html=True,
                    )

            pending = (
                [e for e in birthdays_today     if not already_sent(e["name"], "birthday",    today)] +
                [e for e in anniversaries_today if not already_sent(e["name"], "anniversary", today)]
            )
            if pending:
                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
                st.markdown('<div class="ag-send-cta">', unsafe_allow_html=True)
                if st.button(f"Send {len(pending)} greeting(s) now", type="primary"):
                    _nav("Preview & Send")
                st.markdown("</div>", unsafe_allow_html=True)

    # ── Right: Upcoming + activity + checklist ──
    with right:
        st.markdown("**Upcoming — next 7 days**")
        if employees:
            upcoming = []
            for delta in range(1, 8):
                d = today + timedelta(days=delta)
                for emp in employees:
                    if emp.get("dob") and emp["dob"].month == d.month and emp["dob"].day == d.day:
                        upcoming.append((d, "Birthday", emp["name"]))
                    if emp.get("doj") and emp["doj"].month == d.month and emp["doj"].day == d.day:
                        upcoming.append((d, "Anniversary", emp["name"]))
            upcoming.sort(key=lambda x: x[0])
            if upcoming:
                for d, etype, name in upcoming[:8]:
                    pill = "ag-pill-bd" if etype == "Birthday" else "ag-pill-ann"
                    st.markdown(
                        f"""<div class="ag-log-row">
  <div>
    <div class="ag-log-name">{name}</div>
    <span class="ag-pill {pill}" style="font-size:0.7rem;">{etype}</span>
  </div>
  <div class="ag-log-date">{d.strftime("%d %b")}</div>
</div>""",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<div style="color:#94a3b8;font-size:0.83rem;padding:6px 0;">Nothing coming up.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#94a3b8;font-size:0.83rem;padding:6px 0;">Load data to see upcoming events.</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        st.markdown("**Recent Activity**")
        log = recent_sent_log(8)
        if log:
            for entry in log:
                pill = "ag-pill-bd" if entry["type"] == "birthday" else "ag-pill-ann"
                st.markdown(
                    f"""<div class="ag-log-row">
  <div>
    <div class="ag-log-name">{entry['name']}</div>
    <span class="ag-pill {pill}" style="font-size:0.7rem;">{entry['type'].title()}</span>
  </div>
  <div class="ag-log-date">{entry['date']}</div>
</div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div style="color:#94a3b8;font-size:0.83rem;padding:6px 0;">No emails sent yet.</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        st.markdown("**Setup Checklist**")
        for p, k in SETUP_DONE_KEYS.items():
            done = st.session_state.get(k, False)
            cls  = "ag-step-done" if done else "ag-step-pending"
            icon = "&#10003;" if done else "&#9675;"
            st.markdown(
                f'<div class="ag-step-row {cls}">{icon}&nbsp;&nbsp;{p}</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Page: Data source
# ---------------------------------------------------------------------------

def page_data_source() -> None:
    _page_header("Data Source", "Connect AutoGreet to your employee directory.")
    cfg = st.session_state.cfg

    mode = st.radio(
        "Source type",
        ["sample_json", "zinghr"],
        index=0 if cfg["data_source"]["mode"] == "sample_json" else 1,
        format_func=lambda x: {"sample_json": "JSON Endpoint", "zinghr": "ZingHR (coming soon)"}[x],
        horizontal=True,
        label_visibility="collapsed",
    )
    if mode == "zinghr":
        mode = "sample_json"
        st.info("ZingHR integration is coming soon. Use the JSON endpoint for now.")
    cfg["data_source"]["mode"] = mode

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    url = st.text_input(
        "API endpoint URL",
        value=cfg["data_source"].get("sample_url", ""),
        placeholder="https://your-api.com/employees.json",
    )
    cfg["data_source"]["sample_url"] = url

    with st.expander("Authentication (optional)"):
        h_name = st.text_input(
            "Header name",
            value=cfg["data_source"].get("auth_header_name", ""),
            placeholder="Authorization",
        )
        cfg["data_source"]["auth_header_name"] = h_name
        st.info(
            "Store the header **value** (e.g. Bearer token) in "
            "`.streamlit/secrets.toml` as `api_auth_header_value`. "
            "This keeps credentials out of the committed config file."
        )
        if cfg["data_source"].get("auth_header_value"):
            st.warning("A header value is still in `template_config.json`. Move it to `secrets.toml`.")

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("Save & Test Connection", type="primary", use_container_width=True):
            save_config(cfg)
            if cfg["data_source"].get("sample_url"):
                from data_sources import get_employees, invalidate_cache
                invalidate_cache()
                with st.spinner("Connecting..."):
                    try:
                        raws = get_employees(cfg, get_secrets())
                        st.success(f"Connected — {len(raws)} employee record(s) found.")
                        st.session_state[SETUP_DONE_KEYS["Data source"]] = True
                        _nav("Field mapping")
                    except Exception as exc:
                        st.error(f"Connection failed: {exc}")
            else:
                st.session_state[SETUP_DONE_KEYS["Data source"]] = True
                st.success("Saved.")
    with c2:
        if st.button("Save", use_container_width=True):
            save_config(cfg)
            st.session_state[SETUP_DONE_KEYS["Data source"]] = True
            st.success("Saved.")


# ---------------------------------------------------------------------------
# Page: Field mapping
# ---------------------------------------------------------------------------

def page_field_mapping() -> None:
    _page_header("Field Mapping", "Map your API field names to AutoGreet's internal fields.")
    cfg = st.session_state.cfg

    if cfg["data_source"].get("sample_url"):
        try:
            from data_sources import get_employees
            raws = get_employees(cfg, get_secrets())
            if raws:
                with st.expander("Sample record from your API", expanded=False):
                    rows = "".join(
                        f"<tr><td style='padding:3px 14px 3px 0;color:#64748b;font-size:0.8rem;'>{k}</td>"
                        f"<td style='font-size:0.8rem;color:#0f172a;'>{str(v)[:60]}</td></tr>"
                        for k, v in raws[0].items()
                    )
                    st.markdown(f"<table>{rows}</table>", unsafe_allow_html=True)
        except Exception:
            pass

    mapping = cfg.get("field_mapping", {})
    fields = [
        ("name",        "Full name",           "EmployeeName"),
        ("designation", "Designation / title", "Designation"),
        ("department",  "Department",          "Department"),
        ("vertical",    "Vertical / BU",       "Vertical"),
        ("dob",         "Date of birth",       "DateOfBirth"),
        ("doj",         "Date of joining",     "DateOfJoining"),
        ("photo_url",   "Photo URL",           "EmployeeImage"),
        ("location",    "Location / office",   "Location"),
    ]
    c1, c2 = st.columns(2, gap="large")
    for i, (key, label, default) in enumerate(fields):
        col = c1 if i % 2 == 0 else c2
        with col:
            mapping[key] = st.text_input(label, value=mapping.get(key, default), key=f"fm_{key}")
    cfg["field_mapping"] = mapping

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    c1, c2, c3, _ = st.columns([1, 1, 1, 2])
    with c1:
        if st.button("Save & Continue", type="primary", use_container_width=True):
            save_config(cfg)
            st.session_state[SETUP_DONE_KEYS["Field mapping"]] = True
            _nav("Templates & fonts")
    with c2:
        if st.button("Save", use_container_width=True):
            save_config(cfg)
            st.session_state[SETUP_DONE_KEYS["Field mapping"]] = True
            st.success("Saved.")
    with c3:
        if st.button("Back", use_container_width=True):
            _nav("Data source")


# ---------------------------------------------------------------------------
# Page: Templates & fonts
# ---------------------------------------------------------------------------

def page_templates_fonts() -> None:
    _page_header("Templates & Fonts", "Upload poster backgrounds and configure typography.")
    cfg = st.session_state.cfg
    font_dir     = Path("assets/fonts");     font_dir.mkdir(parents=True, exist_ok=True)
    template_dir = Path("assets/templates"); template_dir.mkdir(parents=True, exist_ok=True)

    tab_bd, tab_ann, tab_fonts = st.tabs(["Birthday Poster", "Anniversary Poster", "Fonts"])

    for tab, pt in [(tab_bd, "birthday"), (tab_ann, "anniversary")]:
        with tab:
            c_prev, c_set = st.columns([1, 1], gap="large")
            with c_prev:
                st.markdown("**Template image**")
                current = cfg[pt].get("template", f"assets/templates/{pt}.png")
                if Path(current).exists():
                    st.image(current, use_container_width=True)
                else:
                    st.markdown(
                        '<div style="background:#f8fafc;border:2px dashed #e2e8f0;border-radius:12px;'
                        'padding:40px;text-align:center;color:#94a3b8;font-size:0.83rem;">No template uploaded</div>',
                        unsafe_allow_html=True,
                    )
                up = st.file_uploader(f"Upload {pt} template", type=["png", "jpg", "jpeg"], key=f"tmpl_{pt}")
                if up:
                    dest = template_dir / f"{pt}.png"
                    Image.open(up).save(str(dest), format="PNG")
                    cfg[pt]["template"] = str(dest)
                    st.success("Template saved.")
                    st.rerun()

            with c_set:
                st.markdown("**Text colour**")
                current_colour = cfg[pt].get("text_colour", "#FFFFFF")
                new_colour = st.color_picker(f"{pt} colour", value=current_colour, label_visibility="collapsed")
                cfg[pt]["text_colour"] = new_colour
                st.markdown(
                    f'<div style="margin-top:4px;font-size:0.78rem;color:#64748b;">'
                    f'<span class="ag-swatch" style="background:{new_colour};"></span>{new_colour}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
                st.markdown("**Layout positions** (px)")
                pb = cfg[pt]["photo_box"]
                tb = cfg[pt]["text_block"]
                lc = st.columns(4)
                pb["x"] = lc[0].number_input("Photo X", value=pb["x"], step=5, key=f"{pt}_pb_x")
                pb["y"] = lc[1].number_input("Photo Y", value=pb["y"], step=5, key=f"{pt}_pb_y")
                pb["w"] = lc[2].number_input("Photo W", value=pb["w"], step=5, key=f"{pt}_pb_w")
                pb["h"] = lc[3].number_input("Photo H", value=pb["h"], step=5, key=f"{pt}_pb_h")
                tc = st.columns(4)
                tb["x"] = tc[0].number_input("Text X", value=tb["x"], step=5, key=f"{pt}_tb_x")
                tb["y"] = tc[1].number_input("Text Y", value=tb["y"], step=5, key=f"{pt}_tb_y")
                tb["font_size_name"]   = tc[2].number_input("Name px",   value=tb.get("font_size_name", 38),   step=1, key=f"{pt}_fn")
                tb["font_size_detail"] = tc[3].number_input("Detail px", value=tb.get("font_size_detail", 26), step=1, key=f"{pt}_fd")
                if pt == "anniversary":
                    yl = cfg["anniversary"].get("year_label", {"x": 80, "y": 80, "font_size": 64})
                    yc = st.columns(4)
                    yl["x"]         = yc[0].number_input("Year X",  value=yl["x"],                 step=5, key="ann_yl_x")
                    yl["y"]         = yc[1].number_input("Year Y",  value=yl["y"],                 step=5, key="ann_yl_y")
                    yl["font_size"] = yc[2].number_input("Year px", value=yl.get("font_size", 64), step=2, key="ann_yl_fs")
                    cfg["anniversary"]["year_label"] = yl

    with tab_fonts:
        st.markdown(
            '<div style="font-size:0.83rem;color:#64748b;margin-bottom:14px;">'
            'Upload TTF/OTF fonts. Without custom fonts AutoGreet falls back to a '
            'low-quality system bitmap font.</div>',
            unsafe_allow_html=True,
        )
        fonts = cfg.get("fonts", {})
        fc = st.columns(3, gap="large")
        for i, (slot, label, desc) in enumerate([
            ("regular", "Body / detail font",   "Designation, department, location"),
            ("bold",    "Name font (bold)",      "Employee name — prominent display"),
            ("year",    "Anniversary year font", "Large ordinal year number"),
        ]):
            with fc[i]:
                cur = fonts.get(slot, "")
                if cur and Path(cur).exists():
                    st.markdown(f'<span class="ag-pill ag-pill-sent">&#10003; {Path(cur).name}</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="ag-pill ag-pill-skip">No font uploaded</span>', unsafe_allow_html=True)
                st.markdown(f"**{label}**")
                st.caption(desc)
                up = st.file_uploader(f"Upload {label}", type=["ttf", "otf"], key=f"font_{slot}")
                if up:
                    dest = font_dir / up.name
                    dest.write_bytes(up.read())
                    fonts[slot] = str(dest)
                    st.success(f"Saved {up.name}")
        cfg["fonts"] = fonts

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    c1, c2, c3, _ = st.columns([1, 1, 1, 2])
    with c1:
        if st.button("Save & Continue", type="primary", use_container_width=True):
            save_config(cfg)
            st.session_state[SETUP_DONE_KEYS["Templates & fonts"]] = True
            _nav("Recipients")
    with c2:
        if st.button("Save", use_container_width=True):
            save_config(cfg)
            st.session_state[SETUP_DONE_KEYS["Templates & fonts"]] = True
            st.success("Saved.")
    with c3:
        if st.button("Back", use_container_width=True):
            _nav("Field mapping")


# ---------------------------------------------------------------------------
# Page: Recipients
# ---------------------------------------------------------------------------

def page_recipients() -> None:
    _page_header("Recipients", "Who receives the daily greeting emails?")
    cfg       = st.session_state.cfg
    has_error = False

    tab_bd, tab_ann = st.tabs(["Birthday Email", "Anniversary Email"])
    for tab, pt in [(tab_bd, "birthday"), (tab_ann, "anniversary")]:
        with tab:
            rec = cfg["recipients"][pt]
            st.markdown(
                '<div style="font-size:0.83rem;color:#64748b;margin-bottom:10px;">One address per line.</div>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("**To** — Primary recipients")
                to_str = st.text_area("To", value="\n".join(rec.get("to", [])),
                                      key=f"rec_to_{pt}", height=120,
                                      placeholder="hr@company.com", label_visibility="collapsed")
            with c2:
                st.markdown("**CC** — Optional copy")
                cc_str = st.text_area("CC", value="\n".join(rec.get("cc", [])),
                                      key=f"rec_cc_{pt}", height=120,
                                      placeholder="ceo@company.com", label_visibility="collapsed")

            to_list = [e.strip() for e in to_str.splitlines() if e.strip()]
            cc_list = [e.strip() for e in cc_str.splitlines() if e.strip()]
            bad = validate_emails(to_list + cc_list)
            if bad:
                st.error(f"Invalid email(s): {', '.join(bad)}")
                has_error = True
            elif to_list or cc_list:
                n = len(to_list) + len(cc_list)
                st.markdown(
                    f'<div style="color:#4ade80;font-size:0.78rem;margin-top:4px;">&#10003; {n} valid address{"es" if n > 1 else ""}</div>',
                    unsafe_allow_html=True,
                )
            rec["to"] = to_list
            rec["cc"] = cc_list

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    c1, c2, c3, _ = st.columns([1, 1, 1, 2])
    with c1:
        if st.button("Save & Finish Setup", type="primary", use_container_width=True, disabled=has_error):
            save_config(cfg)
            st.session_state[SETUP_DONE_KEYS["Recipients"]] = True
            _nav("Dashboard")
    with c2:
        if st.button("Save", use_container_width=True, disabled=has_error):
            save_config(cfg)
            st.session_state[SETUP_DONE_KEYS["Recipients"]] = True
            st.success("Saved.")
    with c3:
        if st.button("Back", use_container_width=True):
            _nav("Templates & fonts")


# ---------------------------------------------------------------------------
# Page: Preview & Send
# ---------------------------------------------------------------------------

def page_preview_send() -> None:
    from data_sources import get_employees, map_employee
    from poster_engine import generate_birthday_poster, generate_anniversary_poster, poster_to_bytes
    from mailer import send_birthday_emails, send_anniversary_emails, _names_summary

    cfg     = st.session_state.cfg
    secrets = get_secrets()
    _page_header("Preview & Send", "Review and dispatch today's greeting emails.")

    smtp_sender   = secrets.get("smtp_sender", "")
    smtp_password = secrets.get("smtp_password", "")
    smtp_ok = bool(smtp_sender and smtp_password)

    if not smtp_ok:
        st.error(
            "SMTP credentials not configured. "
            "Add `smtp_sender` and `smtp_password` to `.streamlit/secrets.toml`."
        )

    # ── Controls row ──
    ctrl1, ctrl2, ctrl3, _ = st.columns([1, 1, 1, 3])
    with ctrl1:
        chosen_date = st.date_input("Date", value=date.today())
    with ctrl2:
        st.markdown("<div style='padding-top:25px;'>", unsafe_allow_html=True)
        load_clicked = st.button("Load Matches", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with ctrl3:
        st.markdown("<div style='padding-top:25px;'>", unsafe_allow_html=True)
        if st.button("Clear", use_container_width=True):
            st.session_state.pop("send_employees", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if load_clicked:
        with st.spinner("Fetching employees..."):
            try:
                raws   = get_employees(cfg, secrets)
                mapped = [map_employee(r, cfg.get("field_mapping", {})) for r in raws]
                st.session_state["send_employees"] = mapped
                st.session_state["employees"]      = mapped
            except Exception as exc:
                st.error(f"Failed to fetch employees: {exc}")
                return

    employees: list[dict] = st.session_state.get("send_employees", [])
    if not employees:
        st.markdown(
            '<div class="ag-empty" style="padding:40px 0;">'
            '<div class="ag-empty-icon">&#128269;</div>'
            "<div class=\"ag-empty-text\">Click <strong>Load Matches</strong> to see who's celebrating.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    birthdays     = [e for e in employees if e.get("dob") and e["dob"].month == chosen_date.month and e["dob"].day == chosen_date.day]
    anniversaries = [e for e in employees if e.get("doj") and e["doj"].month == chosen_date.month and e["doj"].day == chosen_date.day]
    new_bd        = [e for e in birthdays     if not already_sent(e["name"], "birthday",    chosen_date)]
    new_ann       = [e for e in anniversaries if not already_sent(e["name"], "anniversary", chosen_date)]
    skip_bd       = [e for e in birthdays     if     already_sent(e["name"], "birthday",    chosen_date)]
    skip_ann      = [e for e in anniversaries if     already_sent(e["name"], "anniversary", chosen_date)]

    if not birthdays and not anniversaries:
        st.markdown(
            f'<div class="ag-empty" style="padding:40px 0;">'
            f'<div class="ag-empty-icon">&#127774;</div>'
            f'<div class="ag-empty-text">No celebrations on {chosen_date.strftime("%d %B %Y")}.</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        return

    # ── Stats ──
    s1, s2, s3, s4 = st.columns(4)
    for col, num, label, colour in [
        (s1, len(new_bd),                        "Birthdays to send",     "#f472b6"),
        (s2, len(new_ann),                       "Anniversaries to send", "#fbbf24"),
        (s3, len(skip_bd) + len(skip_ann),       "Already sent today",    "#94a3b8"),
        (s4, len(birthdays) + len(anniversaries),"Total matches",         "#34d399"),
    ]:
        col.markdown(
            f'<div class="ag-stat"><div class="ag-stat-num" style="color:{colour};">{num}</div>'
            f'<div class="ag-stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    # ── Employee grid ──
    for event_list, etype, pill_cls, key_pfx in [
        (birthdays,     "Birthday",    "ag-pill-bd",  "bd"),
        (anniversaries, "Anniversary", "ag-pill-ann", "ann"),
    ]:
        if not event_list:
            continue
        st.markdown(
            f'<div style="margin-bottom:10px;"><span class="ag-pill {pill_cls}" style="font-size:0.85rem;">{etype}s</span></div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(min(max(len(event_list), 1), 3))
        for i, emp in enumerate(event_list):
            with cols[i % 3]:
                sent  = already_sent(emp["name"], etype.lower(), chosen_date)
                badge = (f'<span class="ag-pill ag-pill-sent">Sent</span>'
                         if sent else f'<span class="ag-pill {pill_cls}">Pending</span>')
                extra = ""
                if etype == "Anniversary":
                    doj   = emp.get("doj")
                    years = chosen_date.year - doj.year if doj else 0
                    extra = f"  &middot;  {years} yr"
                loc = f"  &middot;  {emp.get('location', '')}" if emp.get("location") else ""
                st.markdown(
                    f"""<div class="ag-person" style="margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
    <div class="ag-person-name">{emp['name']}</div>{badge}
  </div>
  <div class="ag-person-meta">{emp.get('designation', '')}{loc}{extra}</div>
</div>""",
                    unsafe_allow_html=True,
                )
                with st.expander("Preview poster"):
                    if st.button("Generate", key=f"{key_pfx}_gen_{i}"):
                        with st.spinner("Rendering..."):
                            try:
                                fn  = generate_birthday_poster if etype == "Birthday" else generate_anniversary_poster
                                png = poster_to_bytes(fn(emp, cfg, secrets, chosen_date))
                                st.image(png, use_container_width=True)
                                st.download_button(
                                    "Download PNG", data=png,
                                    file_name=f"{etype.lower()}_{emp['name'].replace(' ', '_')}.png",
                                    mime="image/png", key=f"{key_pfx}_dl_{i}",
                                    use_container_width=True,
                                )
                            except Exception as exc:
                                st.error(f"Render failed: {exc}")

    if not new_bd and not new_ann:
        st.info("All greetings for this date have already been sent.")
        return

    # ── Email preview ──
    with st.expander("Email preview", expanded=False):
        if new_bd:
            bd_to = cfg["recipients"]["birthday"].get("to", [])
            bd_cc = cfg["recipients"]["birthday"].get("cc", [])
            st.markdown(
                f"**Birthday email**  \n"
                f"To: `{', '.join(bd_to) or '—'}`   CC: `{', '.join(bd_cc) or '—'}`  \n"
                f"Subject: Happy Birthday – {_names_summary([e['name'] for e in new_bd])} | {chosen_date.strftime('%d %B %Y')}"
            )
        if new_ann:
            ann_to = cfg["recipients"]["anniversary"].get("to", [])
            ann_cc = cfg["recipients"]["anniversary"].get("cc", [])
            st.markdown(
                f"**Anniversary email**  \n"
                f"To: `{', '.join(ann_to) or '—'}`   CC: `{', '.join(ann_cc) or '—'}`  \n"
                f"Subject: Work Anniversary – {_names_summary([e['name'] for e in new_ann])} | {chosen_date.strftime('%d %B %Y')}"
            )

    # ── Confirm & send ──
    total = len(new_bd) + len(new_ann)
    st.warning(
        f"This will send **{total} email{'s' if total > 1 else ''}** "
        f"({len(new_bd)} birthday, {len(new_ann)} anniversary). "
        "This action cannot be undone.",
        icon="warning",
    )
    st.markdown('<div class="ag-send-cta">', unsafe_allow_html=True)
    send_clicked = st.button(
        f"Confirm & Send {total} email{'s' if total > 1 else ''}",
        type="primary",
        disabled=not smtp_ok,
        help="Configure SMTP credentials in secrets.toml first" if not smtp_ok else None,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if not send_clicked:
        return

    # ── Execute send ──
    bd_posters:  list[tuple[str, bytes]] = []
    bd_names:    list[str] = []
    ann_posters: list[tuple[str, bytes]] = []
    ann_names:   list[str] = []

    with st.status("Generating posters...", expanded=True) as status_box:
        for emp in new_bd:
            st.write(f"Birthday poster — {emp['name']}")
            try:
                png = poster_to_bytes(generate_birthday_poster(emp, cfg, secrets, chosen_date))
                bd_posters.append((f"birthday_{emp['name'].replace(' ', '_')}.png", png))
                bd_names.append(emp["name"])
            except Exception as exc:
                st.warning(f"Birthday poster failed for {emp['name']}: {exc}")

        for emp in new_ann:
            st.write(f"Anniversary poster — {emp['name']}")
            try:
                png = poster_to_bytes(generate_anniversary_poster(emp, cfg, secrets, chosen_date))
                ann_posters.append((f"anniversary_{emp['name'].replace(' ', '_')}.png", png))
                ann_names.append(emp["name"])
            except Exception as exc:
                st.warning(f"Anniversary poster failed for {emp['name']}: {exc}")

        status_box.update(label="Sending emails...", state="running")
        results: list[tuple[bool, str]] = []

        if bd_posters:
            try:
                send_birthday_emails(
                    bd_posters, cfg["recipients"]["birthday"],
                    smtp_sender, smtp_password, chosen_date,
                    employee_names=bd_names,
                )
                for n in bd_names:
                    mark_sent(n, "birthday", chosen_date)
                results.append((True, f"Birthday email sent ({len(bd_posters)} poster(s)) — {', '.join(bd_names)}"))
            except Exception as exc:
                results.append((False, f"Birthday email failed: {exc}"))

        if ann_posters:
            try:
                send_anniversary_emails(
                    ann_posters, cfg["recipients"]["anniversary"],
                    smtp_sender, smtp_password, chosen_date,
                    employee_names=ann_names,
                )
                for n in ann_names:
                    mark_sent(n, "anniversary", chosen_date)
                results.append((True, f"Anniversary email sent ({len(ann_posters)} poster(s)) — {', '.join(ann_names)}"))
            except Exception as exc:
                results.append((False, f"Anniversary email failed: {exc}"))

        all_ok = all(ok for ok, _ in results)
        status_box.update(
            label="All emails sent!" if all_ok else "Completed with errors",
            state="complete" if all_ok else "error",
        )

    for ok, msg in results:
        st.success(msg) if ok else st.error(msg)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="AutoGreet",
        page_icon="celebration",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    _init_state()
    page = render_sidebar()

    dispatch = {
        "Dashboard":         page_dashboard,
        "Data source":       page_data_source,
        "Field mapping":     page_field_mapping,
        "Templates & fonts": page_templates_fonts,
        "Recipients":        page_recipients,
        "Preview & Send":    page_preview_send,
    }
    dispatch.get(page, page_dashboard)()


if __name__ == "__main__":
    main()
