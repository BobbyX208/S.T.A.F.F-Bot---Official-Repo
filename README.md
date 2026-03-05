# 🤖 S.T.A.F.F. Bot
> **The Self-Updating Discord Staff Ecosystem**

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![discord.py](https://img.shields.io/badge/discord.py-2.3+-green.svg)
![Status](https://img.shields.io/badge/Status-Phase%201%20Complete-success.svg)
![Auto-Update](https://img.shields.io/badge/Auto--Update-GitHub-purple.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![PRs](https://img.shields.io/badge/PRs-Welcome-orange.svg)

---

## 🎯 The Vision

Most Discord servers run on duct tape and prayers. Staff bots are either:
- **Too simple** (just moderation commands)
- **Too complex** (enterprise tools that need a PhD to configure)
- **Brittle** (every update requires a restart)

**S.T.A.F.F. Bot** is built from the ground up as a complete staff ecosystem that focuses on **UI-first interactions**, **Staff Accountability**, and **Zero-Downtime Deployment**.

| What | How |
|------|-----|
| 🔄 **Updates Itself** | Push code to GitHub → bot pulls & reloads modules instantly |
| 🎫 **Smart Tickets** | Data-driven modals and select menus per category |
| 📊 **Staff Metrics** | Automated clock-in/out and activity tracking |
| 📢 **High-Fidelity Broadcasts** | Markdown-preserving announcements with preview workflows |
| 🛡️ **Auto-Mod** | Raid shield and button-based quick actions |

---

## 🏗️ Project Architecture

S.T.A.F.F. Bot uses a **Modular Cog Architecture**. Each feature is a standalone plugin that can be hot-reloaded without taking the entire bot offline.

```

S.T.A.F.F-Bot/
├── main.py                      # Entry point + auto-update core
├── database.py                   # Multi-db handler (PostgreSQL/MySQL/JSON)
├── config.json                    # Global UI & Logic settings
├── .env                           # Secrets (gitignored)
├── logs/                          # Rotating log files
├── cogs/
│   ├── git_manager.py             # GitHub Auto-pull logic (Phase 1) ✅
│   ├── tickets.py                  # Multi-category ticket system (Phase 2) 🔨
│   ├── staff_management.py         # Clock-in/out, leaderboards (Phase 3) ⏸️
│   ├── broadcaster.py              # High-fidelity announcements (Phase 4) ⏸️
│   ├── welcomer.py                  # Verification + UI onboarding (Phase 5) ⏸️
│   ├── automod.py                   # Smart moderation (Phase 6) ⏸️
│   └── admin_panel.py                # Live dashboard + hot-config (Phase 7) ⏸️
├── utils/
│   ├── logger.py                     # Production logging
│   ├── ui_factory.py                  # Reusable Button/Modal templates
│   ├── transcripts.py                  # HTML/Markdown log generator
│   └── embeds.py                        # Template system for broadcasts
└── data/                               # JSON storage (if DB_TYPE=json)

```

---

## ✨ The Complete Roadmap

| Phase | Feature | Status | Description |
|-------|---------|--------|-------------|
| **1** | **Foundation** | ✅ **COMPLETE** | Git Core, Cog Architecture, Hot-Reloading, Multi-DB, Production Hardening |
| **2** | **Smart Tickets** | 🔨 **IN PROGRESS** | Modals, Select Menus, Claim System, Transcripts, Add Member |
| **3** | **Staff Management** | ⏸️ **PLANNED** | Clock-in/out, Activity leaderboards, Performance metrics |
| **4** | **Broadcasting** | ⏸️ **PLANNED** | Draft workflows, Markdown preservation, Scheduled announcements |
| **5** | **Interactive Welcomer** | ⏸️ **PLANNED** | Verification gates, UI-based onboarding, Role buttons |
| **6** | **Auto-Moderation** | ⏸️ **PLANNED** | Raid shield, Smart detection, Button-based quick actions |
| **7** | **Command & Control** | ⏸️ **PLANNED** | Live dashboard, Hot-config, Cog manager |

---

## 🚀 Key Feature Breakdown

### 🟢 **Phase 1: Foundation (COMPLETE)**
*The engine that makes everything else possible*

| Feature | Description |
|---------|-------------|
| ✅ **Self-Updating Git Core** | Push to GitHub → bot pulls & reloads itself |
| ✅ **Modular Cog Architecture** | Features as plugins, isolated failures |
| ✅ **Multi-Database Support** | PostgreSQL, MySQL, or JSON (configurable) |
| ✅ **Production Hardening** | Survives broken code, network failures |
| ✅ **Staff Commands** | `!sync`, `!gitstatus`, `!reload` |
| ✅ **Pterodactyl Ready** | Works in shared hosting, persistent storage |
| ✅ **Fetch Timeout** | 30s network guard, no hanging |
| ✅ **Large Diff Protection** | Limits reload storm to 50 files |
| ✅ **Commit Comparison** | Only pulls when changes exist |
| ✅ **Broken Code Survival** | One bad cog won't crash the bot |
| ✅ **Sync Locking** | No overlapping updates |
| ✅ **Local Change Warning** | Alerts if files modified manually |

---

### 🟡 **Phase 2: Advanced Ticket System (IN PROGRESS)**
*The reason most servers need a staff bot*

#### 🎫 **Multi-Category Support**
Dynamic Select Menus populated from `config.json`:
- General Support
- Billing/Purchase
- Report a Player
- Staff Application

#### 📝 **Smart Modals**
Each category triggers a different form:
- **Purchase** → asks for Transaction ID
- **Report** → asks for User ID + Evidence
- **Application** → asks for Experience + Availability

#### 👋 **Claim System**
- "Claim" button renames channel to `claimed-username`
- Pings the staff member who took it
- Prevents duplicate responses

#### 📄 **Automated Transcripts**
- HTML/Markdown file generated on close
- DMed to the user for their records
- Logged in private archive channel

#### 👥 **One-Click "Add Member"**
- Button opens modal to add friend/witness
- Instantly updates channel permissions
- No more manual role assignments

#### ⏰ **Unclaimed Pings**
- If ticket sits unclaimed >10 minutes
- Pings higher-up role automatically

---

### 🟡 **Phase 3: Staff Management (PLANNED)**
*Running a staff team is a business - treat it like one*

| Feature | Description |
|---------|-------------|
| ⏱️ **Clock-In/Out System** | UI panel to start/end shifts, tracks total hours |
| 📊 **Staff Leaderboard** | Shows who closed most tickets, sent most messages |
| 📈 **Activity Reports** | Weekly summaries of staff performance |
| 🏆 **Achievement Badges** | Visual recognition for top performers |

---

### 🟡 **Phase 4: High-Fidelity Broadcasting (PLANNED)**
*Announcements that don't look like garbage*

| Feature | Description |
|---------|-------------|
| 📝 **Draft System** | Create announcements, save for admin approval |
| 📅 **Scheduled Broadcasts** | Pick date/time, bot sends automatically |
| 🎨 **Embed Templates** | Configurable styles (Warning/Info/Success) in `config.json` |
| 👁️ **Preview Mode** | See exactly how it looks before sending |
| 🎯 **Targeted Delivery** | Send to specific channels or roles |

---

### 🟡 **Phase 5: Interactive Welcomer (PLANNED)**
*First impressions matter*

| Feature | Description |
|---------|-------------|
| 🎭 **Welcome UI** | Embed with buttons: [Read Rules], [Get Roles], [Help Desk] |
| ✅ **Verification Gate** | Modal with simple question to block bots |
| 🖼️ **Image Generation** | Optional welcome cards with member count |
| 🔄 **Role Buttons** | Self-serve role assignment |

---

### 🔴 **Phase 6: Automated Moderation (PLANNED)**
*Safety without the noise*

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Auto-Mod** | Detects banned words, sends staff alert with action buttons |
| 🛡️ **Raid Shield** | Panic button that locks server instantly |
| ⚡ **Quick Actions** | Buttons for [Timeout], [Delete], [Dismiss] right in the alert |
| 📊 **Raid Detection** | Auto-triggers if multiple joins in short time |

---

### 🟣 **Phase 7: Command & Control (PLANNED)**
*Because editing JSON files is so 2020*

| Feature | Description |
|---------|-------------|
| 📊 **Live Dashboard** | `/admin-panel` shows cogs loaded, latency, git status |
| ⚙️ **Hot-Config** | Change settings via Discord modals (no file editing) |
| 🔄 **Cog Manager** | Enable/disable features on the fly |
| 📈 **Analytics** | See bot usage stats |

---

## 🚦 Quick Start

### Prerequisites
- Python 3.10+
- Git
- Discord Bot Token ([Guide](https://discordpy.readthedocs.io/en/stable/discord.html))
- GitHub repository (public or private)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/BobbyX208/S.T.A.F.F-Bot---Official-Repo.git
cd S.T.A.F.F-Bot---Official-Repo

# 2. Run setup (handles venv, dependencies, config)
chmod +x setup.sh
./setup.sh

# 3. Configure environment
nano .env  # Add your Discord token and GitHub repo
```

Environment Variables (.env)

```env
# Required
DISCORD_TOKEN=your_discord_bot_token
GITHUB_REPO=BobbyX208/S.T.A.F.F-Bot---Official-Repo  # or full HTTPS URL

# Optional
GITHUB_BRANCH=main                        # default: main
ENABLE_GIT_SYNC=true                       # default: false
GITHUB_POLL_INTERVAL=60                     # seconds, default: 60
DB_TYPE=json                               # postgresql, mysql, or json
```

First-Time Git Setup

```bash
# Verify remote is configured
git remote -v
# Should show origin pointing to your GitHub repo

# If not, add it:
git remote add origin https://github.com/BobbyX208/S.T.A.F.F-Bot---Official-Repo.git
git fetch origin
```

Start the Bot

```bash
python main.py
```

---

**🧪 Testing the Auto-Update**

S.T.A.F.F. Bot monitors your GitHub branch. To update the production bot:

```bash
# 1. Make a change in /cogs
echo 'print("Auto-update works!")' >> cogs/test.py

# 2. Commit and push
git add cogs/test.py
git commit -m "Test auto-update"
git push origin main

# 3. Watch your bot logs - it will appear automatically
# 15:30:00 | 🔍 Checking for updates...
# 15:30:01 | 📥 Changes detected
# 15:30:02 | ✅ Loaded new: cogs.test
```

---

**🛠️ Staff Commands**

Command Description Permission
!sync Manual git sync trigger Administrator
!gitstatus Show commit status, branch, local changes Administrator
!reload [cog] Reload specific or all cogs Administrator

---

**🏭 Production Deployment (Pterodactyl)**

1. Create a new Pterodactyl egg using Python 3.10+
2. Set working directory to /home/container
3. Clone your repo manually first time:
   ```bash
   git clone https://github.com/BobbyX208/S.T.A.F.F-Bot---Official-Repo.git .
   ```
4. Set environment variables in Pterodactyl startup tab
5. Ensure persistent storage is enabled (.git folder must persist)
6. Start the bot - it will auto-update from GitHub

---

**🔒 Security Notes**

· .env is in .gitignore - never commit secrets to your repository
· Bot only pulls from GitHub, never pushes changes upstream
· All sync operations use git reset --hard - production mirrors remote exactly
· Local changes on production are warned and overwritten during sync
· Commands are restricted to users with Administrator permission
· Database credentials are stored in .env, never in code
· GitHub token (if used) has minimum required permissions (only read access needed)
· No user data is ever sent to GitHub - sync is code-only
· Rate limiting protects against abuse
· All operations are logged for audit trails

---

**📊 Current Status (March 2026)**

Phase Feature Status Completion ETA
1. Foundation ✅ COMPLETE 100% DONE
2. Smart Tickets 🔨 IN PROGRESS
3. Staff Management ⏸️ PLANNED
4. Broadcasting ⏸️ PLANNED
5. Interactive Welcomer ⏸️ PLANNED
6. Auto-Moderation ⏸️ PLANNED
7. Command & Control ⏸️ PLANNED

What Works Right Now (Phase 1)

· ✅ Auto-updating git core - push code, bot updates
· ✅ Git status commands - !gitstatus, !sync
· ✅ Cog reloading - !reload
· ✅ Production logging with rotation
· ✅ Multi-database support (PostgreSQL/MySQL/JSON)
· ✅ Network timeout protection (30s)
· ✅ Broken code survival - one bad cog won't crash bot
· ✅ Pterodactyl compatibility
· ✅ Cross-platform paths (Windows/Linux)

What's Coming Next (Phase 2)

· 🔄 Category-based ticket system
· 🔄 Smart modals per ticket type
· 🔄 Claim system with channel renaming
· 🔄 HTML transcript generation
· 🔄 "Add Member" functionality
· 🔄 Unclaimed ticket alerts

---

**📈 Performance Metrics**

Metric Value
CPU impact <1% per sync check
Memory baseline ~50MB
Network per check ~10KB
Reload time per cog <1s
Max files processed 50 per sync
Fetch timeout 30s
Poll interval Configurable (default 60s)

---

**🤝 Contributing**

This is a living project. Each phase builds on the last.

1. Pick a Phase from the roadmap
2. Build the Cog locally following our patterns
3. Test thoroughly
4. Submit a PR
5. Watch the production bot live-update upon merge

**Contribution Guidelines**

· Follow the existing code structure
· Use cog_unload() for clean task management
· Keep cogs lightweight, move heavy logic to /utils
· Add comprehensive logging
· Update this README if adding features
· Include docstrings for all methods
· Test with both PostgreSQL and JSON backends

---

**🙏 Acknowledgments**

Built with:

· discord.py - The best Discord library
· GitPython - Git integration
· Pterodactyl Panel - Game panel hosting
· asyncpg - PostgreSQL driver
· aiomysql - MySQL driver

---

## 📝 License

MIT License - feel free to use, modify, and distribute.

Copyright (c) 2026 S.T.A.F.F. Bot Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

---

**🎯 The Bottom Line**

This bot doesn't need you to restart it. Push code, and it just works. That's the entire point.

```bash
# Local machine
git add .
git commit -m "New ticket feature"
git push origin main

# Production bot (automatically)
# - Detects change
# - Pulls update
# - Reloads new code
# - Keeps running
```

Zero downtime. Zero manual intervention. Just works. 🚀

---

<div align="center">

⭐ Star this repo if you want a bot that actually works

Found a bug? Report it here
Want a feature? Request it here
Have questions? Start a discussion

---

Built with ❤️ for Discord staff teams everywhere

</div>
