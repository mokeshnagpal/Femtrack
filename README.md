# FemTrack — Personal Reproductive Health Platform

FemTrack is a private, secure web application designed for menstrual cycle tracking, cycle phase forecasting, intimacy and sexual activity logging, biometric analytics, and shareable read-only dashboard access. All data is securely persisted in Google Cloud Firestore. The platform features responsive layouts, light/dark mode theme support with automatic chart updates, and a toast-based notification system.

---

## Setup & Quick Start

Follow these steps to configure, install, and run FemTrack on your local machine.

### 1. Prerequisites

Before running the application, make sure you have:
* **Python 3.10+** installed on your system.
* **Google Firebase Project**: Set up a Firebase project and enable the Firestore database in Native mode.
* **Firebase service account credentials**: Generate a private key JSON file from the Firebase console (Project Settings > Service Accounts).

### 2. Installation

Clone the repository and prepare the virtual environment:

```bash
git clone <repository-url>
cd Femtrack

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Windows (CMD)
.\venv\Scripts\activate.bat
# macOS / Linux
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root directory and add the following keys:

```env
SECRET_KEY=your_flask_secret_key
FIREBASE_CREDENTIALS={"type":"service_account","project_id":"your-project-id",...}
ADMIN_USER=your_admin_email@gmail.com
DEFAULT_PASS=your_first_time_password
VIEW_PASS=default_view_only_password
EMAIL_USER=your_smtp_email@gmail.com
EMAIL_PASSWORD=your_smtp_app_password
```

#### Environment Variables Reference

| Variable | Required | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Secret key used by Flask to secure and sign session cookies. |
| `FIREBASE_CREDENTIALS` | Yes | The complete Firebase Service Account JSON credentials object compressed into a single-line string. |
| `ADMIN_USER` | Yes | A comma-separated list of emails authorized to register and sign in as administrators. |
| `DEFAULT_PASS` | Yes | Temporary password used during first-time login for an admin email before their profile is created in Firestore. |
| `VIEW_PASS` | No | Default view-only shared access password. Can be changed later via the Settings page. |
| `EMAIL_USER` / `EMAIL_PASSWORD` | No | SMTP credentials used for sending OTP codes for password recovery. |

### 4. Running the Application Locally

Start the Flask development server:

```bash
python app.py
```

* The app will spin up at `http://127.0.0.1:5000`.
* **First Login**: Use an email address defined in `ADMIN_USER` and the `DEFAULT_PASS` from your `.env` file. Upon first login, the application will initialize your document database.
* **Security Action**: Immediately navigate to the **Settings** page (`/settings`) to update your temporary password to a secure personal password.

### 5. Production Deployment

The application lists `gunicorn` in its dependencies for production environments. To start the Gunicorn WSGI server:

```bash
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

Ensure all environment variables defined in your `.env` are configured in your production host environment (e.g. Render, Railway, Heroku).

---

## System Architecture

FemTrack is built with a decoupled architecture, separating routing logic from core computation.

```
Browser (Bootstrap 5 + Chart.js)
        │
        ▼
   app.py  ── routes, sessions, flash → toast
        │
        ├── utils/firestore_service.py   Firestore CRUD
        ├── utils/auth.py                Password hashing (bcrypt)
        ├── utils/auth_decorators.py     Login requirements & API access guards
        ├── utils/biometrics.py          BMI and biometric metrics stability
        ├── utils/fertility.py           Cycle predictions and fertility scoring
        ├── utils/date_helpers.py        Date sorting, local conversions, charts formatting
        ├── utils/email_service.py       SMTP mail forwarding
        └── utils/otp.py                 One-time password lifecycle
        │
        ▼
   Google Cloud Firestore
```

### Core Architectural Features

* **Timezone-Safe Formatting**: Front-end dates are calculated and parsed using local browser timezones via a helper function `toLocalIsoDate(date)` rather than UTC-based `.toISOString()`. This prevents 1-day offsets that typically occur in timezones ahead of UTC (such as IST, +5:30).
* **Live Chart Mode Sync**: An HTML element `MutationObserver` monitors changes to the `data-bs-theme` attribute (Light/Dark mode). On theme toggle, it queries updated CSS variables (`--text-color` and `--border-color`), overrides standard Chart.js defaults, and instantly redraws all charts to maintain readability and high contrast.
* **Persistent Sessions**: Sessions are permanent with a 10-year lifetime. They refresh with each request, keeping users logged in on their private devices.
* **Toasts Notification Queue**: Validation issues, system errors, and success updates are broadcast to the user via a top-right toast stack. Client-side form handlers validate forms locally before submission to reduce server round-trips.

---

## Project Directory Map

```
Femtrack/
├── app.py                 Main web app entry point, defines page routing and API routes
├── config.py              Firestore client initialization and environment validation
├── requirements.txt       List of Python packages required
├── templates/             Jinja2 HTML templates
│   ├── base.html          Global navbar, mobile nav drawer, theme toggles, and toast container
│   ├── macros.html        Reusable components (buttons, stat cards, glassmorphic panels, forms)
│   ├── forecast.html      Timeline visualizations, forecast graphs, and cycle calendars
│   ├── analytics.html     Historical charts (symptoms, weight, intimacy distributions)
│   └── ...                Input and log forms
├── static/                Static files
│   ├── css/styles.css     Global styles, custom UI variables, and responsive classes
│   ├── js/error-handler.js Form interceptors and error alert triggers
│   ├── data/              Motivational daily note files
│   ├── icons/             Symptom SVG vector icons
│   └── images/            Hero carousel assets
└── utils/                 Decoupled utility modules
```

---

## User Manual: How to Use Each Feature

### 1. Daily Menses & Symptom Tracking
Record menses flows, check symptoms, and write logs.

* **Viewing Your Menses Logs**: Navigate to **Menses** (`/entries`). Desktop views show a paginated table (12 entries per page) with search filters and column sorting. On mobile screens, the page automatically switches to a list of premium card panels.
* **Adding a Daily Entry**:
  1. Click **Add Period Entry** (or go to `/input`).
  2. Select the Date (defaults to today).
  3. **Cycle Start**: Check the **Start of Cycle (First day of period)** box if this is the first day of a new period. This flag triggers the cycle length calculations and starts a new cycle in the database.
  4. **Period Ended**: Check **Period Ended** if your bleeding has stopped to close the active flow window.
  5. **Flow Amount**: Use the slider (1 to 10) to log bleeding volume.
  6. **Symptoms**: Check off any symptoms you experienced: `Period`, `Craving`, `Irritation`, `Diarrhea`, or `Feeling Weird`. If you check a symptom, select its intensity (`Low`, `Medium`, or `High`).
  7. **Notes**: Add optional private notes.
  8. Click **Save Entry**.
* **Editing/Deleting**: Click the pencil icon or the trash icon next to an entry on the logs list to modify or delete it.

### 2. Intimacy & Sexual Activity Logs
Keep a record of your sexual activity, positions, and logs.

* **Viewing Intimacy Logs**: Navigate to **Sex Entries** (`/sex-entries`). Review past dates, intimacy types, and positions. On mobile devices, this view renders as an ordered card list.
* **Adding an Entry**:
  1. Navigate to `/sex-entries/add` (or click **Add Entry** from the intimacy list).
  2. Choose the Date, **Intimacy Type** (e.g. Soft, Hard - Protected, Hard - Pullout, Hard - Natural), and the **Position** used (e.g. Missionary, Doggy, Cowgirl, Side, Standing).
  3. Add notes if desired and click **Save**.
* **Managing Custom Options**: Customize your types and positions on the **Customize** page.

### 3. Biometrics & Body Metrics
Track your weight, height, and body mass index over time.

* **Viewing Metrics**: Navigate to **Weight & Height** (`/weight-height`). The page lists weight logs, height entries, computed BMI metrics, and classification badges (e.g., Normal, Overweight).
* **Adding a Biometric Log**:
  1. Click **Add Metric** (or navigate to `/weight-height/add`).
  2. Input your weight in kilograms (kg) and height in centimeters (cm).
  3. **Live Preview**: The form computes your BMI and displays its category card in real-time.
  4. **Autofill Helper**: Check the **Use Previous Recorded Values** box to pre-fill the form fields with your last recorded metrics.
  5. Click **Save**. Duplicate dates are rejected to keep metrics clean.

### 4. Cycle Forecasting & Forecast Dashboard
Review your cycle timeline, predictions, and safety forecasts.

* **Baseline Overview Cards**:
  - **Current Phase Window**: Shows your active phase (e.g. Period/Menstruation), its active date range, and the average period length. Also displays the calculated percentage probability of today falling into this phase.
  - **Next Phase Window**: Forecasts the next chronological phase (e.g. transitioning from Period to Building/Follicular), predicted date ranges, and average phase duration.
  - **Typical Cycle**: Summarizes average cycle duration, regularity, and overall prediction confidence.
* **Selected Phase Focus**:
  - Select a phase (Period, Building, Fertile, or Luteal) from the **Cycle Phase Focus** dropdown.
  - The **Phase Forecast Graph** updates to plot your statistical probability curve for that specific phase.
  - The calendar grids (Previous, Current, and Upcoming cycles) adjust their colors to highlight when you are predicted to enter that phase.
* **Calendar Day Tooltips**:
  - Hover over a calendar cell to see details: date, days in cycle, predicted phase, pregnancy risk, and safety rating.
  - If intimacy is logged on that day, a heart icon is displayed. Hover over the day, move your cursor onto the popup window, and click **View Details** to open the Intimacy Modal.
* **Intimacy Details Modal**:
  - A split-pane view displaying logged intimacy parameters on the left and computed cycle context metrics (Phase, Period Probability, and Pregnancy Likelihood) for that date on the right.

### 5. Analytics Dashboard
Analyze patterns across months and years.

* **Telemetries**: Navigate to **Analytics** (`/analytics`). Review charts for period flows, symptom distributions, intimacy preferences, and weight/BMI trends.
* **Data Filters**: Use the top menu bar to group data by Daily, Weekly, Monthly, or Yearly windows, and limit the history length to filter charts dynamically.

### 6. Customization
Tailor the application to your logging habits.

* Navigate to **Customize** (`/customize`).
* **Custom Symptoms**: Add new symptoms (e.g., "Headache" or "Cramps") to your checklist, or delete ones you do not wish to track. Pre-defined core symptoms cannot be deleted.
* **Custom Intimacy**: Add new intimacy categories or positions.
* **Pre-fill Defaults**: Set default values (e.g. default flow amount, pre-checked symptoms, default position) that load automatically when creating new entries.

### 7. Partner & Shared Access (View-Only Mode)
Safely share your cycle forecasts and logs with your partner or doctor.

* **Enabling Shared Access**:
  1. Navigate to **Settings** (`/settings`).
  2. Scroll to the **View-only password** section. Verify your primary password to reveal or set a shared view-only password.
  3. Share your tracking email and the view-only password with your partner.
* **Accessing the View-Only Dashboard**:
  - Direct your partner to `/view-analytics-login`.
  - Once authenticated, they can view your Home, Menses table, Intimacy list, Weight logs, Analytics charts, and Forecast calendars.
  - **Security Restrictions**: View-only sessions have no write permissions. All add/edit/delete actions, settings modification forms, and customization pages are completely hidden from view.

---

## Data Engine Calculations

### Body Mass Index (BMI) & Stability
* Computed using weight and height. Categories include Underweight ($<18.5$), Normal ($18.5 - 24.9$), Overweight ($25 - 29.9$), and Obese ($\ge 30$).
* Stability checks compare the standard deviation across the last three logs. Returns **Stable** (variation $\le 0.5$), **Increasing** / **Decreasing** (strictly monotonic), or **Fluctuating**.

### Regularity & Confidence Ratings
* Variance in cycle lengths determines regularity categories:
  - **Regular** ($\le 2$ days spread): 95% forecast confidence.
  - **Moderately Regular** ($\le 5$ days spread): 80% forecast confidence.
  - **Irregular** ($> 5$ days spread): 60% forecast confidence.
* Prediction confidence scales from 20% (initial setup) to 95% as history is logged.

### Cycle Phase Transitions
The application tracks four key phases chronologically in a loop:
$$\text{Menstruation} \rightarrow \text{Follicular (Building)} \rightarrow \text{Ovulation (Fertile)} \rightarrow \text{Luteal} \rightarrow \text{Menstruation}$$
* **Menstruation**: Days $1$ to Avg Period Length.
* **Follicular**: Days after period to Ovulation - 6.
* **Ovulation**: Ovulation - 5 to Ovulation + 1 (Peak fertility day).
* **Luteal**: Ovulation + 2 to End of cycle.

---

## REST API Reference

JSON endpoints require session authorization and return details or error messages.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/weight-height` | Lists all logged metrics (newest first). |
| `GET` | `/api/weight-height/latest` | Retrieves the most recent weight/height record. |
| `POST` | `/api/weight-height` | Submits a new metric record (validates limits and duplicates). |
| `PUT` | `/api/weight-height/<id>` | Updates an existing biometric record. |
| `DELETE` | `/api/weight-height/<id>` | Removes a biometric record. |
| `GET` | `/api/weight-height/analytics` | Returns averages and BMI distribution categories. |
| `GET` | `/api/weight-height/trends` | Returns ascending records formatted for Chart.js. |
| `GET` | `/api/sex-entries/trends` | Returns intimacy type and position timelines for Chart.js. |
| `GET` | `/analytics-data` | Returns cycle lengths, menses flows, and symptoms counts for Chart.js. |

---

## Security Specifications

* **Password Security**: Primary and view-only passwords are encrypted and checked using `bcrypt`.
* **Registration Controls**: Registration is restricted to email addresses defined in the `.env` configuration file under `ADMIN_USER`.
* **Data Write Separation**: Session access tokens block mutation requests (POST/PUT/DELETE) on the server-side when logged in under a view-only session.

---

## Tech Stack Mappings

* **Backend**: Flask (Python), Jinja2 templates
* **Database**: Google Cloud Firestore (NoSQL document store)
* **Security & Auth**: Bcrypt password hashing, secure Flask session validation
* **Frontend**: Bootstrap 5, Font Awesome 6 icons, Chart.js visualizations
* **Email**: SMTP server routing for one-time password (OTP) delivery (optional)
* **Deployment**: Gunicorn WSGI server (production)
