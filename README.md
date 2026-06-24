# 🌸 FemTrack — Technical Documentation & Architecture Manual

FemTrack is an integrated reproductive health intelligence and personal analytics platform. It combines menstrual cycle tracking, fertility predictions, sexual activity logs, body composition metrics, and private sharing into a single, unified Flask backend architecture.

---

## 🏗️ System Architecture & Mechanics

### Modular Backend & Frontend Architecture
FemTrack utilizes a decoupled, professional module architecture:
1. **Routing and Controllers**: Located in [app.py](file:///d:/PROJECTS/SELF%20PROJECTS/__TOOLS%20I%20AM%20USING/WEBSITE/Femtrack/app.py). It acts purely as a routing layer delegating calculations, database interactions, and security checks to decoupled service utilities in the `utils/` package.
2. **Jinja2 Macro Library**: Front-end interface elements (buttons, inputs, dropdowns, tables, and pagination) are standardized as reusable templates in [macros.html](file:///d:/PROJECTS/SELF%20PROJECTS/__TOOLS%20I%20AM%20USING/WEBSITE/Femtrack/templates/macros.html).
3. **Database Access Layer**: Database queries are centralized in [firestore_service.py](file:///d:/PROJECTS/SELF%20PROJECTS/__TOOLS%20I%20AM%20USING/WEBSITE/Femtrack/utils/firestore_service.py).
4. **Calculations & Math Services**: Isolated in dedicated modules (e.g. `biometrics.py`, `fertility.py`).

### Calculations & Analytics Engine
* **BMI Logic**: Calculated dynamically as $\text{Weight (kg)} / \left(\frac{\text{Height (cm)}}{100}\right)^2$.
* **Body Metrics Stability**: Compares the last 3 entries. Classified as `Stable` if variation is $\le 0.5$ units (or $\le 0.2$ for BMI), `Increasing` / `Decreasing` if strictly monotonic, or `Fluctuating` otherwise.
* **Cycle & Period Averages**: Groups sorted period dates into contiguous blocks (gap $\le 2$ days). Computes consecutive cycle start dates (from the `start_marked` flag) and averages lengths.
* **Regularity Score**: Standard deviation/spread of cycle lengths:
  * Difference $\le 2$ days $\rightarrow$ `Regular` (95% fertility window consistency).
  * Difference $\le 5$ days $\rightarrow$ `Moderately Regular` (80% consistency).
  * Difference $> 5$ days $\rightarrow$ `Irregular` (60% consistency).
* **Prediction Confidence**: Scaled from 20% (no cycles) to 95% based on the number of historical cycles tracked.
* **Fertility Probability Curve**: Estimated dynamically for the current cycle day:
  * Period phase (Day $\le$ period duration): 30%
  * Pre-fertility window (Day $<$ ovulation $- 5$): 40%
  * Fertile window (ovulation $- 5 \le$ Day $\le$ ovulation $+ 1$): Peak up to 100% (declines by 15% per day away from ovulation)
  * Post-ovulatory / luteal phase: 30% (drops to 20% past average cycle length)

---

## 🖥️ Page & Interface Details

### 1. Home Dashboard (`/`)
* **Overview**: Simple entry page checking authentication.
* **Components**: Welcomes the user with a customized formatted name and provides navigation options.

### 2. Daily Log / Add Entry Page (`/input`)
* **Overview**: Form to track daily symptoms and menstrual flow.
* **Components**:
  * Date picker with formatted date display.
  * Flow amount range (1-10) and intensity selectors.
  * Checklist for symptoms: Period, Craving, Irritation, Diarrhea, Feeling Weird.
  * **Period Start** checkbox to designate cycle start dates.
  * Smart validation preventing duplicate entries for the same date.

### 3. Body Metrics Log & Form (`/weight-height`, `/weight-height/add`, `/weight-height/edit/<id>`)
* **Overview**: Records weight and height logs.
* **Components**:
  * Log listing with search filtering and sorting columns (date, weight, height, BMI).
  * Add/Edit forms with live BMI calculation.
  * **Use Previous Recorded Values** checkbox: Autofills weight/height using the user's latest record.

### 4. Unified Health Analytics Dashboard (`/analytics`)
* **Overview**: Aggregates all reproductive and physical health trends.
* **Components**:
  * **Summary cards**: Cycle length, period duration, cycle regularity, and confidence score.
  * **Body Metrics cards**: Current weight, weight change, current height, current BMI, stability, and min/max/average stats tables.
  * **Interactive charts**: Period flow lines, symptom doughnuts (excluding period), weight trends and BMI progression.
  * **History log**: Table of completed previous cycle ranges.

### 5. Cycle Predictor & Fertility Intelligence (`/predictor`)
* **Overview**: Predictions and cycle phase visualization.
* **Components**:
  * **Cycle timeline**: Interactive visual timeline of previous, current, and upcoming cycles with hover tooltips (shows date, phase, safety rating, and fertility chance).
  * **Probability Curve**: Live line chart showing the fertility probability curve across the current cycle.
  * **Trends Chart**: Line charts tracking cycle length and ovulation day changes.

### 6. Settings Page (`/settings` & `/customize`)
* **Overview**: User customizations and shared credentials management.
* **Components**:
  * Login password updates.
  * Copy shared link for read-only analytics access.
  * Add custom symptoms (with or without intensity scales).
  * Disable system-default symptoms.
  * Setup custom default form parameters.

### 7. Shared Read-Only Analytics (`/view-analytics/<password>`)
* **Overview**: Password-protected sharing mode.
* **Components**: Renders the Unified Analytics and Predictor pages with edit/delete buttons hidden.

---

## 💾 Database Schema & API Endpoints

### Nested Subcollection Firestore Schema
FemTrack uses a nested subcollection hierarchy under the root `users` collection to segment setting controls, daily period logs, and physical body metrics:

#### Root Collection: `users`
* Document ID: `user_email` (e.g., `user@example.com`)
* Payload:
```json
{
  "email": "user@example.com"
}
```

#### Nested Subcollection: `users_setting`
* Document ID: `settings` (Unique settings document per user)
* Payload:
```json
{
  "email": "user@example.com",
  "password": "hashed_password",
  "view_password": "hashed_view_only_password",
  "custom_symptoms": [{"name": "headache", "display_name": "Headache", "has_intensity": true, "system_default": false}],
  "disabled_symptoms": [],
  "symptom_overrides": {},
  "defaults": {"flow_amount": 5, "weird_intensity": "medium"},
  "created_at": "timestamp"
}
```

#### Nested Subcollection: `period_entries`
* Document ID: Random firestore hash (`{entry_id}`)
* Payload:
```json
{
  "date": "2026-06-15",
  "symptoms": [
    {"name": "period", "flow_amount": 7, "start_marked": true},
    {"name": "weird", "intensity": "medium"}
  ],
  "notes": "Optional log comments",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

#### Nested Subcollection: `weight_height_entries`
* Document ID: Random firestore hash (`{entry_id}`)
* Payload:
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

### Backend REST APIs

* `GET /api/weight-height`: Returns all body metrics entries for the user (sorted by date descending).
* `GET /api/weight-height/latest`: Returns the most recent body metrics entry.
* `POST /api/weight-height`: Creates a new entry (validates values, computes BMI, checks duplicate dates).
* `PUT /api/weight-height/<id>`: Updates weight or height for a specific entry.
* `DELETE /api/weight-height/<id>`: Deletes a specific entry.
* `GET /api/weight-height/analytics`: Returns structured weight, height, and BMI analytics summary.
* `GET /api/weight-height/trends`: Returns all entries (sorted by date ascending) for chart plotting.
* `GET /analytics-data`: Returns sorted daily symptom entries for flow charts.

---

## 🛠️ Reusable & Modular Components Catalog

### 🎨 Frontend UI Jinja2 Macros (`templates/macros.html`)
To ensure styling consistency, dark/light theme alignment, and responsiveness, the layout components are implemented as Jinja2 macros:
1. **`card`**: Standard glassmorphic container with support for titles, custom header classes, and icons.
2. **`btn`**: Unified button and link rendering system with color variants, size modifiers, and icons.
3. **`table`**: Table wrapper with responsive scroll and hover aesthetics.
4. **`pagination`**: Interactive pagination navigation panel.
5. **`input_box`**: Unified input box with labels, input validations, values, and optional prepended icons.
6. **`dropdown`**: Select drop-down form component.
7. **`checkbox`**: Toggle checkbox input element.
8. **`textarea`**: Form textareas component.
9. **`stat_card`**: Dashboard stats visual metric card with trend lines, badges, and units.
10. **`alert`**: Dismissible dynamic notification alerts.
11. **`error_list`**: Clean form validation error lists.

### ⚙️ Backend Generalised Utilities (`utils/`)
The application features a generalized python service layer to cleanly isolate concerns:
1. **`auth_decorators.py`**: Route and API filters (`@login_required`, `@auth_required`, `@api_login_required`, `@api_auth_required`).
2. **`date_helpers.py`**: Formatting and parsing library for dates, sorting, and charts formatting.
3. **`firestore_service.py`**: Nested subcollection Firestore API wrappers for reading/updating data.
4. **`biometrics.py`**: BMI calculation formulas and stability trends.
5. **`fertility.py`**: Timelines predictions, confidence scores, and fertility probability formulas.

---

## 🔄 Recent Changes & Enhancements (Changelog)

- **Navbar Brand Cleanup**: Removed the word "Femtrack" from the navbar brand text, leaving only the lotus icon and logo.
- **Predictor Renaming & Refactoring**:
  - Renamed "Cycle Predictor" to "Forecast" across the navbar, home page dashboard cards, and the predictions page.
  - Replaced the `fas fa-star` icon with the `fas fa-wand-magic-sparkles` (Magic Wand) icon.
  - Removed instances of the word "cycle" from headings and summaries on the predictions page.
- **Cleanup of Unused Files**: Deleted the unused `templates/signup.html` template.
- **Server-Side Pagination (Max 12 Rows)**:
  - Fixed entries per page at exactly 12 across all logs.
  - Removed "Per Page" and "Filter" selectors from the entries page.
  - Re-engineered backend logic to perform a count query on Firestore and fetch exactly 12 records using `.limit(12).offset(12 * (page-1))`.
  - Upgraded components to utilize server-side pagination with page button grids (`prev 1 2 3 ... n next`).
- **In-Memory Table Sorting**:
  - Added header sort caret/arrow indicators to both the entries log table and the weight/height metrics table.
  - Enabled client-side in-memory sorting of the active page's 12 records without requiring additional database hits.
- **Custom Dropdown Component**:
  - Re-implemented the `dropdown` macro in `macros.html` to output a premium, styled Bootstrap dropdown selector instead of standard select lists.
  - Created a global JS sync helper to update standard form values, matching dark mode configurations and animations.
## 2026-06-23 UI, Analytics, and Sex Entries Update

- Enlarged the navbar logo and added active page highlighting for all primary navigation items.
- Added a right-side mobile navigation drawer with cleaner light/dark styling.
- Replaced global flashed alerts with a reusable top-right toast stack that auto-dismisses after 4 seconds.
- Refreshed the site palette away from the previous light-blue/purple-heavy theme and added reusable soft panels for light and dark mode.
- Removed the height trend graph from analytics while keeping weight and BMI charts.
- Split analytics into clearer Period, Sex, and Body Metrics sections, including improved weight/BMI summary stat boxes.
- Removed the Forecast empty-state Add Entry button and added BMI, recent sex-entry, and predicted-vs-actual context cards.
- Updated Settings so the main password flow remains unchanged, while view-only password management is split into:
  - verify current view-only password, reveal it, and copy it;
  - set a new view-only password directly with new/confirm fields.
- Removed the Back to Home button from Settings.
- Added `/sex-entries`, `/sex-entries/add`, `/sex-entries/edit/<id>`, `/sex-entries/delete/<id>`, and `/api/sex-entries/trends`.
- Sex entries are stored at `users/{email}/sex_entries` with `date`, `sex_type`, `position`, `notes`, `created_at`, and `updated_at`.
- Sex Entries uses an 11-row paginated table and the same read-only/edit protections as the other log pages.
- Added customizable sex types and positions in `/customize`; defaults remain available and custom options are stored in the user settings document.
- Simplified the home page by removing the old navigation card buttons and replacing the static tip with a random message loaded from `static/data/home_messages.txt`.
- Added 120 rotating home messages for daily tracking prompts.

