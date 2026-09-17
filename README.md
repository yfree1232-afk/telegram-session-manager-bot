# ⚡ Telegram Session Manager Bot (SessionManagerVoltxbot)

An advanced, high-aesthetic All-in-One Telegram Session Generator, Active Devices Inspector, and Multi-Account Security Suite.

---

## 🌟 Features

- **⚡ Dual Session Generator:**
  - Generates both **Pyrogram v2** and **Telethon** string sessions.
  - Interactive, step-by-step Telegram bot wizard.
  - Safe OTP entry & Two-Step Verification (2FA) password handling.
  - Sensitive messages (OTP & passwords) are automatically deleted from chat history upon reading.

- **📱 Active Devices & Security Inspector:**
  - View all connected devices, device models, OS, app version, IP addresses, country, and login timestamps.
  - **🚨 Terminate All Other Sessions** with a single click.

- **💼 Encrypted Account Vault:**
  - Store multiple sessions safely in local SQLite database using **AES-Fernet** encryption.
  - Run 1-click **Alive / Dead** status checks on all accounts.
  - Export backup file of all saved sessions.

- **🛠 Account Utilities:**
  - **Leave All Chats:** Leave all spam/joined channels and groups at once.
  - **Quick Health Check:** Paste any string session to verify if it is alive or banned.

- **👑 Admin Panel:**
  - Bot user statistics (`/stats`).
  - Broadcast message to all bot users.

---

## 🚀 Heroku Deployment Guide

### Option 1: Deploy via Heroku CLI (Fastest)

1. **Install Heroku CLI and Login:**
   ```bash
   heroku login
   ```

2. **Clone / Open your project directory:**
   ```bash
   cd telegram-session-manager
   git init
   git add .
   git commit -m "Initial commit - Session Manager Bot"
   ```

3. **Create Heroku App:**
   ```bash
   heroku create your-session-bot-name
   ```

4. **Set Environment Variables in Heroku:**
   ```bash
   heroku config:set BOT_TOKEN="8973572372:AAFD7hLJ2cPdlOCmcta08m4WkSsISOac-sc"
   heroku config:set API_ID="2040"
   heroku config:set API_HASH="b18441a1ff607e10a989891a5462e627"
   heroku config:set OWNER_ID="YOUR_TELEGRAM_USER_ID"
   ```

5. **Deploy Code:**
   ```bash
   git push heroku master
   ```

6. **Start the Worker Dyno:**
   ```bash
   heroku ps:scale worker=1
   ```

7. **View Logs:**
   ```bash
   heroku logs --tail
   ```

---

### Option 2: Deploy via GitHub & Heroku Dashboard

1. Push this folder to a GitHub repository (Public or Private).
2. Go to [Heroku Dashboard](https://dashboard.heroku.com/apps).
3. Click **New** -> **Create new app**.
4. In the **Deploy** tab, select **GitHub** and connect your repository.
5. In the **Settings** tab, click **Reveal Config Vars** and add:
   - `BOT_TOKEN`: `8973572372:AAFD7hLJ2cPdlOCmcta08m4WkSsISOac-sc`
   - `API_ID`: `2040` (or your own from my.telegram.org)
   - `API_HASH`: `b18441a1ff607e10a989891a5462e627`
   - `OWNER_ID`: Your Telegram numeric User ID
6. Go to **Resources** tab, make sure the **worker** dyno is turned ON.

---

## 💻 Local Testing & Running

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Bot:**
   ```bash
   python main.py
   ```
