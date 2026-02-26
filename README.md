# AutoGreet

An MVP auto-greeting poster generator and sender for birthdays and work anniversaries.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure secrets

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your real values
```

Required secrets:

| Key | Description |
|-----|-------------|
| `smtp_sender` | Office365 sender email address |
| `smtp_password` | Office365 SMTP password |
| `withoutbg_api_key` | API key from [withoutbg.com](https://withoutbg.com) (for birthday photo background removal) |
| `zinghr_client_secret` | ZingHR API secret (future, only when using ZingHR data source) |

### 3. Add template images

Place your poster templates in `assets/templates/`:
- `assets/templates/birthday.png`
- `assets/templates/anniversary.png`

You can also upload them via the Streamlit UI (Templates page).

### 4. Run the Streamlit app

```bash
streamlit run app.py
```

### 5. Configure via UI

Open the app in your browser and:

1. **Data Source** – Enter your sample JSON URL (or configure ZingHR for the future).
2. **Field Mapping** – Map your JSON keys to AutoGreet fields.
3. **Fonts** – Upload TTF/OTF fonts for text and the anniversary year label.
4. **Templates** – Upload/verify poster template images.
5. **Layout Config** – Adjust photo box and text positions in pixels.
6. **Recipients** – Set TO and CC email lists for birthday/anniversary emails.
7. **Preview / Generate** – Fetch employees and preview/download posters.
8. **Send Emails** – Generate and send today's greeting emails.

## Daily automated run

```bash
python daily_run.py
```

Generates posters for today's birthdays and anniversaries and sends two emails
(one per category). Skips sending if there are zero matching employees.

Schedule with cron:

```cron
0 8 * * * cd /path/to/autogreet && python daily_run.py >> storage/daily.log 2>&1
```

## File layout

```
autogreet/
├── app.py                  # Streamlit UI
├── poster_engine.py        # Pillow poster composition
├── image_tools.py          # Background removal, face-aware crop, ordinal helper
├── mailer.py               # SMTP email sending
├── daily_run.py            # Daily automated runner
├── data_sources.py         # Sample JSON + ZingHR placeholder
├── template_config.json    # Non-secret configuration
├── requirements.txt
├── assets/
│   ├── templates/
│   │   ├── birthday.png
│   │   └── anniversary.png
│   └── fonts/              # Uploaded font files
├── storage/                # Gitignored – runtime output
│   ├── output/             # Generated poster PNGs
│   └── overrides/
└── .streamlit/
    ├── secrets.toml        # Gitignored – your secrets
    └── secrets.toml.example
```

## Data source: Sample JSON format

The sample JSON endpoint should return a single employee object or a list.
Expected field names (customisable via Field Mapping):

```json
{
  "EmployeeName": "John Doe",
  "Designation": "Senior Engineer",
  "Vertical": "Technology",
  "Department": "Engineering",
  "Location": "Mumbai",
  "DateOfBirth": "15-08-1990",
  "DateOfJoining": "01-06-2018",
  "EmployeeImage": "https://example.com/photo.jpg"
}
```

Dates must be in `DD-MM-YYYY` format (other common formats are also accepted).
