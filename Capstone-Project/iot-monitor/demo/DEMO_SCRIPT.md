# Demo script (about 7 minutes)

## Before recording
1. Start the stack: `docker compose --profile demo up --build` (or the no-Docker steps in the README plus `python scripts/simulate.py --interval 5`).
2. Sign in once as `user@example.com` / `User@12345` so the dashboard has live data; wait about a minute.
3. Browser window at 1280 px wide; close other tabs; zoom 100%.
4. Open MailHog (http://localhost:8025) in a second tab (Docker only).

## Script

| Time | Do | Say |
|---|---|---|
| 0:00 | Show the login page | "IoT Monitor lets a factory watch hundreds of sensors in one place. It has a REST API and this web app." |
| 0:30 | Click *Sign up*, type a weak password, then a strong one | "The checklist mirrors the server's rules, and the server checks again." |
| 1:00 | Submit, switch to MailHog, open the email, click the link | "Accounts start inactive. The signed link activates them." |
| 1:30 | Log in with *Remember me* | "Sessions use short-lived tokens that refresh automatically." |
| 2:00 | **Dashboard:** point at the cards, hover the chart, point at the red threshold line | "Live data every five seconds. The band is min to max; red marks thresholds." |
| 2:45 | Change period to *Last 7 days*, then pick another sensor; click *Pause live updates*; *Export CSV* | "Presets stay live; custom ranges are fixed." |
| 3:30 | **Sensors:** search, filter by *Faulty*, sort by priority; open a sensor, add a reading | "Search, filters and paging run on the server." |
| 4:15 | *+ New sensor*: submit empty (show errors), then fill thresholds and save | "Client and server validation. Thresholds feed the dashboard and alerts." |
| 4:45 | **Reports:** create a PDF *Alerts* report, wait for *ready*, download and open it | "Built in the background; PDF or CSV; summary, detailed or alerts." |
| 5:30 | Tick *Repeat automatically*, choose *daily*, create | "Schedules run automatically and can email the owner." |
| 6:00 | Log out, log in as `guest@example.com` | "Guests are read-only; the API enforces it, the UI just hides buttons." |
| 6:30 | Log in as admin: *Users* (change a role), *Audit log* | "Admins manage users; every action is audited." |
| 7:00 | Show `/docs` (Swagger) and say where tests and docs are | "Fully documented API, 38 endpoints, with automated tests and a Postman collection." |

## Tips
- Keep the cursor still when pointing at something.
- If a step fails, stop, fix it and re-record that part only.
