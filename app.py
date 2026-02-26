"""AutoGreet – Streamlit UI."""
from __future__ import annotations

import io
import json
import os
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
CONFIG_PATH = Path("template_config.json")


def load_config() -> dict:
    with CONFIG_PATH.open() as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with CONFIG_PATH.open("w") as f:
        json.dump(cfg, f, indent=2)


def get_secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # noqa: BLE001
        return {}


# ---------------------------------------------------------------------------
# Page: Data Source
# ---------------------------------------------------------------------------

def page_data_source(cfg: dict) -> None:
    st.header("Data Source Configuration")

    mode = st.radio(
        "Active data source",
        ["sample_json", "zinghr"],
        index=0 if cfg["data_source"]["mode"] == "sample_json" else 1,
        format_func=lambda x: {"sample_json": "Sample JSON URL", "zinghr": "ZingHR API (future)"}[x],
    )
    cfg["data_source"]["mode"] = mode

    if mode == "sample_json":
        url = st.text_input("Sample JSON URL", value=cfg["data_source"].get("sample_url", ""))
        cfg["data_source"]["sample_url"] = url
    else:
        st.info("ZingHR integration is a future placeholder. Provide credentials in .streamlit/secrets.toml.")
        base_url = st.text_input("ZingHR Base URL", value=cfg["data_source"]["zinghr"].get("base_url", ""))
        client_id = st.text_input("Client ID", value=cfg["data_source"]["zinghr"].get("client_id", ""))
        cfg["data_source"]["zinghr"]["base_url"] = base_url
        cfg["data_source"]["zinghr"]["client_id"] = client_id

    if st.button("Save Data Source Config"):
        save_config(cfg)
        st.success("Saved.")


# ---------------------------------------------------------------------------
# Page: Field Mapping
# ---------------------------------------------------------------------------

def page_field_mapping(cfg: dict) -> None:
    st.header("Field Mapping")
    st.caption("Map AutoGreet fields to the keys returned by your data source.")

    mapping = cfg.get("field_mapping", {})
    fields = ["name", "designation", "vertical", "department", "location", "dob", "doj", "photo_url"]

    for field in fields:
        mapping[field] = st.text_input(field, value=mapping.get(field, field))

    cfg["field_mapping"] = mapping

    if st.button("Save Field Mapping"):
        save_config(cfg)
        st.success("Saved.")


# ---------------------------------------------------------------------------
# Page: Fonts
# ---------------------------------------------------------------------------

def page_fonts(cfg: dict) -> None:
    st.header("Font Management")
    st.caption("Upload TTF/OTF font files. They are saved to assets/fonts/.")

    font_dir = Path("assets/fonts")
    font_dir.mkdir(parents=True, exist_ok=True)

    fonts = cfg.get("fonts", {})

    for slot, label in [("regular", "Text Regular"), ("bold", "Text Bold (optional)"), ("year", "Anniversary Year")]:
        col1, col2 = st.columns([2, 3])
        with col1:
            st.markdown(f"**{label}**")
            current = fonts.get(slot, "")
            st.caption(f"Current: `{current}`" if current else "Current: _(none)_")
        with col2:
            uploaded = st.file_uploader(f"Upload {label}", type=["ttf", "otf"], key=f"font_{slot}")
            if uploaded:
                dest = font_dir / uploaded.name
                dest.write_bytes(uploaded.read())
                fonts[slot] = str(dest)
                st.success(f"Saved to {dest}")

    cfg["fonts"] = fonts

    if st.button("Save Font Config"):
        save_config(cfg)
        st.success("Saved.")


# ---------------------------------------------------------------------------
# Page: Templates
# ---------------------------------------------------------------------------

def page_templates(cfg: dict) -> None:
    st.header("Poster Templates")
    st.caption("Upload or view birthday and anniversary template images.")

    template_dir = Path("assets/templates")
    template_dir.mkdir(parents=True, exist_ok=True)

    for poster_type, key in [("birthday", "birthday"), ("anniversary", "anniversary")]:
        st.subheader(poster_type.title())
        current_path = cfg[poster_type].get("template", f"assets/templates/{poster_type}.png")
        if Path(current_path).exists():
            st.image(current_path, caption=f"Current {poster_type} template", use_container_width=True)
        else:
            st.warning(f"Template not found at `{current_path}`")

        uploaded = st.file_uploader(f"Upload {poster_type} template", type=["png", "jpg", "jpeg"], key=f"tmpl_{poster_type}")
        if uploaded:
            dest = template_dir / f"{poster_type}.png"
            img = Image.open(uploaded)
            img.save(str(dest), format="PNG")
            cfg[poster_type]["template"] = str(dest)
            st.success(f"Saved to {dest}")

    if st.button("Save Template Config"):
        save_config(cfg)
        st.success("Saved.")


# ---------------------------------------------------------------------------
# Page: Layout Config
# ---------------------------------------------------------------------------

def page_layout(cfg: dict) -> None:
    st.header("Template Layout Configuration")
    st.caption("Adjust photo box and text block positions (in pixels).")

    for poster_type in ["birthday", "anniversary"]:
        st.subheader(poster_type.title())
        pcfg = cfg[poster_type]

        with st.expander("Photo Box", expanded=False):
            pb = pcfg["photo_box"]
            c1, c2, c3, c4 = st.columns(4)
            pb["x"] = c1.number_input("X", value=pb["x"], step=5, key=f"{poster_type}_pb_x")
            pb["y"] = c2.number_input("Y", value=pb["y"], step=5, key=f"{poster_type}_pb_y")
            pb["w"] = c3.number_input("W", value=pb["w"], step=5, key=f"{poster_type}_pb_w")
            pb["h"] = c4.number_input("H", value=pb["h"], step=5, key=f"{poster_type}_pb_h")

        with st.expander("Text Block", expanded=False):
            tb = pcfg["text_block"]
            c1, c2 = st.columns(2)
            tb["x"] = c1.number_input("X", value=tb["x"], step=5, key=f"{poster_type}_tb_x")
            tb["y"] = c2.number_input("Y", value=tb["y"], step=5, key=f"{poster_type}_tb_y")
            tb["line_spacing"] = c1.number_input("Line Spacing", value=tb.get("line_spacing", 48), step=2, key=f"{poster_type}_tb_ls")
            tb["font_size_name"] = c2.number_input("Font Size (Name)", value=tb.get("font_size_name", 38), step=1, key=f"{poster_type}_tb_fn")
            tb["font_size_detail"] = c1.number_input("Font Size (Detail)", value=tb.get("font_size_detail", 26), step=1, key=f"{poster_type}_tb_fd")

        if poster_type == "anniversary":
            with st.expander("Year Label", expanded=False):
                yl = pcfg.get("year_label", {"x": 80, "y": 80, "font_size": 64})
                c1, c2, c3 = st.columns(3)
                yl["x"] = c1.number_input("X", value=yl["x"], step=5, key="ann_yl_x")
                yl["y"] = c2.number_input("Y", value=yl["y"], step=5, key="ann_yl_y")
                yl["font_size"] = c3.number_input("Font Size", value=yl.get("font_size", 64), step=2, key="ann_yl_fs")
                pcfg["year_label"] = yl

    if st.button("Save Layout Config"):
        save_config(cfg)
        st.success("Saved.")


# ---------------------------------------------------------------------------
# Page: Recipients
# ---------------------------------------------------------------------------

def page_recipients(cfg: dict) -> None:
    st.header("Email Recipients")

    for poster_type in ["birthday", "anniversary"]:
        st.subheader(poster_type.title())
        rec = cfg["recipients"][poster_type]

        to_str = st.text_area(
            "TO (one per line)",
            value="\n".join(rec.get("to", [])),
            key=f"rec_to_{poster_type}",
            height=100,
        )
        cc_str = st.text_area(
            "CC (one per line)",
            value="\n".join(rec.get("cc", [])),
            key=f"rec_cc_{poster_type}",
            height=80,
        )
        rec["to"] = [e.strip() for e in to_str.splitlines() if e.strip()]
        rec["cc"] = [e.strip() for e in cc_str.splitlines() if e.strip()]

    if st.button("Save Recipients"):
        save_config(cfg)
        st.success("Saved.")


# ---------------------------------------------------------------------------
# Page: Preview / Generate
# ---------------------------------------------------------------------------

def page_preview(cfg: dict) -> None:
    from data_sources import get_employees, map_employee
    from poster_engine import (
        generate_birthday_poster,
        generate_anniversary_poster,
        poster_to_bytes,
    )

    st.header("Preview & Generate")
    secrets = get_secrets()

    # Date picker
    chosen_date = st.date_input("Target date", value=date.today())

    # Fetch employees
    if st.button("Fetch Employees"):
        try:
            raws = get_employees(cfg, secrets)
            st.session_state["employees"] = [
                map_employee(r, cfg.get("field_mapping", {})) for r in raws
            ]
            st.success(f"Fetched {len(st.session_state['employees'])} employee(s).")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Failed to fetch employees: {exc}")

    employees: list[dict] = st.session_state.get("employees", [])

    if not employees:
        st.info("Click 'Fetch Employees' to load data.")
        return

    # Select employee
    names = [e["name"] or f"Employee #{i}" for i, e in enumerate(employees)]
    idx = st.selectbox("Select employee", range(len(names)), format_func=lambda i: names[i])
    emp = employees[idx]

    col1, col2 = st.columns(2)

    # Birthday preview
    dob = emp.get("dob")
    with col1:
        st.subheader("Birthday Poster")
        if dob:
            st.caption(f"DOB: {dob.strftime('%d-%m-%Y')} | Match today: {dob.month == chosen_date.month and dob.day == chosen_date.day}")
        if st.button("Generate Birthday Poster"):
            try:
                img = generate_birthday_poster(emp, cfg, secrets, chosen_date)
                png = poster_to_bytes(img)
                st.image(png, caption="Birthday Poster")
                st.download_button("Download", data=png, file_name=f"birthday_{emp['name']}.png", mime="image/png")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Error: {exc}")

    # Anniversary preview
    doj = emp.get("doj")
    with col2:
        st.subheader("Anniversary Poster")
        if doj:
            matches = doj.month == chosen_date.month and doj.day == chosen_date.day
            years = chosen_date.year - doj.year if matches else None
            years_str = f" | Years: {years}" if years is not None else ""
            st.caption(f"DOJ: {doj.strftime('%d-%m-%Y')} | Match today: {matches}{years_str}")
        if st.button("Generate Anniversary Poster"):
            try:
                img = generate_anniversary_poster(emp, cfg, secrets, chosen_date)
                png = poster_to_bytes(img)
                st.image(png, caption="Anniversary Poster")
                st.download_button("Download", data=png, file_name=f"anniversary_{emp['name']}.png", mime="image/png")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Page: Send Emails
# ---------------------------------------------------------------------------

def page_send(cfg: dict) -> None:
    from data_sources import get_employees, map_employee
    from poster_engine import (
        generate_birthday_poster,
        generate_anniversary_poster,
        poster_to_bytes,
    )
    from mailer import send_birthday_emails, send_anniversary_emails

    st.header("Send Emails")
    secrets = get_secrets()

    smtp_sender = st.text_input("SMTP Sender (email)", value=secrets.get("smtp_sender", ""))
    smtp_pass_placeholder = "(set in secrets.toml)"
    st.caption(f"SMTP password: {smtp_pass_placeholder} – set `smtp_password` in `.streamlit/secrets.toml`")

    chosen_date = st.date_input("Date for poster generation", value=date.today())

    if st.button("Generate and Send Emails"):
        smtp_password = secrets.get("smtp_password", "")
        if not smtp_sender or not smtp_password:
            st.error("Configure smtp_sender and smtp_password in .streamlit/secrets.toml first.")
            return

        with st.spinner("Fetching employees…"):
            try:
                raws = get_employees(cfg, secrets)
                employees = [map_employee(r, cfg.get("field_mapping", {})) for r in raws]
            except Exception as exc:  # noqa: BLE001
                st.error(f"Failed to fetch employees: {exc}")
                return

        birthday_posters: list[tuple[str, bytes]] = []
        anniversary_posters: list[tuple[str, bytes]] = []
        today = chosen_date

        for emp in employees:
            safe_name = (emp["name"] or "emp").replace(" ", "_")
            dob = emp.get("dob")
            if dob and dob.month == today.month and dob.day == today.day:
                try:
                    img = generate_birthday_poster(emp, cfg, secrets, today)
                    birthday_posters.append((f"birthday_{safe_name}.png", poster_to_bytes(img)))
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"Birthday poster failed for {emp['name']}: {exc}")

            doj = emp.get("doj")
            if doj and doj.month == today.month and doj.day == today.day:
                try:
                    img = generate_anniversary_poster(emp, cfg, secrets, today)
                    anniversary_posters.append((f"anniversary_{safe_name}.png", poster_to_bytes(img)))
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"Anniversary poster failed for {emp['name']}: {exc}")

        results = []
        try:
            send_birthday_emails(
                birthday_posters,
                cfg["recipients"]["birthday"],
                smtp_sender,
                smtp_password,
                today,
            )
            results.append(f"Birthday email sent ({len(birthday_posters)} poster(s)).")
        except Exception as exc:  # noqa: BLE001
            results.append(f"Birthday email FAILED: {exc}")

        try:
            send_anniversary_emails(
                anniversary_posters,
                cfg["recipients"]["anniversary"],
                smtp_sender,
                smtp_password,
                today,
            )
            results.append(f"Anniversary email sent ({len(anniversary_posters)} poster(s)).")
        except Exception as exc:  # noqa: BLE001
            results.append(f"Anniversary email FAILED: {exc}")

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
    st.title("🎉 AutoGreet – Poster Generator")

    cfg = load_config()

    pages = {
        "Data Source": page_data_source,
        "Field Mapping": page_field_mapping,
        "Fonts": page_fonts,
        "Templates": page_templates,
        "Layout Config": page_layout,
        "Recipients": page_recipients,
        "Preview / Generate": page_preview,
        "Send Emails": page_send,
    }

    with st.sidebar:
        st.title("Navigation")
        selected = st.radio("Go to", list(pages.keys()))

    pages[selected](cfg)


if __name__ == "__main__":
    main()
