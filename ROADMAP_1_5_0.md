# RenKill 1.5.0 Roadmap

`1.5.0` is the next real capability release.
The goal is simple: get RenKill closer to the kind of coverage people are leaning on from `FRST.txt` + `Addition.txt`, while staying much safer than a generic fixlist runner.

## Release Goals

- improve structural detection for `Instaler.exe` / RenEngine variants that rotate names fast
- close more of the FRST/Addition parity gaps around startup state, policy state, and abnormal system posture
- keep remediation bounded and reversible where possible
- reduce false positives so users can trust `KILL & CLEAN`
- make post-clean confidence clearer after reboot and rescan

## Milestone 1: Detection Core

- strengthen scoring for Ren'Py bundle abuse beyond exact filenames
- tighten staging-dir detection for temp launchers, Godot `app_userdata`, and mixed `.exe` + `.dll` + data bundles
- improve loader-chain confidence so one noisy heuristic does not dominate the verdict
- expand known-safe context handling for dev tools, game launchers, browsers, and security software

## Milestone 2: FRST-Style Review Surfaces

- browser policy review for Chrome, Edge, Brave, and other Chromium variants
- recent security event review for Defender, Code Integrity, and related logs
- stronger startup state review across Startup folders, `StartupApproved`, Run keys, tasks, and shortcuts
- more posture review around Defender policy drift, Security Center state, proxy state, firewall allowances, and installed-program context
- optional analyst-style export with the same review buckets people keep posting from FRST/Addition cases

## Milestone 3: Remediation Safety

- quarantine-first cleanup for more removable artifact types
- better undo coverage for registry, task, firewall, Defender, and proxy changes
- stronger blocks around core OS processes, shell hosts, browsers, and security tools
- clearer separation between auto-remediated threats and review-only findings

## Milestone 4: Confidence And Workflow

- stronger post-clean scoring after reboot and rescan
- better distinction between local cleanup confidence and account/session exposure risk
- cleaner summaries for "probably RenLoader", "possible RenLoader", and "something else suspicious"
- guided next-step messaging for account recovery, sync reset, and remote session revocation

## Milestone 5: UX And Reporting

- cleaner report layout with sections that mirror the scan buckets
- export formats that are easier to share without leaking usernames or noisy local paths
- progress reporting that makes long scans feel alive instead of stuck
- better compact-window layout and fewer clipped UI elements

## First 1.5.0 Passes

- add browser policy review
- add recent security event review
- expand event review into Security Center, Firewall, and service-control clues without turning it into noisy generic log scraping
- keep both review-only until the heuristics are battle-tested
- use those findings to sharpen cleanup confidence instead of forcing more deletions
