# 🚀 Telegram Multi-Session Manager & Channel Multi-Tool Bot

An ultra-secure, asynchronous Python bot powered by **Aiogram 3.x**, **Telethon MTProto**, and **MongoDB Atlas** for managing multiple Telegram accounts, bulk channel joining, ZIP session batch imports, post emoji reactions, forwarding, and official Telegram moderation reporting.

---

## 🌟 Key Features

1. **📦 ZIP & File Batch Session Import:**
   - Import multiple Telethon `.session` files directly from `.zip` archives.
   - 1-Click single `.session` file and `.txt` string session batch import.

2. **📢 Bulk Channel Joiner (Public & Private):**
   - Joins `@username`, `https://t.me/channel`, and private invite links `https://t.me/+hash` across all connected sessions.
   - Anti-Ban staggering & duplicate participant detection.

3. **🎯 Channel Post Multi-Tool:**
   - **Emoji Reactions:** 12 quick-tap emojis + custom emoji reactions.
   - **Post Forwarding:** Forward messages across accounts to channels/groups/Saved Messages.
   - **Official Moderation Reporting:** File Spam, Fake, Violence, Copyright, Pornography, and Child Abuse reports.
   - **Text & Link Copy:** 1-Click Markdown code block copy.
   - **Discussion Comments:** Send replies & comments from all active accounts.

4. **🛡️ Ultra-Secure Database:**
   - Direct persistence to **MongoDB Atlas Cloud**.

---

## 🚀 Heroku Deployment

1. Add Buildpack: `heroku/python`
2. Set Config Vars:
   - `BOT_TOKEN`
   - `API_ID`
   - `API_HASH`
   - `MONGO_URI`
   - `DATABASE_NAME`
3. Turn on the `worker` Dyno in Resources.
