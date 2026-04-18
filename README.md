# RenKill v1.4.3
**made with love - Cloud**

Detects, kills, and removes RenEngine Loader / HijackLoader infostealer artifacts
from Windows systems, with added cleanup coverage for the `Instaler.exe` chain,
post-infection session fallout, and FRST-style persistence review points.

---

## What it targets

| Malware Component | Detection Method |
|---|---|
| RenEngine Loader (`Instaler.exe`, `Instaler.py`) | Filename + folder structure match |
| HijackLoader DLL (`iviewers.dll`, randomname EXEs) | Filename + entropy heuristic |
| Ren'Py bundle structure (`renpy/` + `data/` + `lib/`) | Directory signature |
| Persistence staging (`broker_crypt_v4_i386`) | `%ProgramData%` / `%AppData%` path match |
| Persistence payloads (`Froodjurain.wkk`, `VSDebugScriptAgent170.dll`, `chime.exe`, `ZoneInd.exe`) | High-confidence filename + location match |
| Malicious desktop shortcuts (`.lnk`) | Shortcut target and argument review |
| Defender exclusions | FRST-style Defender posture review |
| Disabled startup leftovers | `StartupApproved` plus autorun correlation |
| Firewall allow-rules for suspicious programs | Rule target review with safe removal gates |
| Payload decrypt keys (`.key`) and Ren'Py payload scripts | Filename + location |
| Scheduled task persistence | `schtasks` query + keyword match |
| Registry autorun / IFEO / AppInit persistence | Registry review |
| WMI persistence | Subscription review |
| Active C2 connections | Network scan for known bad IPs |

---

## Build instructions (Windows)

Requirements: Python 3.10+ installed and in PATH.

```text
1. Place renkill.py and build.bat in the same folder
2. Double-click build.bat (or run from cmd)
3. Wait ~60 seconds for PyInstaller to compile
4. RenKill.exe appears in the same folder
```

## GitHub Actions release builds

```text
1. Push a version tag like v1.4.3
2. GitHub Actions builds RenKill.exe on windows-latest
3. The workflow attaches RenKill.exe and a SHA256 checksum to the GitHub Release
```

---

## Usage

1. Right-click and run as Administrator for full registry, service, and persistence cleanup coverage
2. Click `SCAN SYSTEM`
3. Review the verdict, confidence readout, and findings
4. Click `KILL & CLEAN` to remove high-confidence artifacts
5. If prompted, use `RESET SESSION DATA` to clear local browser and Discord session material
6. Reboot and run one more scan to confirm the machine comes back clean

---

## Scan locations

- `%TEMP%` and `%TMP%`
- `%APPDATA%` and `%LOCALAPPDATA%`
- `%PROGRAMDATA%`
- `%USERPROFILE%\Downloads`
- `%USERPROFILE%\Desktop`
- `%USERPROFILE%\Documents`
- `%LOCALAPPDATA%\Programs`
- Running processes and process trees
- Loaded modules for suspicious processes
- Active network connections
- Scheduled tasks
- Registry autoruns, IFEO, and AppInit
- WMI subscriptions
- Browser extensions
- Hosts, proxy, Defender exclusions, and firewall rules

---

## Research notes

- See [`RESEARCH_RENENGINE_2026.md`](./RESEARCH_RENENGINE_2026.md) for campaign notes,
  artifact mapping, recovery guidance, and source links that shaped detection coverage.

---

## After cleaning

Even if RenKill removes local artifacts, the data theft may already have happened.
From a separate clean device:

1. Change saved browser passwords
2. Revoke active sessions for Discord, Google, Steam, email, finance, and anything important
3. Move crypto assets to a fresh wallet if wallets were exposed
4. Re-enable strong MFA on critical accounts
5. Run Microsoft Defender Full Scan and Defender Offline after cleanup

---

## Sources / Research

- Cyderes Howler Cell (Feb 2026)
- Kaspersky Securelist (Feb 2026)
- Malwarebytes threat research on fake game / cracked software lure chains
- FRST helper workflows and remediation guidance from BleepingComputer, Emsisoft, and current Reddit cleanup threads
