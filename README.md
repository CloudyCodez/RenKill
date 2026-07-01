# RenKill v1.7.2


THIS PROJECT HAS BEEN DEPRECATED. FOR UPDATED UTILITIES SURROUNDING THIS VIRUS, PLEASE VISIT: https://github.com/CloudyCodez/RenGuard


RenKill is a Windows cleanup tool for the fake Ren'Py `Instaler.exe` / `setup.exe` loader chain and the nearby infostealer and account-hijacker cases that now show up through trainers, cracks, fake playtests, fake VPNs, fake utilities, and Discord or Steam lures.

The tool is built around behavior and persistence, not one filename. These infections rotate names quickly, but they still tend to leave the same kinds of evidence: staged payload folders, scheduled tasks, startup relaunchers, policy drift, suspicious browser or extension state, and account-session fallout.

RenKill is not a replacement for changing passwords and revoking sessions from a clean device. It is meant to remove the local infection and give the user a clearer answer about whether persistence stayed gone after cleanup.

Current release notes are in [CHANGELOG.md](./CHANGELOG.md).

RenKill now reads the Windows UI language and localizes the visible app shell, key scan-status messaging, exposure warnings, and the critical safety prompts where translations are available, with English fallback when a string has not been translated yet.

## What RenKill Looks For

| Area | What RenKill Reviews |
|---|---|
| Fake Ren'Py bundles | `Instaler.exe`, `setup.exe`, Ren'Py folder layout, `archive.rpa`, `script.rpyc`, `.key` payload clues |
| Loader staging | HijackLoader-style side-load folders, odd `.dll` / `.exe` pairs, temp compile stages, Godot `app_userdata` + `.asar` payloads |
| Startup persistence | Startup folder files, shortcuts, `Run`, `RunOnce`, `RunOnceEx`, `StartupApproved`, Active Setup, policy autoruns |
| Scheduled tasks | Logon relaunchers, highest-privilege tasks, script hosts, staged Python payloads, missing task targets |
| WMI and services | WMI consumers, fake helper services, missing or user-writable service paths |
| Shell and logon hooks | Winlogon shell/userinit drift, Notify DLLs, Explorer hooks, toast activation residue |
| FRST-style load points | App Paths hijacks, `netsvcs` service membership, IFEO, KnownDLLs, Active Setup, RunOnceEx, shell hooks |
| Browser and session state | Chromium, Firefox, Discord, Telegram, Steam, wallet, VPN, password-manager, and FileZilla exposure indicators |
| Web redirect chains | Generated fake-download hosts, encoded redirect state, suspicious browser-history aftermath, and risky nearby downloads |
| Security posture | Defender exclusions, Defender policy drift, proxy settings, Security Center service state, suspicious firewall rules |
| Post-clean confidence | Reboot/rescan comparison for startup persistence and suspicious browser residue |

The scanner keeps a small vendor-noise filter for known updater residue from software such as Adobe, Lenovo Vantage, Edge Update, and OneNote. Those entries are ignored only when they match normal vendor paths or names and do not carry campaign markers.

## How Cleanup Works

RenKill separates findings into confirmed malware-style items, review-first items, and lower-confidence residue. High-confidence items can be quarantined or removed by `KILL & CLEAN`. Review-first findings are shown to the user and can be trusted when the user recognizes a local tool, server, or game path.

When RenKill quarantines a file, it moves it out of the live path, gives risky payloads inert names, and records recovery data where possible. `REVERT LAST CLEAN` can restore reversible changes from the most recent cleanup session.

`REPAIR DEFAULTS` handles safe protection repairs such as suspicious Defender exclusions, policy drift, proxy tampering, and suspicious firewall rules. It is intentionally separate from malware removal so security posture repair stays easy to reason about.

## Account Lockdown

`ACCOUNT LOCKDOWN` clears local session material from this PC, including supported browser profiles and common desktop app session stores. It helps reduce the chance that leftover local cookies, tokens, or web data can be reused after cleanup.

After `KILL & CLEAN`, RenKill also shows a critical account-safety warning. That warning is intentional: modern infostealers can steal usable browser cookies and app sessions before the local files are removed, so users still need to revoke sessions and secure accounts from a clean device.

After running malware, users should still use a clean device to:

1. Secure the email account tied to Steam, Discord, Google, Microsoft, and other important services.
2. Change passwords for saved browser accounts.
3. Revoke active sessions and trusted devices.
4. Review Discord Authorized Apps, Steam device trust, Steam Web API access, Microsoft/Google OAuth grants, unknown device-code sign-ins, and mailbox forwarding rules.
5. Move crypto assets to fresh wallets if wallet software or browser wallets were present.

## Typical Use

1. Extract the release zip.
2. Run `RenKill.exe` as Administrator.
3. Click `SCAN SYSTEM`.
4. Review the verdict and findings.
5. Use `KILL & CLEAN` for confirmed traces.
6. Use `ACCOUNT LOCKDOWN` if the user ran the malware or account abuse already happened.
7. Reboot and scan again.
8. Use the exported report if another helper needs a readable case log.

The main window keeps the first-run path simple: `SCAN`, `CLEAN`, `REPAIR`, and `ACCOUNT LOCKDOWN` stay visible. Less common actions live under `UTILITIES` so the tool feels calmer for users who are already stressed.

The red `!` button opens the account-safety warning at any time. It exists because local cleanup and account recovery are different jobs: RenKill can remove local persistence, but stolen cookies and sessions still need clean-device revocation.

## Trusted Paths

Some legitimate private servers, game tools, mods, or local projects can look unusual because they listen on the network or create firewall rules. RenKill lets the user trust a specific file or folder so review-only noise from that exact path stops appearing.

Trusted paths do not suppress strong campaign markers or high-confidence malware findings.

## RenInspect

`reninspect.py` is the static-only package inspector. It never executes the sample.

Use it on suspicious archives or extracted folders before running anything:

```text
python reninspect.py "C:\path\to\suspicious-folder"
python reninspect.py "C:\path\to\sample.zip" --report-out "C:\path\to\reninspect_report.txt"
```

It looks for Ren'Py bundle structure, suspicious side-load files, random launchers, payload clues, Godot `.asar` chains, and campaign-linked markers.

## Build

Requirements: Python 3.10+ in `PATH`.

```text
.\build.bat
```

The build creates:

```text
dist\RenKill\RenKill.exe
```

## Release Builds

GitHub Actions builds release packages from version tags:

```text
v1.7.2
```

The public release ships as a folder package instead of a single packed EXE. That keeps updates more reliable and reduces the amount of AV friction caused by fresh one-file packers.

RenKill currently tracks patterns from:

- Cyderes and Kaspersky reporting on RenEngine / HijackLoader.
- Microsoft reporting on Lumma and ClickFix-style delivery.
- BleepingComputer reporting on Steam-distributed malware and REMUS session theft.
- Malwarebytes reporting on fake game, fake VPN, fake utility, and gaming-mod infostealer lures.
- FRST helper workflows and real-world cleanup logs.

## Important Note

RenKill can remove local persistence and help clear local session material. It cannot undo data that was already stolen. If a user ran the malware, account recovery from a clean device is still part of the cleanup.
