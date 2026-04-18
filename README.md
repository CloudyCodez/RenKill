# RenEngine Hunter v1.3.0
**CJMXO STUDIOS — Defensive Security Tool**

Detects, kills, and removes RenEngine Loader / HijackLoader infostealer artifacts
from Windows systems.

---

## What it targets

| Malware Component | Detection Method |
|---|---|
| RenEngine Loader (`Instaler.exe`, `Instaler.py`) | Filename + folder structure match |
| HijackLoader DLL (`iviewers.dll`, randomname EXEs) | Filename + entropy heuristic |
| Ren'Py bundle structure (`renpy/` + `data/` + `lib/`) | Directory signature |
| Persistence staging (`broker_crypt_v4_i386`) | `%ProgramData%` / `%AppData%` path match |
| Persistence payloads (`Froodjurain.wkk`, `VSDebugScriptAgent170.dll`, `chime.exe`, `ZoneInd.exe`) | High-confidence filename + location match |
| Malicious desktop shortcuts (`.lnk`) | Shortcut content references persistence chain |
| Payload decrypt keys (`.key` files in `%TEMP%`) | Extension + location |
| Compiled payload scripts (`script.rpyc`, `archive.rpa` in temp) | Filename + location |
| Scheduled task persistence | `schtasks` query + keyword match |
| Registry autorun entries | `HKCU/HKLM Run` key scan |
| Active C2 connections | Network scan for `78.40.193.126` |
| Processes running from `%TEMP%` | Process path check via psutil |

---

## Build instructions (Windows)

Requirements: Python 3.10+ installed and in PATH.

```
1. Place renengine_hunter.py and build.bat in the same folder
2. Double-click build.bat (or run from cmd)
3. Wait ~60 seconds for PyInstaller to compile
4. RenEngineHunter.exe appears in the same folder
```

---

## Usage

1. **Right-click → Run as Administrator** (required for registry + scheduled task removal)
2. Click **SCAN SYSTEM** — scans filesystem, processes, network, registry, scheduled tasks
3. Review threats in the log (color-coded by severity)
4. Click **KILL & CLEAN** to execute all remediations
5. Click **EXPORT REPORT** to save a full threat report
6. Run scan a second time to verify the system is clean

---

## Scan locations

- `%TEMP%` and `%TMP%`
- `%APPDATA%` and `%LOCALAPPDATA%`
- `%PROGRAMDATA%`
- `%USERPROFILE%\Downloads`
- `%USERPROFILE%\Desktop`
- `%USERPROFILE%\Documents`
- `%LOCALAPPDATA%\Programs`
- All running processes (via psutil)
- All active network connections (via psutil)
- Scheduled tasks (via schtasks.exe)
- Registry Run keys (HKCU + HKLM)

---

## Known IOCs hardcoded

- **C2 IP**: `78.40.193.126`
- **Persistence dir**: `%ProgramData%\broker_crypt_v4_i386`
- **Persistence files**: `Froodjurain.wkk`, `Taig.gr`, `VSDebugScriptAgent170.dll`, `chime.exe`, `ZoneInd.exe`
- **Distrib site**: `dodi-repacks[.]site` (not blocked in tool, informational)
- **Kaspersky names**: `Trojan.Python.Agent.nb`, `HEUR:Trojan.Python.Agent.gen`,
  `Trojan.Win32.Penguish`, `Trojan.Win32.DllHijacker`, `Trojan-PSW.Win32.ACRstealer.gen`

## Research notes

- See [`RESEARCH_RENENGINE_2026.md`](./RESEARCH_RENENGINE_2026.md) for current campaign notes,
  artifact mapping, and source links used to shape detection coverage.

---

## After cleaning — mandatory steps

Even if this tool removes all artifacts, the data theft already occurred.
Do the following from a **separate clean device**:

1. **Change all saved browser passwords** — assume 100% of them are compromised
2. **Revoke all active sessions** — Google, banking, Discord, Steam, etc.
   Session cookies bypass 2FA so revocation is required, not just password reset
3. **Move crypto assets** — generate new wallet with fresh seed phrase on a clean machine
4. **Enable hardware/app MFA** on all critical accounts
5. **Consider full Windows reinstall** if any CRITICAL threats persist after two scans

---

## Sources / Research

- Cyderes Howler Cell (Feb 2026) — RenEngine + HijackLoader full chain analysis
- Kaspersky Securelist (Feb 2026) — RenEngine campaign deep dive
- AhnLab ASEC (Oct 2025) — Rhadamanthys / RenPy fake loading screen
- Malwarebytes Threat Intel (Apr 2026) — NWHStealer + Vidar campaigns
- Cloudflare Research (2025) — Lumma Stealer playbook
