# Changelog

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
