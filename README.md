# FemTrack — Personal Reproductive Health Platform

FemTrack is a private Flask web application for menstrual cycle tracking, fertility forecasting, body metrics, sexual activity logs, and shareable read-only analytics. Data is stored in Google Cloud Firestore. The interface supports light and dark themes, responsive layouts, and a unified toast notification system for feedback and errors.

---

## Quick Start

### Prerequisites

- Python 3.10+
- A Firebase / Google Cloud project with Firestore enabled
- Service account credentials (JSON) for Firestore access

### Installation

```bash
git clone <repository-url>
cd Femtrack
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Environment configuration

Create a `.env` file in the project root:

```env
SECRET_KEY=your_flask_secret_key
FIREBASE_CREDENTIALS={"type":"service_account",...}
ADMIN_USER=you@example.com,partner@example.com
DEFAULT_PASS=your_first_login_password
VIEW_PASS=shared_analytics_password
EMAIL_USER=optional_smtp_user
EMAIL_PASSWORD=optional_smtp_password
```


| Variable                        | Purpose                                                                 |
| ------------------------------- | ----------------------------------------------------------------------- |
| `SECRET_KEY`                    | Flask session signing key                                               |
| `FIREBASE_CREDENTIALS`          | Full Firebase service account JSON as a single-line string              |
| `ADMIN_USER`                    | Comma-separated emails allowed to log in                                |
| `DEFAULT_PASS`                  | Password used on first login before the account is created in Firestore |
| `VIEW_PASS`                     | Default view-only analytics password (can be changed in Settings)       |
| `EMAIL_USER` / `EMAIL_PASSWORD` | SMTP credentials for OTP password reset emails (optional)               |


### Run locally

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser. Use an email listed in `ADMIN_USER` and `DEFAULT_PASS` on first login, then change your password in Settings.

### Production

The app includes `gunicorn` in `requirements.txt`. Example:

```bash
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

Set the same environment variables on your host (e.g. Render, Railway, VPS).

---

## Architecture

FemTrack uses a thin routing layer in `app.py` and delegates business logic to modules under `utils/`.

```
Browser (Bootstrap 5 + Chart.js)
        │
        ▼
   app.py  ── routes, sessions, flash → toast
        │
        ├── utils/firestore_service.py   Firestore CRUD
        ├── utils/auth.py                Password hashing
        ├── utils/auth_decorators.py     @login_required, @auth_required, API guards
        ├── utils/biometrics.py          BMI and body-metric trends
        ├── utils/fertility.py           Cycle prediction and fertility scoring
        ├── utils/date_helpers.py        Date parsing, sorting, chart formatting
        ├── utils/email_service.py       OTP email delivery
        └── utils/otp.py                 OTP generation and validation
        │
        ▼
   Google Cloud Firestore
```

### Frontend layout

- `**templates/base.html**` — Navbar, theme toggle, footer, toast stack, custom dropdown sync
- `**templates/macros.html**` — Reusable Jinja2 components (cards, buttons, tables, forms)
- `**static/css/styles.css**` — Theme variables, responsive nav drawer, toasts, metric panels
- `**static/js/error-handler.js**` — Validation helpers that route errors to toasts

### Sessions

Sessions are permanent with a 10-year lifetime and refresh on each request, so users stay signed in until they log out explicitly.

### Notifications

All server `flash()` messages and client-side validation errors appear as **top-right toasts** (auto-dismiss after 4 seconds). Types: `success`, `danger`, `warning`, `info`. Helpers: `showFemtrackToast(message, type)` and `showFemtrackErrors([...])`.

---

## Project structure

```
Femtrack/
├── app.py                 Main Flask application and routes
├── config.py              Firebase init and environment config
├── requirements.txt
├── templates/             Jinja2 pages and macros
├── static/
│   ├── css/styles.css
│   ├── js/error-handler.js
│   ├── data/home_messages.txt
│   ├── icons/             Symptom SVG icons
│   └── images/            Home carousel assets
└── utils/                 Backend services
```

---

## Features by page

### Authentication


| Route              | Page             | Description                                      |
| ------------------ | ---------------- | ------------------------------------------------ |
| `/login`           | Login            | Email + password for authorized admin users      |
| `/forgot-password` | Forgot password  | Sends OTP to registered email                    |
| `/verify-otp`      | OTP verification | Validates OTP (debug OTP shown when email fails) |
| `/reset-password`  | Reset password   | Sets new password after OTP                      |
| `/logout`          | —                | Clears session                                   |


Errors (invalid password, unauthorized email, OTP failure) are shown via toast after redirect.

### Home (`/`)

- Personalized greeting using the user’s display name
- **Today’s note** — random motivational message from `static/data/home_messages.txt` (120 messages)
- Image carousel introducing tracking features
- View-only mode shows the shared user email instead of edit actions

### Menses log


| Route                | Page             | Description                                                          |
| -------------------- | ---------------- | -------------------------------------------------------------------- |
| `/entries`           | Entry list       | Paginated table (12 rows/page), sortable columns, mobile card layout |
| `/input`             | Add / edit entry | Daily symptom and flow logging                                       |
| `/delete-entry/<id>` | —                | POST delete (logged-in users only)                                   |


**Daily entry form (`/input`):**

- Date picker (defaults to today for new entries)
- Period tracking: flow amount (1–10), period start marker, start/end times, “period ended” mode
- Symptoms: Period, Craving, Irritation, Diarrhea, Feeling Weird (with intensity where applicable)
- Optional notes
- Client validation via toast (intensity required when symptom checked; at least one symptom required)
- User defaults from Customize pre-fill new entries

### Sex entries


| Route                      | Page | Description                                      |
| -------------------------- | ---- | ------------------------------------------------ |
| `/sex-entries`             | List | Paginated table (11 rows/page), sortable columns |
| `/sex-entries/add`         | Add  | Date, sex type, position, notes                  |
| `/sex-entries/edit/<id>`   | Edit | Same fields as add                               |
| `/sex-entries/delete/<id>` | —    | POST delete                                      |


Default sex types: Soft, Hard (Protected), Hard (Pullout), Hard (Natural). Default positions: Missionary, Cowgirl, Doggy, Side, Standing. Custom types and positions are managed under Customize.

### Body metrics


| Route                        | Page | Description                                        |
| ---------------------------- | ---- | -------------------------------------------------- |
| `/weight-height`             | List | Paginated metrics with BMI, search, column sorting |
| `/weight-height/add`         | Add  | Weight (kg), height (cm), live BMI preview         |
| `/weight-height/edit/<id>`   | Edit | Update existing record                             |
| `/weight-height/delete/<id>` | —    | POST delete                                        |


- **Use Previous Recorded Values** checkbox autofills from the latest entry via `/api/weight-height/latest`
- Duplicate dates are rejected server-side
- Validation errors shown via toast

### Analytics (`/analytics`)

Unified dashboard with filter bar (group by: daily / weekly / monthly / yearly; limit: all or last N records).

**Period section**

- Summary cards: cycle length, period duration, regularity, prediction confidence
- Flow line chart and symptom frequency doughnut (excluding period symptom)
- Completed cycle history table

**Sex section**

- Bar charts for sex type and position distribution
- Summary stats from logged entries

**Body metrics section**

- Current weight, change, height, BMI, stability badge
- Min / max / average stat tables
- Weight trend and BMI progression charts (height trend chart is not shown)

Chart load failures display an inline empty state **and** a danger toast with the error message.

### Forecast (`/predictor`)

Cycle phase intelligence powered by `utils/fertility.py`:

- Interactive timeline of past, current, and predicted cycles (hover for phase, safety rating, fertility chance)
- Phase-specific probability curves (period, building, fertile, luteal modes)
- Trend charts for cycle length and ovulation day over time
- Context cards: BMI, recent sex entries, predicted vs actual cycle comparison

Requires enough historical period data; empty states guide the user without blocking the page.

### Customize (`/customize`)

- **Symptoms grid** — view, edit, delete custom symptoms; system defaults can be customized but core symptoms (date, period) cannot be removed
- **Sex types & positions** — add, edit, delete custom options
- **Default selections** — pre-fill flow amount, symptom intensities, and sex entry defaults on new forms

Modal validation errors (empty name, etc.) use toast notifications.

### Settings (`/settings`)

- **Login password** — change with current + new + confirm fields
- **View-only password** — verify current to reveal and copy; separate form to set a new shared password
- Copy action shows a success toast

### View-only sharing


| Route                        | Description                                          |
| ---------------------------- | ---------------------------------------------------- |
| `/view-analytics-login`      | Email + view password for a specific user’s data     |
| `/view-analytics-mode`       | Password-only entry when email is already in session |
| `/view-analytics/<password>` | Legacy direct link                                   |


View-only users see Home, Menses, Sex Entries, Weight & Height, Analytics, and Forecast **without** edit, delete, Customize, or Settings. All write actions are blocked server-side.

---

## UI components (`templates/macros.html`)


| Macro        | Use                                                       |
| ------------ | --------------------------------------------------------- |
| `card`       | Glass-style container with optional header icon           |
| `btn`        | Buttons and links with variants, sizes, icons             |
| `table`      | Responsive scrollable table wrapper                       |
| `pagination` | Server-side page navigation                               |
| `input_box`  | Labeled inputs with optional icons                        |
| `dropdown`   | Styled custom dropdown synced to hidden `<select>`        |
| `checkbox`   | Toggle checkbox                                           |
| `textarea`   | Multi-line input                                          |
| `stat_card`  | Dashboard metric with badge/trend                         |
| `alert`      | Inline informational blocks (empty states, modals)        |
| `error_list` | Server-side form error list (rare; most errors use toast) |


### Theme and responsiveness

- **Light / dark mode** — toggled from the navbar; preference stored in `localStorage` (`data-bs-theme` on `<html>`)
- **Mobile nav** — collapsible right-side drawer below 768px width
- **Tables** — horizontal scroll on small screens; menses log switches to card layout on mobile
- **Forms** — centered columns (`col-xl-`*, `col-md-*`) stack on narrow viewports
- **Toasts** — fixed top-right, max width 360px, adapt to viewport padding

CSS variables in `styles.css` drive colors for both themes (`--primary-color`, `--card-bg`, `--metric-bg`, etc.).

---

## Firestore schema

Documents are nested under `users/{email}/`.

### `users/{email}`

```json
{ "email": "user@example.com" }
```

### `users/{email}/users_setting/settings`

```json
{
  "email": "user@example.com",
  "password": "hashed",
  "view_password": "hashed_view_only",
  "custom_symptoms": [],
  "disabled_symptoms": [],
  "symptom_overrides": {},
  "custom_sex_types": [],
  "custom_sex_positions": [],
  "defaults": {
    "flow_amount": 5,
    "weird_intensity": "medium",
    "sex_type": "",
    "position": ""
  },
  "created_at": "timestamp"
}
```

### `users/{email}/period_entries/{id}`

```json
{
  "date": "2026-06-15",
  "symptoms": [
    { "name": "period", "flow_amount": 7, "start_marked": true },
    { "name": "weird", "intensity": "medium" }
  ],
  "notes": "",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### `users/{email}/weight_height_entries/{id}`

```json
{
  "date": "2026-06-15",
  "weight": 67.5,
  "height": 172.0,
  "bmi": 22.82,
  "bmi_category": "Normal",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### `users/{email}/sex_entries/{id}`

```json
{
  "date": "2026-06-15",
  "sex_type": "Soft",
  "position": "Missionary",
  "notes": "",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

## REST API

All JSON APIs require an authenticated session (`@api_auth_required` or `@api_login_required`).


| Method | Endpoint                       | Description                                   |
| ------ | ------------------------------ | --------------------------------------------- |
| GET    | `/api/weight-height`           | All body metrics (newest first)               |
| GET    | `/api/weight-height/latest`    | Most recent entry                             |
| POST   | `/api/weight-height`           | Create entry (validates BMI, duplicate dates) |
| PUT    | `/api/weight-height/<id>`      | Update entry                                  |
| DELETE | `/api/weight-height/<id>`      | Delete entry                                  |
| GET    | `/api/weight-height/analytics` | Weight/height/BMI summary                     |
| GET    | `/api/weight-height/trends`    | Ascending entries for charts                  |
| GET    | `/api/sex-entries/trends`      | Sex entries for analytics charts              |
| GET    | `/analytics-data`              | Period/symptom data for analytics charts      |


API errors return JSON `{ "error": "message" }` with appropriate HTTP status codes (400, 401, 404, 409).

---

## Analytics engine

### BMI


\text{BMI} = \frac{\text{weight (kg)}}{(\text{height (cm)} / 100)^2}


Categories: Underweight (<18.5), Normal (18.5–24.9), Overweight (25–29.9), Obese (≥30).

### Body metric stability

Compares the last three entries. **Stable** if variation ≤ 0.5 units (≤ 0.2 for BMI); **Increasing** / **Decreasing** if strictly monotonic; otherwise **Fluctuating**.

### Cycle averages

Period dates are grouped into contiguous blocks (gap ≤ 2 days). Cycle starts use the `start_marked` flag. Averages drive prediction windows.

### Regularity


| Cycle length spread | Label              | Consistency score |
| ------------------- | ------------------ | ----------------- |
| ≤ 2 days            | Regular            | 95%               |
| ≤ 5 days            | Moderately Regular | 80%               |
| > 5 days            | Irregular          | 60%               |


### Prediction confidence

Scales from 20% (no cycles) up to 95% based on number of historical cycles tracked.

### Fertility probability (by cycle day)


| Phase                               | Probability                                      |
| ----------------------------------- | ------------------------------------------------ |
| Menstruation (day ≤ period length)  | 30%                                              |
| Pre-fertile window                  | 40%                                              |
| Fertile window (ovulation ± window) | up to 100% (declines 15% per day from ovulation) |
| Luteal / post-ovulation             | 30% (20% past average cycle length)              |


---

## Security notes

- Passwords are bcrypt-hashed before storage
- Only emails in `ADMIN_USER` may register/log in
- View-only mode uses a separate hashed password and cannot mutate data
- Firestore credentials must never be committed; use `.env` or host secrets only

---

## Tech stack


| Layer    | Technology                            |
| -------- | ------------------------------------- |
| Backend  | Flask, Jinja2                         |
| Database | Google Cloud Firestore                |
| Auth     | Flask sessions, bcrypt                |
| Frontend | Bootstrap 5, Font Awesome 6, Chart.js |
| Email    | SMTP (optional, for OTP reset)        |
| Server   | Gunicorn (production)                 |


