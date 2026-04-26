# RenKill 2.0 Roadmap

`2.0` is the point where RenKill stops feeling like a sharp single-purpose remover and starts feeling like a full response tool for the fake Ren'Py `Instaler.exe` / RenEngine mess.

The goal is still the same:

- kill the local infection
- kill its persistence
- help the user recover accounts and sessions
- do it with more precision than generic AV cleanup
- stay safer than a blind fixlist runner

## Release Pillars

### 1. Account Recovery Center

The malware problem and the account-compromise problem are not the same thing.
`2.0` should treat them as separate lanes.

Planned work:

- a built-in recovery center in the UI, not just a footer warning
- service-aware recovery guidance for browsers, Discord, email, socials, and wallets
- clearer clean-device messaging after scans and cleanup
- stronger separation between `local cleanup confidence` and `account/session risk`
- recovery-focused exports that can be shared with victims without dumping raw logs first

### 2. FRST Parity

RenKill should keep moving closer to the reasoning helpers are using in `FRST.txt` and `Addition.txt`.

Planned work:

- deeper startup-state coverage across Startup folders, Run keys, `StartupApproved`, tasks, and WMI
- better policy and posture review for Defender, Security Center, firewall, proxy, browser policy, and extensions
- stronger correlation between surfaces so one weird autorun means less than the same launcher showing up in three places
- more analyst-style reporting that groups findings by persistence surface and investigation value
- more of the small cleanup themes helpers keep doing manually, but only when bounded and reversible

### 3. Better Finding Separation

Right now users still have to think a little too hard about which findings are "kill this" versus "review this."
`2.0` should make that obvious.

Planned work:

- clearer distinction between:
  - confirmed malware / persistence
  - review-first posture drift
  - suspicious but weak/noisy findings
- better threat summaries in the UI and reports
- cleaner confirmation text before `KILL & CLEAN`
- less log spam from benign Windows/security churn
- stronger confidence scoring that weighs corroborated findings more than isolated heuristics

## Major Milestones

### Milestone A: Recovery UX

- add a real Account Recovery Center panel or dialog
- add service-specific next steps after scan/remediation
- make post-clean reboot/rescan flow more guided

### Milestone B: Persistence Depth

- keep expanding startup/task/WMI/script-host coverage
- improve temp staging and downloader-chain detection
- improve persistence overlap scoring

### Milestone C: Analyst Clarity

- improve report grouping and summary language
- add breakdowns for confirmed, review-only, and weak findings
- keep the exported report useful for helpers reading a user case remotely

### Milestone D: Safer Remediation

- preserve recovery/undo where possible
- keep protecting core Windows, browser, launcher, and security-tool processes
- continue reducing false positives before broadening auto-clean scope

## First 2.0 Passes

- land a clearer finding breakdown in scan/report output
- add a built-in Account Recovery Center entry point
- use the recovery/account-risk model more consistently in post-scan guidance
- keep tightening startup/temp detection around the newer Reddit/FRST case shapes

## Release Bar For 2.0

`2.0` should feel meaningfully different to a real user, not just internally better.

That means:

- scan results are easier to interpret
- cleanup is more trustworthy
- recovery guidance is built in
- startup and persistence coverage feels closer to the FRST workflow people are relying on today
