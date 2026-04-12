# 🌸 Menstrual Cycle Tracker & Fertility Predictor

A comprehensive Flask-based web application for tracking menstrual cycles, fertility prediction, and detailed analytics with Firebase Firestore integration and OTP-based authentication.

## ✨ Features

- 🔐 **Secure Authentication**: OTP-based email verification for signup
- 📊 **Advanced Analytics**: Interactive charts with symptom distribution and cycle patterns
- 🔮 **Fertility Predictor**: AI-powered cycle prediction with fertility windows and phase tracking
- 📱 **Responsive Design**: Mobile-first Bootstrap 5 UI with dark/light mode
- 🔒 **Data Privacy**: Password-protected analytics sharing with read-only access
- 📈 **Visual Timeline**: Custom color-coded cycle timeline with fertility intensity
- 🎯 **Phase Indicators**: Real-time cycle phase badges with probability scores
- 📅 **Smart Date Formatting**: User-friendly "DD Month YYYY" date display
- 🔍 **Data Distinction**: Visual indicators for actual vs calculated predictions

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Database**: Firebase Firestore
- **Frontend**: HTML, CSS, Bootstrap 5, JavaScript
- **Visualization**: Custom Timeline Charts (replaced Chart.js)
- **Authentication**: Email OTP via SMTP
- **Charts**: Interactive fertility probability calculations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Firebase project with Firestore enabled
- Gmail account for SMTP (or any SMTP provider)

### Installation

1. **Clone/Download** the project
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Firebase Setup

1. Create a Firebase project at [Firebase Console](https://console.firebase.google.com/)
2. Enable Firestore Database
3. Generate service account key:
   - Project Settings → Service Accounts → Generate new private key
   - Save as `firebase_key.json` in project root

### Email Configuration

1. **For Gmail**:
   - Enable 2-factor authentication
   - Generate App Password at [Google App Passwords](https://myaccount.google.com/apppasswords)
2. **Update `.env`** with credentials

### Environment Variables

Create `.env` file in project root:

```env
SECRET_KEY=your_secret_key_here
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

### Run Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## 📊 Database Structure

### Users Collection
```json
{
  "email": "user@example.com",
  "password": "hashed_password",
  "view_password": "hashed_password",
  "analytics_access_enabled": false,
  "created_at": "timestamp"
}
```

### Entries Collection
```json
{
  "user_id": "user@example.com",
  "date": "2024-01-15",
  "amount": 7,
  "intensity": "medium",
  "symptoms": ["period", "craving", "irritation"],
  "is_period_start": true,
  "created_at": "timestamp"
}
```

## 🎯 Usage Guide

### 1. Authentication
- **Signup**: Enter email → Receive OTP → Verify
- **Login**: Email + password (auto-generated on first login)

### 2. Home Dashboard
- Overview of your cycle tracking
- Quick navigation to all features

### 3. Add Entry Page
- **Date**: Auto-formatted as "15 January 2024"
- **Flow Amount**: 1-10 scale
- **Intensity**: Low/Medium/High
- **Symptoms**: Multi-select (period, craving, irritation, etc.)
- **Period Start**: Mark first day of menstruation

### 4. Analytics Dashboard
- **Interactive Charts**: Flow trends, symptom patterns
- **Cycle History**: Previous cycle summaries
- **Symptom Distribution**: Pie chart (excludes period for accuracy)
- **Date Filtering**: View specific time ranges

### 5. Cycle Predictor (NEW!)
- **Fertility Timeline**: Color-coded cycle visualization
- **Phase Indicators**: Real-time badges showing current phase
- **Probability Scores**: Accurate fertility intensity (30%-100%)
- **Data Distinction**: Green (actual) vs Gray (calculated) indicators
- **Safe Sex Windows**: Consistent low-fertility ranges for safe periods

#### Cycle Phases:
- 🔴 **Menstruation**: Safe sex period (30%-50% fertility)
- 🟡 **Follicular**: Building phase (40%-80% fertility)
- 🔶 **Ovulation**: Peak fertility (50%-100% fertility)
- 🟢 **Luteal**: Safe sex period (30%-50% fertility)

### 6. Settings
- **Change Password**: Update personal login password
- **View Password**: Shared analytics access password
- **Share Analytics**: Generate read-only analytics link

## 🔧 Advanced Features

### Fertility Prediction Algorithm
- **Cycle Length Analysis**: Based on historical data
- **Ovulation Timing**: Calculated from average cycle length
- **Fertility Windows**: 5 days before to 1 day after ovulation
- **Probability Scoring**: Dynamic intensity based on cycle day

### Timeline Visualization
- **Color Intensity**: Reflects fertility probability
- **Phase Boundaries**: Clear visual separation
- **Data Accuracy**: Distinguishes actual vs predicted data
- **Interactive Tooltips**: Detailed phase information and dates

### Smart Date Handling
- **Input**: Standard YYYY-MM-DD format
- **Display**: User-friendly "DD Month YYYY" format
- **Calculations**: Accurate date arithmetic for predictions

## 📈 Analytics Insights

- **Cycle Length Trends**: Average and historical analysis
- **Symptom Patterns**: Correlation with cycle phases
- **Fertility Windows**: Optimal conception periods
- **Period Regularity**: Cycle consistency tracking

## 🔒 Security & Privacy

- **OTP Authentication**: Email-based verification
- **Password Hashing**: Secure credential storage
- **Data Encryption**: Firebase security rules
- **Access Control**: Authorized user lists
- **Read-Only Sharing**: Password-protected analytics access

## 🎨 UI/UX Features

- **Dark/Light Mode**: Automatic theme switching
- **Mobile Responsive**: Optimized for all devices
- **Interactive Elements**: Hover effects and smooth transitions
- **Color Coding**: Intuitive phase and fertility indicators
- **Accessibility**: Screen reader friendly

---

**Built with ❤️ for comprehensive menstrual health tracking**
5. **Settings**: Change password, enable analytics sharing

## Security Features

- Password hashing with bcrypt
- OTP expiration (5 minutes)
- Input validation
- Protected routes
- Secure analytics sharing

## Deployment

The app can be deployed to:
- Firebase Hosting
- Render
- Railway
- Heroku
- Any Flask-compatible hosting service

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.