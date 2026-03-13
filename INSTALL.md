# JobPulse — Install and run (no terminal needed)

This guide is for **non-technical users** who downloaded the **.exe (Windows)** or **.dmg (Mac)** and want to install and run JobPulse without using the terminal.

---

## Windows (.exe)

### 1. Download

- Get **JobPulse-win64.zip** from the [latest release](https://github.com/SaeedAhmadMalakzai/JobPulse/releases) (or the folder **JobPulse** if it’s not zipped).

### 2. Install

- Unzip **JobPulse-win64.zip** to a folder, e.g. `C:\Users\YourName\JobPulse`.
- You’ll see a folder **JobPulse** with `JobPulse.exe` and other files inside.

### 3. First-time setup (.env)

- In the same folder as `JobPulse.exe`, find **.env.example**.
- Copy it and rename the copy to **.env**.
- Open **.env** in Notepad (right‑click → Open with → Notepad).
- Fill in your details: email, passwords (use [Gmail App Passwords](https://support.google.com/accounts/answer/185833) if you use 2FA), CV path, name, etc. Save and close.

### 4. Run

- Double‑click **JobPulse.exe**.
- The first time, the app may say “Downloading Chromium…” (one-time, ~150 MB). Wait for it to finish.
- When the window opens: go to **Keywords**, **Accounts**, and **Settings**, fill them in, click **Save** on each tab, then click **Start** to run the bot.

**Where are my data and .env?**  
They are in the same folder as `JobPulse.exe`. Keep that folder in a safe place and don’t delete it.

---

## Mac (.dmg)

### 1. Download

- Get **JobPulse-mac.dmg** from the [latest release](https://github.com/SaeedAhmadMalakzai/JobPulse/releases).

### 2. Install

- Double‑click **JobPulse-mac.dmg** to open it.
- Drag **JobPulse** into **Applications** (or to a folder of your choice).
- Eject the disk image (right‑click the disk icon → Eject).

### 3. First-time setup (.env)

- On first run, JobPulse creates a config folder and a **.env** file at:  
  **~/Library/Application Support/JobPulse**
- To edit your settings: in Finder press **Cmd+Shift+G**, type:  
  `~/Library/Application Support/JobPulse`  
  then press Enter. Open **.env** in TextEdit, fill in your email, passwords, CV path, name, etc., and save.

### 4. Run

- Open **Applications** and double‑click **JobPulse**.
- The first time, the app may say “Downloading Chromium…” (one-time). Wait for it to finish.
- In the window: go to **Keywords**, **Accounts**, and **Settings**, fill them in, **Save** each tab, then click **Start**.

**Where are my data and .env?**  
They are in **~/Library/Application Support/JobPulse** (your data and `.env` stay there even if you move or update the app).

---

## Troubleshooting

- **“Chromium download failed”**  
  Check your internet connection and try **Start** again. The app will retry the one-time download.

- **“No CV selected”**  
  In **Settings → Attachments**, set the path to your CV (PDF) and click **Save**.

- **Antivirus or Windows SmartScreen**  
  If Windows blocks the .exe, choose “More info” → “Run anyway.” The app is open source; you can build it yourself from the GitHub repo.

- **Mac “unidentified developer”**  
  Right‑click **JobPulse** → **Open** → **Open** in the dialog. You only need to do this once.

---

For developers and terminal users, see the main [README](README.md).
