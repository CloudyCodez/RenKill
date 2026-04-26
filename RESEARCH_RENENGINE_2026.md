# RenEngine / "RenLoader" Notes

Last updated: 2026-04-26

## Snapshot

What victims are calling "RenLoader" or the "Ren'Py `Instaler.exe` virus" matches current reporting on the `RenEngine Loader` campaign. The packaging in your screenshot is consistent with the Ren'Py launcher abuse described by Cyderes and Kaspersky: a small archive containing `Instaler.exe` plus `data`, `lib`, and `renpy` folders, with the real malicious logic hidden in `archive.rpa` and `script.rpyc`.

## What the campaign does

- Stage 1: Abuse a legitimate Ren'Py launcher (`Instaler.exe`) to execute a malicious compiled Python script from `archive.rpa`.
- Stage 2: Decrypt and hand off execution to HijackLoader.
- Stage 3: Establish persistence using `broker_crypt_v4_i386` directories and dropped loader files.
- Final payload: usually ACR Stealer, but Cyderes also observed Rhadamanthys, AsyncRAT, and XWorm in similar chains.

## Extra Stage Files Seen In Reporting

Kaspersky's February 11, 2026 write-up adds another useful layer. In one infection path, the malicious "game" unpacked a hidden `.temp` directory containing:

- `DKsyVGUJ.exe`
- `borlndmm.dll`
- `cc32290mt.dll`
- `gayal.asp`
- `dbghelp.dll`

Kaspersky also observed later-stage files and modules including:

- `hap.eml`
- `pla.dll`
- `Zt5qwYUCFL.txt`
- `W8CPbGQI.exe`

Those names are not all globally unique on every system. They matter most when they show up in `%TEMP%`, hidden `.temp` folders, or beside the rest of the RenEngine/HijackLoader chain.

## Variant Notes And Filename Churn

- Kaspersky's February 23, 2026 update says the same loader family has been active since at least March 2025 and has shifted payloads from Lumma to ACR, with Vidar also seen in some chains.
- Cyderes also reported new HijackLoader anti-analysis modules named `ANTIVMGPU`, `ANTIVMHYPERVISORNAMES`, and `ANTIVMMACS`.
- AhnLab and Microsoft reporting around `Amatera` suggests defenders should expect overlapping payload naming, MaaS reuse, and quick filename rotation.
- Exact names still help, but the stronger long-term signal is structure and chain behavior:
  - Ren'Py-style `data/lib/renpy` launcher bundles
  - paired launcher `.exe` plus `.py` / `.pyc`
  - user-writable staging directories with side-loading style `.exe` + `.dll` + odd data files
  - persistence and post-launch stealer behavior

## FRST Patterns Showing Up In Reddit Cleanup Threads

Based on Reddit cleanup threads through April 26, 2026 and the FRST lines victims shared, helpers are now seeing a persistence shape that is less dependent on fixed filenames and more dependent on where and how the payload is launched:

- `Startup` shortcuts in `%AppData%\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\`
- direct executable drops in the Startup folder, including names that try to look familiar like `DiscordSetup.exe`
- `ShortcutTarget` values pointing into `%LocalAppData%\Temp\tmp-<digits>-<random>\`
- randomly named temporary EXEs launched from those temp subfolders
- signer/company metadata on some of those temp EXEs reading `Shenzhen iMyFone Technology Co., Ltd`
- scheduled tasks executing payloads from `%AppData%\Roaming\Godot\app_userdata\<id>\`
- scheduled task arguments pointing at `node_modules.asar` or another `.asar` payload from the same user-writable tree
- startup scripts or script-host launches that pull from raw IPs, short-lived domains, or downloader-style PowerShell / `mshta` chains
- at least one April 2026 victim report describing a startup PowerShell script pulling from `45.146.87.17/load`
- FRST helpers in newer threads also calling out broken or injected browser extensions after the main malware cleanup, including a fake or invalid `Google Docs` extension in Chromium profiles

Important caveat: the `Shenzhen iMyFone Technology Co., Ltd` string is not proof of malware by itself. The suspicious signal is the full combination of:

- startup persistence
- temp-stage or Godot user-data execution
- random or throwaway launcher naming
- `.asar` payload handoff or other loader-style arguments

That combination is strong enough to score on structure even if the executable names rotate.

## What Looks Different In The Newer Cases

The big change in the newer Reddit cases is not a completely different loader. It is more that the cleanup stories keep showing broader persistence and a messier post-infection machine state:

- startup folder payloads that are direct `.exe` files, not only `.lnk` shortcuts
- scheduled tasks and startup entries that use throwaway downloader logic instead of a stable family filename
- more warnings from helpers that the recent waves can include backdoor / RAT behavior, not just one-shot stealer behavior
- more emphasis on checking browser extensions, Defender posture, and stray startup residue even after AV products say the machine is clean
- more cases where the first visible symptom is Discord or Gmail account abuse, but the surviving residue is an autorun script, temp launcher, or browser-extension foothold rather than the original `Instaler.exe`

That reinforces the same detection strategy for RenKill:

- care less about exact filenames
- care more about execution surface, launch chain, and persistence overlap
- keep startup, task, WMI, extension, Defender, firewall, and session aftermath in the same investigation loop

## What FRST.txt And Addition.txt Actually Show

The BleepingComputer FRST tutorial is useful here because `FRST.txt` and `Addition.txt` split the machine state into two different kinds of evidence:

- `FRST.txt` is the main scan. It focuses on processes, registry autoruns, scheduled tasks, services/drivers, internet settings, recent file creation/modification, and signature context.
- `Addition.txt` is the companion scan. It adds accounts, Security Center state, installed programs, shortcuts and WMI, loaded modules, hosts content, network state, disabled startup items, firewall rules, event log errors, and restore-point/device-manager context.

For this campaign, the current Reddit cleanup threads show why both matter:

- `FRST.txt` often exposes the autorun or scheduled-task persistence.
- `Addition.txt` often exposes the startup shortcut, WMI, browser-extension, disabled-startup, Defender, firewall, and software-install context that explains how the infection survives or what else it brought with it.

## How Helpers Are Fixing These Cases

Across the April 2026 Reddit threads, the helper workflow is pretty consistent:

1. Instruct the victim to disconnect and change passwords from a clean device.
2. Run `FRST.txt` + `Addition.txt`.
3. Review suspicious startup entries, startup shortcuts, scheduled tasks, Defender exclusions, firewall rules, browser extensions, and installed programs.
4. Build a custom `fixlist.txt` or clipboard fix.
5. Run FRST `Fix`.
6. Run a second-opinion scanner such as Emsisoft Emergency Kit when needed.
7. Re-scan with `FRST.txt` + `Addition.txt`.
8. Repeat until the persistence is gone.

The common themes in those fixes are:

- remove startup-folder `.lnk` entries
- remove scheduled tasks and disabled-startup leftovers
- remove suspicious Defender exclusions
- review installed programs that show up in the same case window, especially abuse-prone items like `Urban VPN proxy` or `NetSupport` if the victim did not knowingly install them
- remove suspicious browser extensions and proxy/VPN add-ons
- remove suspicious firewall allowances
- clear temp/cache with `EmptyTemp:`
- reboot and re-scan

## FRST Safety Details That Matter For RenKill

- FRST scan mode is diagnostic; the danger comes from the `Fix` step.
- FRST maintains backups and quarantine for many fix actions, but not every action is equally reversible.
- The BleepingComputer tutorial explicitly notes that `EmptyTemp:` permanently deletes temporary data and executes after the other fix actions, usually with a reboot.
- FRST can process startup items, scheduled tasks, WMI, firewall rules, and registry values directly from copied log lines or directives, which is why helpers can make very targeted fixes quickly.

For RenKill, the lesson is pretty simple:

- prefer bounded, typed remediation for files, tasks, shortcuts, registry values, exclusions, and firewall entries
- preserve undo where possible
- treat temp/session wipes as separate high-impact actions
- rely on re-scan confidence instead of assuming the first clean attempt was enough

## Current Fix Themes In Instaler / Social-Hijack Threads

The Reddit and FRST-assisted cases are not just "remove one EXE" infections. The cleanup advice keeps circling back to:

- Discord account recovery and session revocation
- browser password rotation and sync review
- Defender exclusion removal
- suspicious browser extension removal
- scheduled-task removal
- startup shortcut removal
- temp/cache cleanup
- repeat FRST scans after each fix

In other words, the "Discord/Instagram/social hijack" symptom is being treated as a full infostealer incident, not just a local file infection.

## High-Confidence Artifacts To Hunt

### Initial Bundle

- `Instaler.exe`
- `archive.rpa`
- `script.rpyc`
- Ren'Py-style folder trio: `data`, `lib`, `renpy`
- Temp `.key` files used to decode the next stage

### Persistence-Stage Artifacts

- `%ProgramData%\broker_crypt_v4_i386\`
- `%ProgramData%\broker_crypt_v4_i386\d3dx9_43.dll`
- `%ProgramData%\broker_crypt_v4_i386\Froodjurain.wkk`
- `%ProgramData%\broker_crypt_v4_i386\Taig.gr`
- `%ProgramData%\broker_crypt_v4_i386\VSDebugScriptAgent170.dll`
- `%AppData%\Roaming\broker_crypt_v4_i386\chime.exe`
- `%AppData%\Local\ZoneInd.exe`
- Desktop `.lnk` shortcuts pointing at the above persistence chain

### Exact Sample Hashes From Cyderes

- ZIP package SHA256: `9e3b296339e25b1bae1f9d028a17f030dcf2ab25ad46221b37731ea4fdfde057`
- `Instaler.exe` SHA256: `7123e1514b939b165985560057fe3c761440a9fff9783a3b84e861fd2888d4ab`
- `d3dx9_43.dll` SHA256: `326ec5aeeafc4c31c234146dc604a849f20f1445e2f973466682cb33889b4e4c`
- `VSDebugScriptAgent170.dll` SHA256: `db4ccd0e8f03c6d282726bfb4ee9aa15aa41e7a5edcb49e13fbd0001452cdfa2`

## Why Victims Lose Discord Even With 2FA

The payload families in this ecosystem steal browser credentials, cookies, auth tokens, wallet data, and session material. That means password changes alone are not enough. Session revocation is mandatory because stolen cookies can preserve access after 2FA.

## Notable Behavioral Signs

- "Game" installer does little or nothing visible.
- Browser sessions or Discord sessions get hijacked shortly after execution.
- Discord account starts sending spam, often fake MrBeast crypto/casino messages.
- Temp, AppData, and ProgramData receive randomly named executables or the `broker_crypt_v4_i386` persistence set.

## Recovery Implications

- File cleanup helps stop reinfection and persistence.
- It does **not** undo stolen credentials, stolen cookies, or wallet compromise.
- Incident response still needs password resets from a clean device, session revocation, Discord authorized-app review, and possibly a full OS reinstall if trust is lost.

## Concrete Remediation For Already-Infected Users

- Disconnect the infected PC from sensitive accounts until cleanup is complete.
- From a separate clean device, change passwords for any accounts saved in the browser.
- Revoke active sessions, not just passwords. This matters because infostealers can abuse stolen cookies and session material.
- For Google accounts, review signed-in devices and sign out unfamiliar sessions.
- For Chrome, turn Sync off and delete synced data before turning it back on if suspicious browser data keeps returning.
- For Discord, review `Authorized Apps`, deauthorize anything suspicious, and use Discord's hacked-account flow if the account is already being abused.
- After RenKill cleanup, run Windows Security Full Scan and Microsoft Defender Offline. Microsoft's guidance is that Offline Scan is specifically useful against persistent threats that hide from the normal running OS.
- If CRITICAL detections return after cleanup and offline scanning, a full Windows reinstall is still the safest option.

## Sources

- Cyderes, "RenEngine Loader and HijackLoader: Dual-Stage Attack Chain Fueling Stealer Campaigns" (2026-02-04): https://www.cyderes.com/howler-cell/renengine-loader-hijackloader-attack-chain
- Kaspersky Securelist, "The game is over: when 'free' comes at too high a price. What we know about RenEngine" (2026-02-11): https://securelist.com/renengine-campaign-with-hijackloader-lumma-and-acr-stealer/118891/
- Kaspersky Press Release, "Kaspersky identifies RenEngine loader distributed through pirated games and software" (2026-02-23): https://me-en.kaspersky.com/about/press-releases/kaspersky-identifies-renengine-loader-distributed-through-pirated-games-and-software
- AhnLab ASEC, "February 2026 Infostealer Trend Report" (2026-03-11): https://asec.ahnlab.com/en/92902/
- Microsoft Security Intelligence, "Trojan:Win32/Amatera.A!AMTB" (published 2026-02-05, accessed 2026-04-18): https://www.microsoft.com/en-us/wdsi/threats/malware-encyclopedia-description?Name=Trojan%3AWin32%2FAmatera.A%21AMTB&ThreatID=2147962444
- Malwarebytes, "Can you try a game I made? Fake game sites lead to information stealers" (2025-01-03): https://www.malwarebytes.com/it/blog/news/2025/01/can-you-try-a-game-i-made-fake-game-sites-lead-to-information-stealers
- Malwarebytes, "Can you test my game? Fake itch.io pages spread hidden malware to gamers" (2025-10-24): https://www.malwarebytes.com/blog/threat-intel/2025/10/can-you-test-my-game-fake-itch-io-pages-spread-hidden-malware-to-gamers
- Discord Support, "My Discord Account was Hacked or Compromised" (accessed 2026-04-17): https://support.discord.com/hc/en-us/articles/24160905919511-My-Discord-Account-was-Hacked-or-Compromised
- Discord Safety, "Tips to Prevent Spam and Hacking" (accessed 2026-04-17): https://discord.com/safety/360044104071-Tips-against-spam-and-hacking
- Google Account Help, "See devices with account access" (accessed 2026-04-17): https://support.google.com/accounts/answer/3067630?hl=en
- Google Chrome Help, "Sign in and sync in Chrome" (accessed 2026-04-17): https://support.google.com/chrome/answer/185277?hl=en
- Microsoft Support, "Virus and Threat Protection in the Windows Security App" (accessed 2026-04-17): https://support.microsoft.com/en-us/windows/help-protect-my-pc-with-microsoft-defender-offline-9306d528-64bf-4668-5b80-ff533f183d6c
- BleepingComputer, "FRST Tutorial - How to use Farbar Recovery Scan Tool" (updated 2025-09-11, accessed 2026-04-18): https://www.bleepingcomputer.com/forums/t/781976/frst-tutorial-how-to-use-farbar-recovery-scan-tool/
- Emsisoft, "How do I run a scan with FRST?" (accessed 2026-04-18): https://www.emsisoft.com/en/help/1738/how-do-i-run-a-scan-with-frst/
- Reddit, "Ran renpy's `instaler` might be cooked" (2026-04-18, accessed 2026-04-18): https://www.reddit.com/r/computerviruses/comments/1sok6ko/ran_renpys_instaler_might_be_cooked/
- Reddit, "accidentally ran the ren'py installer malware and now i have the mr beast crypto scam messages" (2026-04-15, accessed 2026-04-18): https://www.reddit.com/r/computerviruses/comments/1sma7sc/accidentally_ran_the_renpy_installer_malware_and/
- Reddit, "Friend ran Renpy \"Instaler\" and got discord hacked" (2026-04-15, accessed 2026-04-18): https://www.reddit.com/r/computerviruses/comments/1smgprq/friend_ran_renpy_instaler_and_got_discord_hacked/
- Reddit, "Accidentally ran Ren'Py 'Instaler' and now I don't know if I am infected" (2026-04-14, accessed 2026-04-18): https://www.reddit.com/r/computerviruses/comments/1sl5umb/accidentally_ran_renpy_instaler_and_now_i_dont/
- Reddit, "ran renpy instaler malware" (2026-04-10, accessed 2026-04-18): https://www.reddit.com/r/computerviruses/comments/1shbt9r/ran_renpy_instaler_malware/
- Reddit, "Accidentally ran renpy malware, help with FRST?" (2026-04-16, accessed 2026-04-18): https://www.reddit.com/r/computerviruses/comments/1smwlmp/accidentally_ran_renpy_malware_help_with_frst/
- Reddit, "Possibly still have a Ren py Trojan? Windows said it removed it but I'd like to make sure" (2026-04-18, accessed 2026-04-18): https://www.reddit.com/r/computerviruses/comments/1soiqj2/possibly_still_have_a_ren_py_trojan_windows_said/
