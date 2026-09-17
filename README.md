# WhatsApp One-Time Link Gateway

A secure, anti-forwarding invitation redirection service designed to protect private WhatsApp groups from unauthorized access, link leakage, and mass forwarding.

Each recipient is issued a unique, single-use URL. The gateway enforces cryptographic device-binding, automated crawler filtering, and a 15-minute single-device grace window to ensure legitimate recipients can reliably join while completely preventing forwarded links from functioning.

---

## Architecture and Core Security Logic

### 1. Automated Link-Preview and Crawler Filtering
When URLs are shared in messaging apps (such as WhatsApp, Telegram, or iMessage), background crawlers and web preview generators immediately send HTTP GET requests to retrieve OpenGraph metadata (title, description, and thumbnail). 

- Traditional single-use systems fail because the preview crawler consumes the link before the user opens it.
- This gateway inspects incoming user agents (e.g., `WhatsApp`, `facebookexternalhit`, `Twitterbot`, `TelegramBot`, `Applebot`, `Googlebot`) and prefetch headers (`Purpose: prefetch`, `Sec-Purpose: prefetch`, `X-Purpose: preview`).
- When a crawler or prefetch request is detected, the gateway returns the preview metadata without modifying the token state in the database. The token remains completely active and unconsumed.

### 2. Device-Bound 15-Minute Grace Window
To prevent legitimate users from being locked out due to network drops, app switching, or page reloads, the gateway implements a strict device-bound grace period:

- **Initial Access:** When a human recipient opens their unique link for the first time, the gateway marks the token as used (`is_used = 1`), records the client IP address and timestamp, generates a cryptographically secure device identifier, and sets an `HttpOnly` cookie (`dev_token_<token>`) with a 15-minute lifespan (900 seconds).
- **Same-Device Reloads:** If the original recipient refreshes the browser, taps the back button, or switches between the browser and WhatsApp within 15 minutes, the gateway validates the device cookie against the database record and allows them to proceed to the group invite.
- **Expiration:** Once 15 minutes elapse from the initial click, the token expires permanently, and any subsequent visits return HTTP 410 (Gone).

### 3. Shared Network and Hotspot Isolation (Anti-Forwarding)
In environments such as college campuses, dormitories, offices, or shared mobile hotspots, multiple devices share the same public IP address (NAT - Network Address Translation). 

- An IP-only restriction would allow a recipient to forward the link to someone on the same Wi-Fi network.
- The gateway's cookie-based device lock ensures that only the specific device and browser session that originally claimed the link can reuse it during the 15-minute window.
- If Recipient A forwards the link to Recipient B on the exact same Wi-Fi network, Recipient B's device will lack Recipient A's browser cookie. The server detects the missing or mismatched device token and immediately blocks Recipient B with HTTP 410 ("Link Already Used").

---

## System Workflow

```
[ WhatsApp / Email / SMS ]
           │
           ▼
[ Recipient Clicks Token Link: /join/<token> ]
           │
           ├─► Is Crawler / Prefetch?
           │         ├─► YES: Serve Preview HTML (Do NOT mark as used)
           │         └─► NO:  Continue to Device Verification
           │
           ├─► Is Token Unused (is_used = 0)?
           │         └─► YES: 
           │               1. Mark is_used = 1
           │               2. Generate Secret Device ID
           │               3. Store in DB (IP, Timestamp, Device ID)
           │               4. Set HttpOnly Cookie (dev_token_<token>)
           │               5. Redirect to WhatsApp Group
           │
           └─► Is Token Already Used (is_used = 1)?
                     ├─► Does Request have matching Device Cookie AND Elapsed Time < 15 mins?
                     │         ├─► YES: Allow Same Device to Redirect / Join
                     │         └─► NO:  Reject with HTTP 410 (Link Expired / Already Used)
```

---

## Project Structure

```
WhatsApp_OneTime_Gateway/
│
├── app.py                  # Main Flask application and SQLite database controller
├── config.json             # Runtime configuration (WhatsApp link, base URL, admin password)
├── requirements.txt        # Python dependency declarations
├── run.bat                 # Windows quick-launch script
├── invites.db              # SQLite database (contains invites and persistent settings)
│
└── templates/
    ├── admin.html          # Protected administrative dashboard
    ├── login.html          # Administrator login portal
    ├── reset_password.html # Master key password reset interface
    ├── redirect.html       # Automatic redirect screen with direct join fallback
    ├── expired.html        # HTTP 410 error screen (Link Already Used)
    ├── invalid.html        # HTTP 404 error screen (Invalid Token)
    └── index.html          # Public landing fallback page
```

---

## Database Schema

The gateway uses SQLite with the following structure:

### `invites` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER PRIMARY KEY` | Auto-incrementing identifier |
| `token` | `TEXT UNIQUE NOT NULL`| URL-safe random token identifying the invitation |
| `assigned_to` | `TEXT` | Name, roll number, or label of the recipient |
| `is_used` | `INTEGER DEFAULT 0` | State flag: `0` for Active, `1` for Used |
| `used_at` | `TEXT` | Timestamp of initial human access (`YYYY-MM-DD HH:MM:SS`) |
| `ip_address` | `TEXT` | Public IP address of the claiming device |
| `device_id` | `TEXT` | Cryptographic hex token bound to the claiming browser |
| `created_at` | `TEXT` | Timestamp when the token was generated |

### `settings` Table
| Column | Type | Description |
| :--- | :--- | :--- |
| `key` | `TEXT PRIMARY KEY` | Configuration key (e.g., `whatsapp_group_link`, `admin_password`) |
| `value` | `TEXT` | Stored configuration value |

---

## Installation and Local Setup

### Prerequisites
- Python 3.9 or higher
- `pip` package manager

### Setup Steps
1. Navigate to the project directory:
   ```bash
   cd WhatsApp_OneTime_Gateway
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the application:
   ```bash
   python app.py
   ```
   Or on Windows, double-click `run.bat`.

4. The server starts locally at `http://localhost:5000`.

---

## Administration Guide

### Accessing the Dashboard
- URL: `http://localhost:5000/admin` (or `https://<your-domain>/admin`)
- Default Password: `admin` (or the value set in `ADMIN_PASSWORD` environment variable)

### Configuration Management
From the admin panel:
- **WhatsApp Group Link:** Set your official WhatsApp group invite URL (e.g., `https://chat.whatsapp.com/JvimDEP8FrQHOlicdDCEXX`).
- **Base Server URL:** Set the publicly accessible domain (e.g., `https://wp-add-auto.onrender.com`). All exported links will use this domain.
- **Admin Password:** Update the dashboard password at any time.

### Generating Links
- Specify the number of links required (e.g., 350) or paste a list of recipient names.
- Click **Generate Links Now** to insert fresh, active tokens into the database.

### Exporting Links
- Click **Export All to CSV** to download `whatsapp_onetime_links.csv`.
- The CSV file contains: `ID`, `Assigned To`, `One-Time Link`, `Status`, `Redeemed At`, `IP Address`, and `Created At`.

### Maintenance Operations
- **Clear Used Links:** Removes redeemed/expired records while retaining active ones.
- **Delete All Links:** Purges all existing tokens for a fresh rollout.

---

## Production Deployment

### Hosting on Render (Cloud Platform)
1. Push the repository to GitHub.
2. Link the repository to a new Web Service on Render.
3. Configure build and runtime settings:
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Set Environment Variables in the Render dashboard:
   - `ADMIN_PASSWORD` = `<your-secure-password>`
   - `BASE_URL` = `https://<your-service>.onrender.com`

### Reverse Proxy and SSL
When deployed behind Cloudflare or a reverse proxy:
- The gateway reads `CF-Connecting-IP` and `X-Forwarded-For` headers to accurately log the client's public IP address.
- HTTPS is mandatory in production to ensure `HttpOnly` and `SameSite` cookie security.

---

## Client Integration Files

- **`ace.html`**: Production dispatcher interface mapping 227 individual students to 24 team member profiles. Features direct WhatsApp integration, one-click message copy with full Unicode fidelity, real-time search, and local verification checkboxes.
- **`test_ace.html`**: Isolated testing interface utilizing spare links to verify delivery and client-side behavior without consuming production tokens.
- **`unused_spare_links.csv`**: Record of reserve tokens available for operational testing.
