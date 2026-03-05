# PROFESSIONAL DESKTOP APP SETUP

## What This Does

- Click icon -> splash screen appears
- Startup progress/status updates
- Bot starts in background (no terminal)
- Dashboard opens automatically
- System tray icon for quick control
- Can be pinned to taskbar

---

## STEP-BY-STEP INSTALLATION

### Step 1: Install Requirements

From PowerShell in the repo root, run:

```bash
pip install -r requirements.txt
```

If you only need launcher UI package:

```bash
pip install PyQt5
```

---

### Step 2: Confirm Launcher File Location

Required file:

```text
C:\Users\user\Documents\BAC\ict_trading_bot\bot_launcher.pyw
```

Important: keep extension as `.pyw` (not `.py`) so Windows uses `pythonw` mode.

---

### Step 3: Create Desktop Shortcut

#### Option A (Recommended): Direct Shortcut to `pythonw.exe`

1. Right-click Desktop -> New -> Shortcut
2. Use this target:

```text
C:\Users\user\AppData\Local\Programs\Python\Python313\pythonw.exe "C:\Users\user\Documents\BAC\ict_trading_bot\bot_launcher.pyw"
```

3. Name it `ICT Trading Bot`

If your Python path is different, run:

```bash
where pythonw
```

Use the returned path instead of `C:\Windows\System32\pythonw.exe`.

#### Option B: Via Batch File

`start_bot.bat` should contain:

```batch
@echo off
cd /d "C:\Users\user\Documents\BAC\ict_trading_bot"
start "" /B pythonw "bot_launcher.pyw"
exit
```

---

### Step 4: Add Icon

1. Right-click shortcut -> Properties -> Change Icon
2. Select:

```text
C:\Users\user\Documents\BAC\ict_trading_bot\bot_icon.ico
```

Fallback icon:

```text
C:\Windows\System32\shell32.dll
```

---

### Step 5: Pin to Taskbar

Right-click shortcut -> Pin to taskbar.

---

## Startup Flow

- Splash appears
- Bot process starts in background
- Launcher waits for dashboard API port
- Browser opens when dashboard is reachable
- Tray icon stays available for control

---

## System Tray Features

Right-click tray icon:
- Open Dashboard
- Status: Running
- Quit Bot

Double-click tray icon:
- Open Dashboard

Dashboard URL uses `config/settings.json` API config.
Default: `http://127.0.0.1:5000`

---

## Customization

### Change Splash Color

Edit this line in `bot_launcher.pyw`:

```python
palette.setColor(QPalette.Window, QColor(15, 23, 42))
```

### Change Startup Timing

Edit sleep calls in `startup_sequence()`:

```python
time.sleep(1.5)
time.sleep(2)
```

---

## Troubleshooting

### `No module named PyQt5`

```bash
pip install PyQt5
```

### Splash appears then closes

Check these files exist:
- `python/main.py`
- `config/settings.json`

### Dashboard does not open

1. Manually open `http://127.0.0.1:5000`
2. Confirm bot process is running in Task Manager
3. Confirm API host/port in `config/settings.json`

### Shortcut does nothing

1. Verify `pythonw` path with `where pythonw`
2. Recreate shortcut using Option A

### Icon not showing

1. Confirm `bot_icon.ico` exists in repo root
2. Re-apply icon in shortcut properties

---

## Final File Structure

```text
ict_trading_bot/
|- bot_launcher.pyw
|- bot_icon.ico
|- start_bot.bat
|- python/
|  |- main.py
|  |- api_server.py
|- config/
   |- settings.json
```

---

## Testing Checklist

- [ ] `pip install -r requirements.txt` completed
- [ ] `bot_launcher.pyw` exists in repo root
- [ ] `bot_icon.ico` exists in repo root
- [ ] Shortcut opens splash screen
- [ ] Dashboard opens automatically
- [ ] Tray icon appears
- [ ] Quit Bot stops process cleanly

---

## Auto-Start on Windows Boot

### Method 1: Startup Folder

1. Press `Win + R`
2. Run: `shell:startup`
3. Copy your desktop shortcut into this folder

### Method 2: Task Scheduler

Program:

```text
C:\Users\user\AppData\Local\Programs\Python\Python313\pythonw.exe
```

Arguments:

```text
"C:\Users\user\Documents\BAC\ict_trading_bot\bot_launcher.pyw"
```

Start in:

```text
C:\Users\user\Documents\BAC\ict_trading_bot
```