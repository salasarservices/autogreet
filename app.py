"""AutoGreet – Streamlit UI (redesigned)."""
from __future__ import annotations

import io
import json
import logging
import re
from datetime import date
from pathlib import Path

import streamlit as st
from PIL import Image

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("template_config.json")
SENT_LOG = Path("storage/sent_log.jsonl")

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
            # Merge any missing keys from DEFAULT_CONFIG (schema migrations)
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy


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


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_emails(lines: list[str]) -> list[str]:
    """Return list of invalid email strings."""
    return [e for e in lines if e and not EMAIL_RE.match(e)]


# ---------------------------------------------------------------------------
# Sidebar / navigation
# ---------------------------------------------------------------------------

SETUP_PAGES = ["Data source", "Field mapping", "Templates & fonts", "Recipients"]
ACTION_PAGES = ["Preview today", "Send emails"]
ALL_PAGES = SETUP_PAGES + ACTION_PAGES

SETUP_COMPLETE_KEYS = {
    "Data source": "setup_done_datasource",
    "Field mapping": "setup_done_fieldmapping",
    "Templates & fonts": "setup_done_templates",
    "Recipients": "setup_done_recipients",
}


def _init_state() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "Data source"
    if "cfg" not in st.session_state:
        st.session_state.cfg = load_config()
    for key in SETUP_COMPLETE_KEYS.values():
        if key not in st.session_state:
            st.session_state[key] = False


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown("### AutoGreet")
        st.caption("Poster generator")
        st.divider()

        st.caption("SETUP")
        for p in SETUP_PAGES:
            done = st.session_state.get(SETUP_COMPLETE_KEYS.get(p, ""), False)
            icon = "✅" if done else ("▶" if st.session_state.page == p else "○")
            if st.button(f"{icon}  {p}", key=f"nav_{p}", use_container_width=True):
                st.session_state.page = p

        st.divider()
        st.caption("DAILY")
        for p in ACTION_PAGES:
            icon = "▶" if st.session_state.page == p else "○"
            if st.button(f"{icon}  {p}", key=f"nav_{p}", use_container_width=True):
                st.session_state.page = p

        st.divider()
        if st.button("🚀  Send today's greetings", use_container_width=True, type="primary"):
            st.session_state.page = "Send emails"

    return st.session_state.page


# ---------------------------------------------------------------------------
# Page: Data source
# ---------------------------------------------------------------------------

def page_data_source() -> None:
    cfg = st.session_state.cfg

    st.header("Data source")
    st.caption("Where should AutoGreet pull employee data from?")

    mode = st.radio(
        "Source type",
        ["sample_json", "zinghr"],
        index=0 if cfg["data_source"]["mode"] == "sample_json" else 1,
        format_func=lambda x: {"sample_json": "JSON endpoint", "zinghr": "ZingHR (coming soon)"}[x],
        horizontal=True,
    )
    cfg["data_source"]["mode"] = mode

    if mode == "sample_json":
        url = st.text_input(
            "API endpoint URL",
            value=cfg["data_source"].get("sample_url", ""),
            placeholder="https://your-api.com/employees",
        )
        cfg["data_source"]["sample_url"] = url

        with st.expander("Authentication (optional)"):
            c1, c2 = st.columns(2)
            h_name = c1.text_input(
                "Header name",
                value=cfg["data_source"].get("auth_header_name", ""),
                placeholder="Authorization",
            )
            h_val = c2.text_input(
                "Header value",
                value=cfg["data_source"].get("auth_header_value", ""),
                placeholder="Bearer …",
                type="password",
            )
            cfg["data_source"]["auth_header_name"] = h_name
            cfg["data_source"]["auth_header_value"] = h_val
    else:
        st.info("ZingHR integration is coming soon. Configure the JSON endpoint for now.")
        zc = cfg["data_source"]["zinghr"]
        zc["base_url"] = st.text_input("ZingHR base URL", value=zc.get("base_url", ""))
        zc["client_id"] = st.text_input("Client ID", value=zc.get("client_id", ""))

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Save & test", type="primary"):
            save_config(cfg)
            # Attempt a quick fetch to validate
            if mode == "sample_json" and cfg["data_source"].get("sample_url"):
                from data_sources import get_employees, invalidate_cache
                invalidate_cache()
                try:
                    raws = get_employees(cfg, get_secrets())
                    st.success(f"Connected — {len(raws)} employee record(s) found.")
                    st.session_state[SETUP_COMPLETE_KEYS["Data source"]] = True
                    st.session_state.page = "Field mapping"
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not fetch data: {exc}")
            else:
                save_config(cfg)
                st.session_state[SETUP_COMPLETE_KEYS["Data source"]] = True
                st.success("Saved.")


# ---------------------------------------------------------------------------
# Page: Field mapping
# ---------------------------------------------------------------------------

def page_field_mapping() -> None:
    cfg = st.session_state.cfg
    st.header("Field mapping")
    st.caption("Match your API's field names to AutoGreet's internal fields.")

    # Try to show a sample record for reference
    sample_keys: list[str] = []
    if cfg["data_source"].get("sample_url"):
        try:
            from data_sources import get_employees
            raws = get_employees(cfg, get_secrets())
            if raws:
                sample_keys = list(raws[0].keys())
                with st.expander("Sample record keys from your API"):
                    st.code(", ".join(sample_keys))
        except Exception:
            pass

    mapping = cfg.get("field_mapping", {})
    fields = [
        ("name", "Full name"),
        ("designation", "Designation / title"),
        ("department", "Department"),
        ("vertical", "Vertical / business unit"),
        ("dob", "Date of birth (DD-MM-YYYY)"),
        ("doj", "Date of joining (DD-MM-YYYY)"),
        ("photo_url", "Photo URL"),
        ("location", "Location / office"),
    ]

    c1, c2 = st.columns(2)
    for i, (key, label) in enumerate(fields):
        col = c1 if i % 2 == 0 else c2
        mapping[key] = col.text_input(label, value=mapping.get(key, key))

    cfg["field_mapping"] = mapping

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Save & continue", type="primary"):
            save_config(cfg)
            st.session_state[SETUP_COMPLETE_KEYS["Field mapping"]] = True
            st.session_state.page = "Templates & fonts"
            st.rerun()
    with col2:
        if st.button("Back"):
            st.session_state.page = "Data source"
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Templates & fonts
# ---------------------------------------------------------------------------

def page_templates_fonts() -> None:
    cfg = st.session_state.cfg
    st.header("Templates & fonts")
    st.caption("Upload your poster background images and configure fonts.")

    font_dir = Path("assets/fonts")
    font_dir.mkdir(parents=True, exist_ok=True)
    template_dir = Path("assets/templates")
    template_dir.mkdir(parents=True, exist_ok=True)

    # --- Templates ---
    st.subheader("Poster templates")
    tc1, tc2 = st.columns(2)
    for col, poster_type in [(tc1, "birthday"), (tc2, "anniversary")]:
        with col:
            st.markdown(f"**{poster_type.title()} template**")
            current = cfg[poster_type].get("template", f"assets/templates/{poster_type}.png")
            if Path(current).exists():
                st.image(current, use_container_width=True)
            else:
                st.warning("No template uploaded yet")
            uploaded = st.file_uploader(
                f"Upload {poster_type}.png",
                type=["png", "jpg", "jpeg"],
                key=f"tmpl_{poster_type}",
            )
            if uploaded:
                dest = template_dir / f"{poster_type}.png"
                img = Image.open(uploaded)
                img.save(str(dest), format="PNG")
                cfg[poster_type]["template"] = str(dest)
                st.success(f"Saved to {dest}")

    st.divider()

    # --- Text colour ---
    st.subheader("Text colours")
    cc1, cc2 = st.columns(2)
    with cc1:
        cfg["birthday"]["text_colour"] = st.text_input(
            "Birthday poster text colour",
            value=cfg["birthday"].get("text_colour", "#FFFFFF"),
            help="Hex colour, e.g. #FFFFFF for white or #000000 for black",
        )
    with cc2:
        cfg["anniversary"]["text_colour"] = st.text_input(
            "Anniversary poster text colour",
            value=cfg["anniversary"].get("text_colour", "#FFFFFF"),
        )

    st.divider()

    # --- Fonts ---
    st.subheader("Fonts")
    fonts = cfg.get("fonts", {})
    fc1, fc2, fc3 = st.columns(3)
    for col, slot, label in [
        (fc1, "regular", "Body / detail font"),
        (fc2, "bold", "Name font (bold)"),
        (fc3, "year", "Anniversary year font"),
    ]:
        with col:
            current = fonts.get(slot, "")
            st.caption(f"Current: `{Path(current).name}`" if current else "Current: _(none)_")
            uploaded = st.file_uploader(f"Upload {label}", type=["ttf", "otf"], key=f"font_{slot}")
            if uploaded:
                dest = font_dir / uploaded.name
                dest.write_bytes(uploaded.read())
                fonts[slot] = str(dest)
                st.success(f"Saved {uploaded.name}")
    cfg["fonts"] = fonts

    st.divider()

    # --- Advanced layout (collapsed) ---
    with st.expander("Advanced: layout positions (pixels)", expanded=False):
        for poster_type in ["birthday", "anniversary"]:
            st.markdown(f"**{poster_type.title()}**")
            pcfg = cfg[poster_type]
            pb = pcfg["photo_box"]
            tb = pcfg["text_block"]
            lc1, lc2, lc3, lc4 = st.columns(4)
            pb["x"] = lc1.number_input("Photo X", value=pb["x"], step=5, key=f"{poster_type}_pb_x")
            pb["y"] = lc2.number_input("Photo Y", value=pb["y"], step=5, key=f"{poster_type}_pb_y")
            pb["w"] = lc3.number_input("Photo W", value=pb["w"], step=5, key=f"{poster_type}_pb_w")
            pb["h"] = lc4.number_input("Photo H", value=pb["h"], step=5, key=f"{poster_type}_pb_h")
            tc1, tc2, tc3, tc4 = st.columns(4)
            tb["x"] = tc1.number_input("Text X", value=tb["x"], step=5, key=f"{poster_type}_tb_x")
            tb["y"] = tc2.number_input("Text Y", value=tb["y"], step=5, key=f"{poster_type}_tb_y")
            tb["font_size_name"] = tc3.number_input("Name size", value=tb.get("font_size_name", 38), step=1, key=f"{poster_type}_tb_fn")
            tb["font_size_detail"] = tc4.number_input("Detail size", value=tb.get("font_size_detail", 26), step=1, key=f"{poster_type}_tb_fd")
            if poster_type == "anniversary":
                yl = pcfg.get("year_label", {"x": 80, "y": 80, "font_size": 64})
                yc1, yc2, yc3, _ = st.columns(4)
                yl["x"] = yc1.number_input("Year X", value=yl["x"], step=5, key="ann_yl_x")
                yl["y"] = yc2.number_input("Year Y", value=yl["y"], step=5, key="ann_yl_y")
                yl["font_size"] = yc3.number_input("Year size", value=yl.get("font_size", 64), step=2, key="ann_yl_fs")
                pcfg["year_label"] = yl
            st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Save & continue", type="primary"):
            save_config(cfg)
            st.session_state[SETUP_COMPLETE_KEYS["Templates & fonts"]] = True
            st.session_state.page = "Recipients"
            st.rerun()
    with col2:
        if st.button("Back"):
            st.session_state.page = "Field mapping"
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Recipients
# ---------------------------------------------------------------------------

def page_recipients() -> None:
    cfg = st.session_state.cfg
    st.header("Recipients")
    st.caption("Who receives the daily greeting emails? One address per line.")

    has_error = False

    for poster_type in ["birthday", "anniversary"]:
        st.subheader(f"{poster_type.title()} email")
        rec = cfg["recipients"][poster_type]
        c1, c2 = st.columns(2)
        with c1:
            to_str = st.text_area(
                "To",
                value="\n".join(rec.get("to", [])),
                key=f"rec_to_{poster_type}",
                height=100,
                placeholder="hr@company.com",
            )
        with c2:
            cc_str = st.text_area(
                "CC",
                value="\n".join(rec.get("cc", [])),
                key=f"rec_cc_{poster_type}",
                height=100,
                placeholder="manager@company.com",
            )
        to_list = [e.strip() for e in to_str.splitlines() if e.strip()]
        cc_list = [e.strip() for e in cc_str.splitlines() if e.strip()]
        bad = validate_emails(to_list + cc_list)
        if bad:
            st.error(f"Invalid email(s): {', '.join(bad)}")
            has_error = True
        rec["to"] = to_list
        rec["cc"] = cc_list

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Save & finish setup", type="primary", disabled=has_error):
            save_config(cfg)
            st.session_state[SETUP_COMPLETE_KEYS["Recipients"]] = True
            st.session_state.page = "Preview today"
            st.rerun()
    with col2:
        if st.button("Back"):
            st.session_state.page = "Templates & fonts"
            st.rerun()


# ---------------------------------------------------------------------------
# Page: Preview today
# ---------------------------------------------------------------------------

def page_preview() -> None:
    from data_sources import get_employees, map_employee
    from poster_engine import generate_birthday_poster, generate_anniversary_poster, poster_to_bytes

    cfg = st.session_state.cfg
    secrets = get_secrets()

    st.header("Preview today")

    chosen_date = st.date_input("Date to preview", value=date.today())

    if st.button("Fetch employees", type="primary"):
        try:
            raws = get_employees(cfg, secrets)
            st.session_state["employees"] = [
                map_employee(r, cfg.get("field_mapping", {})) for r in raws
            ]
            st.success(f"Loaded {len(st.session_state['employees'])} employee(s).")
        except Exception as exc:
            st.error(f"Failed to fetch employees: {exc}")
            return

    employees: list[dict] = st.session_state.get("employees", [])
    if not employees:
        st.info("Click 'Fetch employees' to load data.")
        return

    # Split by today's event
    birthdays = [
        e for e in employees
        if e.get("dob") and e["dob"].month == chosen_date.month and e["dob"].day == chosen_date.day
    ]
    anniversaries = [
        e for e in employees
        if e.get("doj") and e["doj"].month == chosen_date.month and e["doj"].day == chosen_date.day
    ]

    if not birthdays and not anniversaries:
        st.info(f"No birthdays or anniversaries on {chosen_date.strftime('%d %B %Y')}.")
    else:
        st.success(
            f"**{len(birthdays)}** birthday(s) · **{len(anniversaries)}** anniversary(ies) "
            f"on {chosen_date.strftime('%d %B %Y')}"
        )

    # Birthday previews
    if birthdays:
        st.subheader(f"Birthdays ({len(birthdays)})")
        cols = st.columns(min(len(birthdays), 3))
        for i, emp in enumerate(birthdays):
            with cols[i % 3]:
                already = already_sent(emp["name"], "birthday", chosen_date)
                if already:
                    st.warning(f"⚠ Already sent today")
                st.markdown(f"**{emp['name']}**  \n{emp.get('designation','')} · {emp.get('location','')}")
                if st.button("Generate poster", key=f"bd_gen_{i}"):
                    try:
                        img = generate_birthday_poster(emp, cfg, secrets, chosen_date)
                        png = poster_to_bytes(img)
                        st.image(png)
                        st.download_button(
                            "Download",
                            data=png,
                            file_name=f"birthday_{emp['name'].replace(' ','_')}.png",
                            mime="image/png",
                            key=f"bd_dl_{i}",
                        )
                    except Exception as exc:
                        st.error(f"Error: {exc}")

    # Anniversary previews
    if anniversaries:
        st.subheader(f"Work anniversaries ({len(anniversaries)})")
        cols = st.columns(min(len(anniversaries), 3))
        for i, emp in enumerate(anniversaries):
            with cols[i % 3]:
                doj = emp.get("doj")
                years = chosen_date.year - doj.year - (
                    (chosen_date.month, chosen_date.day) < (doj.month, doj.day)
                ) if doj else 0
                already = already_sent(emp["name"], "anniversary", chosen_date)
                if already:
                    st.warning("⚠ Already sent today")
                st.markdown(
                    f"**{emp['name']}**  \n{emp.get('designation','')} · **{years} year(s)**"
                )
                if st.button("Generate poster", key=f"ann_gen_{i}"):
                    try:
                        img = generate_anniversary_poster(emp, cfg, secrets, chosen_date)
                        png = poster_to_bytes(img)
                        st.image(png)
                        st.download_button(
                            "Download",
                            data=png,
                            file_name=f"anniversary_{emp['name'].replace(' ','_')}.png",
                            mime="image/png",
                            key=f"ann_dl_{i}",
                        )
                    except Exception as exc:
                        st.error(f"Error: {exc}")

    if (birthdays or anniversaries) and st.button("Proceed to send →", type="primary"):
        st.session_state.page = "Send emails"
        st.rerun()


# ---------------------------------------------------------------------------
# Page: Send emails
# ---------------------------------------------------------------------------

def page_send() -> None:
    from data_sources import get_employees, map_employee
    from poster_engine import generate_birthday_poster, generate_anniversary_poster, poster_to_bytes
    from mailer import send_birthday_emails, send_anniversary_emails

    cfg = st.session_state.cfg
    secrets = get_secrets()

    st.header("Send emails")

    smtp_sender = secrets.get("smtp_sender", "")
    smtp_password = secrets.get("smtp_password", "")

    if not smtp_sender or not smtp_password:
        st.error(
            "SMTP credentials are not configured. "
            "Add `smtp_sender` and `smtp_password` to `.streamlit/secrets.toml`."
        )
        return

    chosen_date = st.date_input("Date", value=date.today())

    # --- Fetch & build preview ---
    if st.button("Load today's matches", type="primary"):
        try:
            raws = get_employees(cfg, secrets)
            employees = [map_employee(r, cfg.get("field_mapping", {})) for r in raws]
            st.session_state["send_employees"] = employees
        except Exception as exc:
            st.error(f"Failed to fetch employees: {exc}")
            return

    employees: list[dict] = st.session_state.get("send_employees", [])
    if not employees:
        st.info("Click 'Load today's matches' first.")
        return

    birthdays = [
        e for e in employees
        if e.get("dob") and e["dob"].month == chosen_date.month and e["dob"].day == chosen_date.day
    ]
    anniversaries = [
        e for e in employees
        if e.get("doj") and e["doj"].month == chosen_date.month and e["doj"].day == chosen_date.day
    ]

    already_sent_bd = [e for e in birthdays if already_sent(e["name"], "birthday", chosen_date)]
    already_sent_ann = [e for e in anniversaries if already_sent(e["name"], "anniversary", chosen_date)]
    new_bd = [e for e in birthdays if not already_sent(e["name"], "birthday", chosen_date)]
    new_ann = [e for e in anniversaries if not already_sent(e["name"], "anniversary", chosen_date)]

    # Summary
    st.subheader("What will be sent")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Birthday emails", len(new_bd))
        if new_bd:
            for e in new_bd:
                st.markdown(f"  • {e['name']}")
        if already_sent_bd:
            st.caption(f"⚠ Skipping {len(already_sent_bd)} already sent today")

    with col2:
        st.metric("Anniversary emails", len(new_ann))
        if new_ann:
            for e in new_ann:
                doj = e.get("doj")
                years = chosen_date.year - doj.year if doj else 0
                st.markdown(f"  • {e['name']} ({years} yr)")
        if already_sent_ann:
            st.caption(f"⚠ Skipping {len(already_sent_ann)} already sent today")

    if not new_bd and not new_ann:
        st.info("Nothing new to send for this date.")
        return

    # Email previews
    bd_to = cfg["recipients"]["birthday"].get("to", [])
    ann_to = cfg["recipients"]["anniversary"].get("to", [])
    bd_cc = cfg["recipients"]["birthday"].get("cc", [])
    ann_cc = cfg["recipients"]["anniversary"].get("cc", [])

    with st.expander("Email preview"):
        if new_bd:
            bd_names = [e["name"] for e in new_bd]
            from mailer import _names_summary
            st.markdown(
                f"**Birthday email**  \n"
                f"To: `{', '.join(bd_to)}`  \n"
                f"CC: `{', '.join(bd_cc)}`  \n"
                f"Subject: 🎂 Birthday greetings – {_names_summary(bd_names)} | {chosen_date.strftime('%d %B %Y')}"
            )
        if new_ann:
            ann_names = [e["name"] for e in new_ann]
            from mailer import _names_summary
            st.markdown(
                f"**Anniversary email**  \n"
                f"To: `{', '.join(ann_to)}`  \n"
                f"CC: `{', '.join(ann_cc)}`  \n"
                f"Subject: 🎉 Work anniversary – {_names_summary(ann_names)} | {chosen_date.strftime('%d %B %Y')}"
            )

    st.warning(
        f"This will send **{len(new_bd) + len(new_ann)} email(s)**. "
        "This action cannot be undone."
    )

    if st.button("✅  Confirm & send", type="primary"):
        birthday_posters: list[tuple[str, bytes]] = []
        birthday_names: list[str] = []
        anniversary_posters: list[tuple[str, bytes]] = []
        anniversary_names: list[str] = []

        with st.spinner("Generating posters…"):
            for emp in new_bd:
                try:
                    img = generate_birthday_poster(emp, cfg, secrets, chosen_date)
                    safe = emp["name"].replace(" ", "_")
                    birthday_posters.append((f"birthday_{safe}.png", poster_to_bytes(img)))
                    birthday_names.append(emp["name"])
                except Exception as exc:
                    st.warning(f"Birthday poster failed for {emp['name']}: {exc}")

            for emp in new_ann:
                try:
                    img = generate_anniversary_poster(emp, cfg, secrets, chosen_date)
                    safe = emp["name"].replace(" ", "_")
                    anniversary_posters.append((f"anniversary_{safe}.png", poster_to_bytes(img)))
                    anniversary_names.append(emp["name"])
                except Exception as exc:
                    st.warning(f"Anniversary poster failed for {emp['name']}: {exc}")

        results: list[str] = []

        if birthday_posters:
            try:
                send_birthday_emails(
                    birthday_posters,
                    cfg["recipients"]["birthday"],
                    smtp_sender,
                    smtp_password,
                    chosen_date,
                    employee_names=birthday_names,
                )
                for name in birthday_names:
                    mark_sent(name, "birthday", chosen_date)
                results.append(f"🎂 Birthday email sent ({len(birthday_posters)} poster(s)) — {', '.join(birthday_names)}")
            except Exception as exc:
                results.append(f"❌ Birthday email FAILED: {exc}")

        if anniversary_posters:
            try:
                send_anniversary_emails(
                    anniversary_posters,
                    cfg["recipients"]["anniversary"],
                    smtp_sender,
                    smtp_password,
                    chosen_date,
                    employee_names=anniversary_names,
                )
                for name in anniversary_names:
                    mark_sent(name, "anniversary", chosen_date)
                results.append(f"🎉 Anniversary email sent ({len(anniversary_posters)} poster(s)) — {', '.join(anniversary_names)}")
            except Exception as exc:
                results.append(f"❌ Anniversary email FAILED: {exc}")

        for r in results:
            if "FAILED" in r:
                st.error(r)
            else:
                st.success(r)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="AutoGreet", page_icon="🎉", layout="wide")
    st.title("🎉 AutoGreet")

    _init_state()
    page = render_sidebar()

    dispatch = {
        "Data source": page_data_source,
        "Field mapping": page_field_mapping,
        "Templates & fonts": page_templates_fonts,
        "Recipients": page_recipients,
        "Preview today": page_preview,
        "Send emails": page_send,
    }
    dispatch.get(page, page_data_source)()


if __name__ == "__main__":
    main()
