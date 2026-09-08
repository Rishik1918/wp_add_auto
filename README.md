# WhatsApp One-Time Link Gateway

A self-hosted, anti-forwarding invite redirection gateway. Each member receives a unique one-time URL. The moment someone clicks it, the token expires permanently—preventing anyone from forwarding the link to outsiders.

---

## 📁 Files Included

- `run.bat` — **1-Click launcher** for Windows (installs Flask & launches server).
- `app.py` — The core Flask web server & SQLite database controller.
- `generate_links.py` — CLI generator to instantly produce 350 links into a CSV.
- `config.json` — Configuration for your WhatsApp Group Link & Base URL.
- `templates/` — Clean web interfaces (Admin Dashboard, Redirect screen, Expired screen, Invalid screen).

---

## 🚀 How to Run (Step-by-Step)

### Step 1: Start the Gateway Server
Simply **double-click** `run.bat` on your Desktop.  
Or from PowerShell / Command Prompt:
```powershell
cd C:\Users\rishi\Desktop\WhatsApp_OneTime_Gateway
pip install -r requirements.txt
python app.py
```

You will see:
```text
=======================================================
 WhatsApp One-Time Link Gateway is starting...
 Access the Admin Dashboard at: http://localhost:5000/admin
=======================================================
```

---

### Step 2: Open the Admin Dashboard
1. Open your browser and navigate to: **`http://localhost:5000/admin`**
2. In the **Gateway Configuration** box:
   - Paste your real **WhatsApp Group Invite Link** (e.g., `https://chat.whatsapp.com/L1abc...`).
   - Click **Save Settings**.
3. In the **Generate One-Time Links** box:
   - Enter **350** (or paste your recipients' names/emails).
   - Click **Generate Links Now**.
4. Click **Export All to CSV** to download `whatsapp_onetime_links.csv` ready for Excel / Google Sheets!

---

## 🌐 Making It Accessible Over the Internet (100% Free)

Because recipients are outside your home Wi-Fi, they need an internet address to click the links. You can get a free HTTPS domain in 10 seconds:

### Option A: Free Cloudflare Tunnel (No Account Required)
1. Download `cloudflared` from Cloudflare or via PowerShell:
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. Run this command while `app.py` is running:
   ```powershell
   cloudflared tunnel --url http://localhost:5000
   ```
3. Cloudflare will give you a public URL like:
   `https://random-words.trycloudflare.com`
4. Go to `http://localhost:5000/admin`, change **Base Server URL** to your Cloudflare URL, and click **Save Settings**!

### Option B: Free ngrok
1. Run:
   ```powershell
   ngrok http 5000
   ```
2. Paste the provided `https://xxxx.ngrok-free.app` into the Admin Dashboard as your Base URL.

---

## 🛡️ Why This Protects You From WhatsApp Bans

1. **Zero Bot Activity on WhatsApp:** You aren't using an unofficial WhatsApp Web bot to message 350 numbers. Meta's anti-spam engine only checks WhatsApp-to-WhatsApp messaging.
2. **Safe Delivery:** You can send these 350 unique links via **Email (Mail Merge)**, **College / Work Portal**, or **SMS**.
3. **Strict Single-Use:** The moment Member A clicks their unique link, the database marks it `is_used = 1`. If Member A forwards the link to Member B, Member B will see:
   > *"🚫 Link Already Used: This one-time WhatsApp invitation link has already been redeemed."*
