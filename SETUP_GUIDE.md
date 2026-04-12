# � Menstrual Cycle Tracker & Fertility Predictor - Admin Access Mode

## 📋 Complete Setup Instructions

### 1. **Configure Authorized Users**

Edit `.env` and add your email addresses:

```env
ADMIN_USER=nagpalmokesh@gmail.com,rachananagpal1978@gmail.com
VIEW_PASS=Mokesh87654321
```

**Only these emails can access the application.**

### 2. **Access the App**

**URL**: `http://localhost:5000`

### 3. **Login Process**

1. Go to `http://localhost:5000/login`
2. Enter one of the authorized emails from `ADMIN_USER`
3. Enter a password (any password on first login)
4. **First login**: Account is created automatically with your password
5. **Subsequent logins**: Use your created password
6. Access granted!

## 🎯 **Complete Feature Overview**

### 🏠 **Home Page**
- Dashboard with navigation
- Quick links to Add Entry, Analytics, Predictor, and Settings
- User welcome message with formatted name

### ➕ **Add Entry Page**
- Track daily menstrual data with enhanced UI
- **Date**: Auto-formatted display as "15 January 2024"
- **Flow Amount**: 1-10 scale with visual indicators
- **Intensity**: Low/Medium/High selection
- **Symptoms**: Multi-select checkboxes (period, craving, irritation, joint_pain, diarrhea, weird)
- **Period Start**: Mark first day of menstruation
- **Notes**: Optional additional notes
- **Smart Validation**: Prevents duplicate entries

### 📊 **Analytics Dashboard**
- **Interactive Charts**: Flow trends over time (Line chart)
- **Symptom Distribution**: Pie chart (excludes period for accuracy)
- **Cycle History Table**: Previous cycles with start dates and lengths
- **Date Filtering**: View specific time ranges
- **Average Cycle Length**: Calculated from historical data
- **Enhanced Data Visualization**: Improved chart styling and responsiveness

### 🔮 **Cycle Predictor (NEW FEATURE!)**
- **Fertility Timeline**: Custom color-coded cycle visualization
- **Phase Indicators**: Real-time colored badges showing current cycle phase
- **Probability Scores**: Accurate fertility intensity calculations (30%-100%)
- **Data Distinction**: Visual indicators for actual vs calculated data
- **Safe Sex Windows**: Consistent low-fertility ranges for safe periods
- **Interactive Tooltips**: Detailed phase information, dates, and fertility percentages

#### **Cycle Phases & Fertility Ranges:**
- 🔴 **Menstruation** (Days 1-5): Safe sex period (30%-50% fertility)
- 🟡 **Follicular** (Days 6-13): Building phase (40%-80% fertility)
- 🔶 **Ovulation** (around Day 14): Peak fertility (50%-100% fertility)
- 🟢 **Luteal** (Days 15-28): Safe sex period (30%-50% fertility)

#### **Timeline Features:**
- **Color Intensity**: Reflects real-time fertility probability
- **Phase Boundaries**: Clear visual separation between phases
- **Data Accuracy**: Green borders/text for actual data, gray for calculated
- **Smart Calculations**: Based on user's historical cycle data
- **Date Display**: Shows actual dates in "DD Month YYYY" format

### ⚙️ **Settings Page**
- **Change Password**: Update your personal login password
- **View Password**: Shared password for analytics access (fixed: `Mokesh87654321`)
- **Share Link**: Copy link to share analytics read-only view
- **Account Management**: Secure password updates

## 🔐 **Security & Authentication**

1. **Personal Password**: Each user can change their own login password
2. **View Password**: Fixed and shared among all users for analytics access
3. **First Login**: Creates account automatically for authorized emails
4. **Email System**: Completely disabled (no OTP, no verification)
5. **Session Management**: Secure Flask sessions with SECRET_KEY

## 📝 **Complete User Workflow**

```
1. Authorized user logs in with email + password
   ↓
2. If first login → Account created automatically
   If not → Validates existing password
   ↓
3. User lands on Home page
   ↓
4. Can:
   - Add daily entries (with smart date formatting)
   - View comprehensive analytics
   - Use fertility predictor with phase tracking
   - Change password (VIEW_PASS stays same)
   - Share analytics with VIEW_PASS
```

## 🎯 **Share Analytics Feature**

**To share analytics read-only:**

1. Go to Settings
2. Copy the share link: `http://localhost:5000/view-analytics/Mokesh87654321`
3. Send to anyone
4. They can view your analytics and predictor data without logging in

## 🚀 **Enhanced Database Structure**

**Users Collection:**
```json
{
  "email": "user@example.com",
  "password": "hashed_password",
  "view_password": "Mokesh87654321",
  "analytics_access_enabled": true,
  "created_at": "timestamp"
}
```

**Entries Collection:**
```json
{
  "user_id": "user@example.com",
  "date": "2024-01-15",
  "amount": 7,
  "intensity": "medium",
  "symptoms": ["period", "craving", "irritation"],
  "is_period_start": true,
  "notes": "Optional notes",
  "created_at": "timestamp"
}
```

## 🛠️ **Environment Variables**

```env
SECRET_KEY=your_secret_key                    # Flask session key
ADMIN_USER=email1@gmail.com,email2@gmail.com  # Authorized users
VIEW_PASS=Mokesh87654321                      # Shared analytics password
```

## 🎨 **UI/UX Enhancements**

- **Dark/Light Mode**: Automatic theme switching
- **Mobile Responsive**: Optimized for all devices
- **Interactive Elements**: Hover effects and smooth transitions
- **Color Coding**: Intuitive phase and fertility indicators
- **Date Formatting**: User-friendly "DD Month YYYY" display
- **Visual Feedback**: Loading states and success messages
- **Accessibility**: Screen reader friendly design

## 📈 **Advanced Analytics Features**

- **Cycle Length Trends**: Average and historical analysis
- **Symptom Patterns**: Correlation with cycle phases (period excluded)
- **Fertility Windows**: Optimal conception periods
- **Period Regularity**: Cycle consistency tracking
- **Interactive Filtering**: Date range selection
- **Data Export**: Ready for future export features

## 🔧 **Technical Improvements**

- **Custom Timeline**: Replaced Chart.js with optimized timeline visualization
- **Smart Calculations**: Accurate fertility probability based on cycle data
- **Data Distinction**: Clear visual separation of actual vs predicted data
- **Performance**: Optimized JavaScript and CSS for better loading
- **Error Handling**: Comprehensive error messages and validation
- **Security**: Enhanced password hashing and session management

## 📞 **Support & Troubleshooting**

**Common Issues:**

1. **"Access denied. This email is not authorized."**
   - Check `.env` ADMIN_USER list
   - Restart the app after updating `.env`

2. **"Invalid password"**
   - On first login, any password creates account
   - On subsequent logins, use the same password

3. **Analytics not showing**
   - Add entries first on the "Add Entry" page
   - Navigate to Analytics to view charts

4. **Predictor not working**
   - Ensure you have at least one complete cycle entered
   - Check that period start dates are marked correctly

5. **Date formatting issues**
   - Dates are stored as YYYY-MM-DD but displayed as "DD Month YYYY"
   - This is normal behavior

---

**🎉 Complete menstrual health tracking solution with advanced fertility prediction!**
  "amount": 7,
  "intensity": "medium",
  "symptoms": ["period", "craving"],
  "is_period_start": true,
  "created_at": "timestamp"
}
```

### 🛠️ **Environment Variables**

```env
SECRET_KEY=your_secret_key                    # Flask session key
ADMIN_USER=email1@gmail.com,email2@gmail.com  # Authorized users
VIEW_PASS=Mokesh87654321                      # Shared analytics password
```

### 📞 **Support**

**Common Issues:**

1. **"Access denied. This email is not authorized."**
   - Check .env ADMIN_USER list
   - Restart the app after updating .env

2. **"Invalid password"**
   - On first login, any password creates account
   - On subsequent logins, use the same password

3. **Analytics not showing**
   - Add entries first on the "Add Entry" page
   - Navigate to Analytics to view charts

---

**Ready to use!** 🚀