# Changelog

## v1.6.2 - 2026-05-06

This release folds in the latest proofing around trainer-style follow-ons and the May 2026 check on RenEngine-adjacent persistence. The important update is that the chain looks broader, but not fundamentally different: the operator is still leaning on user-writable relaunch points, scheduled tasks, and browser/session theft.

- Hardened persistence detection around the newer follow-on sample pattern:
  - scheduled-task review now escalates logon + highest-privilege relaunches that point at double-extension payloads like `*.exe.exe`
  - user-writable task/service payloads that typo-squat core helper names like `svchost` are now treated as masquerade hits, not just generic suspicious executables
  - service cleanup notes are clearer when the binary is a fake helper / fake system host in `%AppData%`, `%ProgramData%`, or similar writable roots
- Tightened Defender-exclusion scoring for stealer tradecraft:
  - exclusions targeting browser application paths, browser profile roots, or other high-value session stores are now treated as strong signals
  - process exclusions aimed at common browser/session targets like `chrome.exe`, `msedge.exe`, `firefox.exe`, `discord.exe`, `steam.exe`, or `telegram.exe` now surface as suspicious
- Refreshed the release notes and research brief so each release keeps a clearer source trail and explains whether the campaign actually changed or just rotated wrappers

## v1.6.1 - 2026-05-04

This release folds in the latest field update around fake playtests, malicious Steam titles, compromised extensions, ClickFix-style command lures, and safer user-driven review suppression.

- Added reviewed-safe path handling:
  - new `TRUST KNOWN PATH` action for software the user personally recognizes as safe
  - trusted paths now suppress review-only firewall and security-event noise tied to that exact file/folder tree without muting strong campaign hits
  - path-backed review findings in the live log can now show clickable inline `[TRUST]` and `[OPEN]` actions so users can trust an item or jump straight to it in Explorer from the scan output
  - fixed the inline action lane so it only appears on real filesystem-backed findings, not generic Defender/web event text
- Fixed a Steam/session cleanup regression:
  - Steam install-root discovery is now shared by both scanner and cleanup flows, which fixes the `ScanEngine` `_steam_install_roots` crash during exposure review
- Tightened current lure and extension coverage:
  - added known malicious Steam-game title markers from recent public victim reporting and FBI follow-up
  - stronger HTML / URL lure detection for fake verification, copy-paste, and `Win+R` style ClickFix prompts
  - extension review now escalates known risky names like `Torrent Scanner` and `QuickLens`
- Broadened ecosystem awareness around adjacent hijacker chains:
  - added `Fickle` / `worker.ps1` / `soft-gets.com` / `cclib.dll` / `CVKRUTNP.exe` style markers from Steam game compromise reporting
  - broader lure-host coverage for Discord CDN attachments, Catbox, GoFile, and similar delivery surfaces seen in game and social-account scams
- Improved account fallout guidance:
  - exposure review now includes `1Password`, `Bitwarden`, `KeePass`, `Authy Desktop`, and `WinSCP`
  - recovery guidance now calls out password-manager and 2FA cleanup when those surfaces are present
- Expanded review-first software coverage with more PUP / remote-support cleanup context from FRST-style cases:
  - `Web Companion`
  - `UltraViewer`

## v1.6.0 - 2026-05-02

This release is the full brief-driven pass. RenKill now covers much more of the broader account-hijacker / infostealer ecosystem around fake Ren'Py installers, trainers, fake playtests, ClickFix-style lures, and adjacent Discord / Steam / browser session theft fallout.

- Expanded account-hijack containment and exposure reporting:
  - Telegram Desktop session artifacts are now first-class in `ACCOUNT LOCKDOWN`, exposure notes, and recovery guidance
  - broader exposure reporting for `MetaMask`, `Exodus`, `Atomic Wallet`, `Ledger Live`, `FileZilla`, `NordVPN`, and `OpenVPN Connect`
  - stronger clean-device recovery guidance for tied email accounts, browser sync, Steam Web API key review, and downstream credential rotation
- Added deeper behavior and aftermath detection:
  - Firefox extension review via `extensions.json`
  - stronger dead-drop / resolver / EtherHiding-style markers including `telegra.ph`, Google Forms/Presentation, Steam profile dead drops, `remus`, and Ethereum RPC host context
  - broader suspicious outbound TLS detection for user-writable loader processes, not just a single hardcoded C2 IP
  - Powercat-style `HKCU\\Software\\Beep` fingerprint artifact review
- Improved forensic confidence and post-clean truthfulness:
  - flagged filesystem findings now include creation/modification time context
  - timestamp clustering now boosts confidence when suspicious artifacts land in the same short window
  - post-clean rescans now call out persistence or browser residue returning instead of falsely reading as a clean pass
  - reports now show post-clean mode, reboot state, and cleanup snapshot timing more clearly
- Hardened cleanup safety and eradication flow:
  - scheduled tasks are disabled before deletion
  - long-path-safe quarantine and restore handling for deep staging trees
  - `ACCOUNT LOCKDOWN` now clears Chromium `History`, `Bookmarks`, `Login Data`, and `Web Data`
  - `REPAIR DEFAULTS` now also tries to restore Windows Security Center service defaults alongside Defender/proxy/firewall posture

## v1.5.4 - 2026-05-02

This release pushes RenKill further beyond the classic fake Ren'Py wrapper and deeper into the broader account-hijacker / infostealer ecosystem around Discord, Steam, cracked software, trainers, and ClickFix-style lures.

- Added stronger account-containment and recovery coverage:
  - Steam session artifacts are now part of `ACCOUNT LOCKDOWN`
  - Steam exposure now feeds the recovery plan and account-risk guidance
  - clean-device recovery guidance now prioritizes the tied email account, Steam device trust, and Steam Web API style access review
- Added new behavior-focused detection for suspicious command residue:
  - `RunMRU` review for malicious loader commands pasted into the Run dialog
  - PowerShell history review for ClickFix-style download/execute chains
  - command-history hits now feed confidence scoring as review-first evidence
- Tightened broader lure awareness:
  - added coverage for `OneBrowser` in installed-program review
  - kept focus on behavior and persistence overlap instead of brittle filename matching
- Expanded research notes around fake playtests, trainer-style lures, Discord / Steam spread, and email-linked account hijack fallout

## v1.5.3 - 2026-04-30

This release is focused on making RenKill better at killing the actual malware chain instead of just sweeping up the mess it leaves behind.

- Added stronger behavior-based detection for trainer-style follow-ons that match the same post-compromise pattern, including:
  - hidden PowerShell hardware and VM profiling
  - random `%TEMP%` C# compile-stage workspaces driven through `csc.exe`
  - suspicious follow-on domain context like `silent-harvester.cc`
- Tightened startup, task, and service correlation so those behavior signals help point at the creator, not just the temp residue.
- Reduced major paranoid-mode false positives:
  - built-in Windows and AppX firewall capability rules
  - trusted `Active Setup` updater flows
  - RenKill's own runtime, updater, recovery, and temp lanes
  - duplicate findings that were inflating threat counts
- Made temp-stage cleanup more disciplined:
  - strong compiler-stage and loader-stage directories still get hit hard
  - weak generic temp folders no longer get auto-removed on their own
  - benign temp roots like `ReShade` are ignored
- Strengthened user-safety actions:
  - broader `ACCOUNT LOCKDOWN` local session wipe coverage
  - stronger `REPAIR DEFAULTS` handling for browser/proxy drift
  - DNS flush after repair so resets settle immediately
- Cleaned up the source shape around the newer helpers so the detection and cleanup lanes read more like one maintained tool and less like stacked patches.

## v1.5.1 - 2026-04-27

- Fixed the GitHub self-updater staging flow so downloaded updates are hashed and verified correctly before restart.
- Added a clearer startup update prompt path for packaged builds.

## v1.5.0 - 2026-04-27

- Improved paranoid-mode safety around noisy firewall/AppX findings.
- Expanded `ACCOUNT LOCKDOWN` and `REPAIR DEFAULTS`.
- Added stronger self-ignore handling for RenKill runtime and update paths.
- Shipped a broader FRST-style persistence review pass.
