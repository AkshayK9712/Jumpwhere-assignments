# IoT Monitor: user manual

## 1. Getting started

**Create an account.** Open the app, choose *Sign up*, enter your name, email and a password with at least 8 characters including an uppercase letter, a lowercase letter, a digit and a symbol (the checklist turns green as you type). We email you a link; open it to activate your account, then log in.
Did not get the email? On the login page use *Resend verification email*.

**Log in.** Tick *Remember me on this device* to stay signed in after closing the browser. Use *Log out* in the top menu on shared computers.

**Roles**

| Role | Can do |
|---|---|
| Admin | Everything, including managing users and viewing the audit log |
| User | Create and manage their own sensors, readings and reports |
| Guest | View sensors, the dashboard and reports; cannot change anything |

## 2. Dashboard

The first page after login.

- **Cards** show how many sensors are active, faulty and so on, and how many readings arrived in the chosen period.
- **Readings over time** charts one sensor: the line is the average, the shaded band is min to max, red dashed lines are the sensor's thresholds, and red dots are periods that crossed them. Hover or touch the chart for exact values.
- **Sensor / Period / Category** change what you see. *Custom range* lets you pick exact start and end times.
- **Live updates:** for ranges like "Last hour" the page refreshes every 5 seconds. Use *Pause live updates* to freeze it. It also pauses while the browser tab is hidden.
- **Export CSV** downloads the chart data. *View chart data as a table* shows the same numbers as a table.

## 3. Sensors

*Sensors* lists everything you may see. Search by title or description, filter by status, category and priority, and sort. Rows can be selected for *Delete selected*.

**Add or edit a sensor:** *+ New sensor*. Fill in the title and category; factory, location, unit and thresholds are optional. Thresholds (minimum and maximum) drive the red lines on the dashboard and the alerts report.
If someone else saved the same sensor while you were editing, you will see a message and can reload the latest version instead of overwriting their work.

**Sensor page:** shows the details and the latest readings. Add a reading by entering a value (and optionally a time).

## 4. Reports

*Reports > New report*.

| Choice | Meaning |
|---|---|
| Format | PDF for reading and printing, CSV for spreadsheets |
| Contents | **Summary**: one row per sensor (min, average, max, alerts). **Detailed**: summary plus every reading. **Alerts**: only readings outside thresholds |
| Sensors / Category | Leave empty for all your sensors |
| Period | Last 24 hours, 7 days, 30 days, or a custom range |
| Repeat automatically | Creates a schedule (daily, weekly or every 30 days). Each run covers the matching period, and you can be emailed when it is ready |

Reports are built in the background; the status changes from *pending* to *ready*, then use *Download*. Files are removed after 30 days. *Stop* on a schedule ends future runs but keeps reports already made.

## 5. Profile

*Your name in the top menu* opens your profile: change your name, avatar link, phone, timezone, language and bio. Guests see their details but cannot edit them.

## 6. For administrators

- **Users:** search, filter by role or status, change a role, disable or enable an account, or delete it. You cannot change or delete your own account here. Disabling a user signs them out immediately.
- **Audit log:** every sign-in, sensor change, report and admin action, with who, when and from which address. Filter by action, entity or user id.

## 7. Troubleshooting

| Problem | What to do |
|---|---|
| "Email not verified" when logging in | Open the link in your email, or request a new one |
| Signed out unexpectedly | Your session ended; log in again |
| "Too many requests" | Wait a minute and retry |
| Charts missing but numbers show | The chart library could not load; check your internet connection and refresh |
| A report stays *pending* | Wait a few seconds; if it turns *failed*, try a shorter period |
| Cannot see a button | Your role may not allow that action |
