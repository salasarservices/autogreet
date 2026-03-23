# AutoGreet

Automated birthday and work-anniversary poster generator and emailer.
Fetches employee data from a JSON endpoint (or ZingHR, coming soon),
composites personalised posters using Pillow, and sends them via Office365 SMTP.

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure secrets

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with real values
```

| Key | Required | Description |
|---|---|---|
| `smtp_sender` | Yes | Office365 sender email address |
| `smtp_password` | Yes | Office365 SMTP password |
| `withoutbg_api_key` | Optional | API key from [withoutbg.com](https://withoutbg.com) for birthday photo background removal |
| `zinghr_client_secret` | Optional | ZingHR API secret (for future ZingHR integration) |

### 3. Run the Streamlit app

```bash
streamlit run app.py
```

### 4. Complete the setup wizard

Open the app and work through the **Setup** section in the sidebar:

1. **Data source** — enter your JSON endpoint URL and test the connection
2. **Field mapping** — map your API's keys to AutoGreet fields (auto-detected from a sample record)
3. **Templates & fonts** — upload poster background images and configure fonts and text colours
4. **Recipients** — set TO/CC addresses for birthday and anniversary emails (validated inline)

Then use **Preview today** to see and download posters before sending, and **Send emails** to
dispatch the day's greetings with a pre-flight confirmation screen.

---

## Automated daily run

### Option A — GitHub Actions (recommended, no server required)

Add these secrets to your repository (`Settings → Secrets → Actions`):

- `SMTP_SENDER`
- `SMTP_PASSWORD`
- `WITHOUTBG_API_KEY` (optional)

The workflow in `.github/workflows/daily_greetings.yml` runs automatically at
08:00 IST on weekdays. You can also trigger it manually with a date override or dry-run flag.

### Option B — cron

```bash
0 8 * * 1-5 cd /path/to/autogreet && python daily_run.py >> storage/daily.log 2>&1
```

### CLI flags

```
python daily_run.py [--date YYYY-MM-DD] [--dry-run]
```

| Flag | Description |
|---|---|
| `--date` | Override today's date — useful for testing or backfill |
| `--dry-run` | Generate posters and log output but skip email sending |

---

## Idempotency

`daily_run.py` and the Send Emails page both write a record to `storage/sent_log.jsonl`
after each successful send. If the script is re-run (crash recovery, double-click, etc.),
employees already sent today are skipped and logged. The log is keyed on
`YYYY-MM-DD|event_type|employee_name`.

---

## JSON data source format

The endpoint should return a single object or an array of objects.
Default field names (configurable via Field Mapping in the UI):

```json
{
  "EmployeeName": "Priya Sharma",
  "Designation": "Senior Engineer",
  "Vertical": "Technology",
  "Department": "Platform",
  "Location": "Mumbai",
  "DateOfBirth": "23-03-1992",
  "DateOfJoining": "23-03-2019",
  "EmployeeImage": "https://example.com/photo.jpg"
}
```

Dates are accepted in `DD-MM-YYYY`, `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`, and `YYYY/MM/DD`.

### Auth headers

If your endpoint requires authentication, add the header name and value on the
Data Source page (or in `template_config.json` as `auth_header_name` / `auth_header_value`).
The header value is masked in the UI and never logged.

---

## Configuration reference (`template_config.json`)

```json
{
  "data_source": {
    "mode": "sample_json",
    "sample_url": "https://your-api.com/employees",
    "auth_header_name": "",
    "auth_header_value": ""
  },
  "birthday": {
    "template": "assets/templates/birthday.png",
    "text_colour": "#FFFFFF",
    "photo_box": { "x": 40, "y": 120, "w": 300, "h": 400 },
    "text_block": { "x": 360, "y": 200, "line_spacing": 48,
                    "font_size_name": 38, "font_size_detail": 26 }
  },
  "anniversary": {
    "template": "assets/templates/anniversary.png",
    "text_colour": "#FFFFFF",
    "photo_box": { "x": 40, "y": 100, "w": 280, "h": 320 },
    "text_block": { "x": 360, "y": 200, "line_spacing": 48,
                    "font_size_name": 38, "font_size_detail": 26 },
    "year_label": { "x": 80, "y": 80, "font_size": 64 }
  },
  "recipients": {
    "birthday":    { "to": ["hr@company.com"], "cc": [] },
    "anniversary": { "to": ["hr@company.com"], "cc": [] }
  }
}
```

Text colour is now configurable per poster type — use any valid hex colour (e.g. `"#000000"`
for black text on a light template).

---

## File layout

```
autogreet/
├── app.py                  # Streamlit UI
├── poster_engine.py        # Pillow poster composition
├── image_tools.py          # BG removal, face-aware crop, ordinal helper
├── mailer.py               # SMTP email sending
├── daily_run.py            # CLI automated runner (idempotent)
├── data_sources.py         # JSON fetch (cached) + ZingHR stub
├── conftest.py             # Pytest shared fixtures
├── template_config.json    # Non-secret configuration
├── requirements.txt
├── tests/
│   ├── test_data_sources.py
│   ├── test_image_tools.py
│   ├── test_poster_engine.py
│   ├── test_mailer.py
│   └── test_daily_run.py
├── assets/
│   ├── templates/          # birthday.png, anniversary.png
│   └── fonts/              # uploaded TTF/OTF files
├── storage/                # gitignored — runtime output
│   ├── output/             # generated poster PNGs
│   └── sent_log.jsonl      # idempotency log
└── .streamlit/
    ├── config.toml         # theme + server config
    ├── secrets.toml        # gitignored — your credentials
    └── secrets.toml.example
```

---

## Running tests

```bash
pip install pytest
pytest tests/ -v
```
