# RenKill v1.4.9

Windows cleanup tool for the fake Ren'Py `Instaler.exe` / RenEngine loader chain.
It focuses on the stuff this infection tends to leave behind: staged payloads,
persistence, session fallout, and the same review surfaces people keep seeing in
FRST cleanup threads.

---

## Coverage

| Artifact or Behavior | How RenKill Looks For It |
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

## Build

Requirements: Python 3.10+ in `PATH`.

```text
1. Place renkill.py and build.bat in the same folder
2. Double-click build.bat (or run from cmd)
3. Wait ~60 seconds for PyInstaller to compile
4. RenKill.exe appears in the same folder
```

## Release Builds

```text
1. Push a version tag like v1.4.3
2. GitHub Actions builds RenKill.exe on windows-latest
3. The workflow attaches RenKill.exe and a SHA256 checksum to the GitHub Release
```

---

## How To Use It

1. Right-click and run as Administrator for full registry, service, and persistence cleanup coverage
2. Click `SCAN SYSTEM`
3. Read the verdict, confidence readout, and findings
4. Click `KILL & CLEAN` to remove high-confidence artifacts
5. If prompted, use `RESET SESSION DATA` to clear local browser and Discord session material
6. Reboot and run one more scan

---

## What It Reviews

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

## Research

- See [`RESEARCH_RENENGINE_2026.md`](./RESEARCH_RENENGINE_2026.md) for campaign notes,
  cleanup patterns, and the sources behind the current detection coverage.
- See [`ROADMAP_1_5_0.md`](./ROADMAP_1_5_0.md) for the next release target and the FRST-style parity work planned for it.

---

## After Cleanup

Removing the local infection does not undo stolen sessions or stolen data.
From a separate clean device:

1. Change saved browser passwords
2. Revoke active sessions for Discord, Google, Steam, email, finance, and anything important
3. Move crypto assets to a fresh wallet if wallets were exposed
4. Re-enable strong MFA on critical accounts
5. Run Microsoft Defender Full Scan and Defender Offline after cleanup

---

## Source Trail

- Cyderes Howler Cell (Feb 2026)
- Kaspersky Securelist (Feb 2026)
- Malwarebytes threat research on fake game / cracked software lure chains
- FRST helper workflows and remediation guidance from BleepingComputer, Emsisoft, and current Reddit cleanup threads
