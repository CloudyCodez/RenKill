# Changelog

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
