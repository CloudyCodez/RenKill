# RENKILL MAX RESEARCH BRIEF
## Fake Ren'Py / RenEngine / HijackLoader / Info-Stealer / Account-Hijacker Ecosystem

**Generated:** 2026-05-02  
**Tool Version Reviewed:** RenKill v1.5.4  
**Brief Type:** Operator/IR Research — Implementation-Driven  

> **Source confidence labeling used throughout this document:**
> - `[CONFIRMED]` — Direct vendor/researcher writeup, hashes, or code evidence
> - `[COMMUNITY]` — Observed in Reddit FRST threads, victim reports, or forum cleanup cases
> - `[INFERRED]` — Synthesis from confirmed behaviors and known patterns; not directly sourced

---

## A. Executive Summary

### What RenKill Is

RenKill is a Windows-native cleanup tool targeting the fake Ren'Py `Instaler.exe` / RenEngine / HijackLoader infection chain and its downstream account-hijack aftermath. It is a GUI-driven scanner and remediator that runs locally, requires administrator elevation, and covers filesystem artifacts, process state, registry persistence, scheduled tasks, WMI subscriptions, services, browser sessions, browser extensions, browser policies, system defense posture, and session material for Discord, Chromium-based browsers, Firefox, and Steam.

It is not an antivirus. It does not use signatures to stop execution in real time. Its value is in providing a structured, auditable, quarantine-first cleanup pass for users who are already infected — especially users who ran something they should not have and are now trying to determine the scope of compromise and restore their machine to a trustworthy state.

### The Problem Space

The fake Ren'Py ecosystem sits at the intersection of three things that make it persistently effective:

1. **Social trust inside piracy communities.** Victims actively seek and trust cracked game installers, game mods, and trainer tools. The malware distribution is baked into that trust loop. No exploit is required — the user double-clicks willingly.

2. **A multi-stage, modular chain with heavy anti-analysis.** RenEngine → HijackLoader is not one file you delete and done. The infection involves at least two distinct loaders, a modular second-stage framework with up to 38 modules, DLL side-loading, process doppelgänging, and systematic VM/sandbox evasion. What AV sees at scan time is often not what ran.

3. **Account-hijack aftermath that outlasts local cleanup.** The terminal payload (ACR Stealer, Lumma, Vidar, or successor families) steals browser session material, Discord tokens, Steam session files, and saved credentials. The local machine can be completely clean and the attacker can still be sitting on those stolen tokens. Local cleanup and remote session revocation are entirely separate problems, and only the first one is in RenKill's lane.

### Why Filename-Based Detection Is Not Enough

`[CONFIRMED]` Kaspersky's February 2026 Securelist writeup and Cyderes's February 2026 HowlerCell report both document active filename rotation within the same campaign:
- Stage 2 filenames (`dksyvguj.exe`, `w8cpbgqi.exe`) are randomized per build
- The `Froodjurain.wkk` persistence configuration file has been seen under different names in different variants
- The `d3dx9_43.dll` sideload target name is stable but the container exe names are not

`[CONFIRMED]` Kaspersky explicitly states the campaign has been distributing under CorelDRAW lures, Norland game lures, and other non-game software lures — the lure filename "Instaler.exe" is campaign-specific to the Ren'Py-themed delivery vector. The same HijackLoader chain is delivered under completely different names in non-gaming lure variants.

`[COMMUNITY]` April 2026 Reddit cleanup threads consistently describe infections where AV flagged and removed the initial dropper but persistence survived — scheduled tasks launching renamed EXEs from temp directories, startup shortcuts pointing at random-named launchers, and browser extension footholds that AV never flagged.

The stable detection signal is not the filename. It is the combination of: the folder layout and file-type set (`.rpa` + `.rpyc` + launcher + `data/lib/renpy`), the persistence shape (user-writable staging dir + autorun), the behavior (hidden PowerShell, hardware profiling, temp compile staging, browser data access), and the account-hijack aftermath (Discord session anomalies, browser extension drift).

---

## B. What RenKill Already Covers

This section maps the current v1.5.4 detection and remediation surfaces as directly derived from the source code and changelog.

### B.1 Filesystem Scanning

**High-confidence filename IOCs (auto-remediation eligible):**
- `instaler.exe`, `instaler.py`, `instaler.pyo`, `instaler.pyc` — core RenEngine stage 1 launcher
- `lnstaier.exe` — typosquat variant of the above
- `iviewers.dll` — HijackLoader DLL injection helper
- `script.rpyc` — compiled Ren'Py malicious payload script
- `archive.rpa` — Ren'Py archive carrying the malicious compiled script
- `froodjurain.wkk` — HijackLoader configuration blob
- `taig.gr` — campaign artifact
- `vsdebugscriptagent170.dll` — sideload target with confirmed SHA256 from Cyderes
- `chime.exe` — persistence-stage launcher
- `zoneind.exe` — persistence-stage launcher
- `d3dx9_43.dll` — sideload target with confirmed SHA256 from Cyderes
- `dksyvguj.exe` — HijackLoader stage 2 exe
- `cc32290mt.dll` — loader container DLL
- `gayal.asp` — stage payload decryption asset
- `hap.eml` — stage payload data file
- `w8cpbgqi.exe` — signed sideload host for DLL loading
- `zt5qwyucfl.txt` — loader stage asset

**RenPy bundle structure detection:**
- Directory trio `renpy/` + `data/` + `lib/` (RENENGINE_FOLDER_SET) triggers `RenEngine Bundle` category
- `.key` + `.rpa` + `.rpyc` extension set within the bundle triggers payload indicator scoring
- Paired launcher `.exe` + `.py`/`.pyc` with generic launcher keywords in the name adds additional confidence

**SHA256 IOC matching:**
- Five known-bad hashes from Cyderes and Hybrid Analysis are compared for specific candidate filenames, providing exact-match certainty independent of filename
- Hash checks are size-gated at 200 MB to avoid performance issues on large files

**Temp-stage directory detection:**
- `TEMP_STAGE_DIR_REGEX` matches `tmp-<digits>-<random>` temp staging patterns
- `HIJACKLOADER_STAGE_DIR_SIGNATURES` — three known file-set combinations that identify a HijackLoader staging directory with high confidence
- `TEMP_STAGE_SIDELOAD_EXTENSIONS` — `.asp`, `.asar`, `.dll`, `.eml`, `.key`, `.txt` in a temp staging context triggers additional scoring
- `TEMP_COMPILE_STAGE_OPTIONAL_SUFFIXES` — `.cmdline`, `.0.cs`, `.dll`, `.err`, `.out`, `.pdb`, `.tmp` in a temp directory alongside a random basename identifies the csc.exe C# compile-stage workspace from the Pragmata Trainer behavior profile

**Godot/ASAR payload detection:**
- `GODOT_APP_USERDATA_MARKER` — catches payload staging in `%AppData%\Roaming\Godot\app_userdata\`
- `ASAR_ARGUMENT_MARKERS` — `node_modules.asar` and `.asar` as process arguments are flagged as suspicious loader indicators

**iMyFone metadata signal:**
- `IMYFONE_COMPANY_TOKENS` — detects startup persistence or temp-stage executables signed with "Shenzhen iMyFone Technology Co., Ltd." metadata, a known signal from April 2026 FRST cleanup threads

**Scan root coverage:**
- `%TEMP%`, `%TMP%`, `%APPDATA%`, `%LOCALAPPDATA%`, `%PROGRAMDATA%`
- `%USERPROFILE%\Downloads`, `%USERPROFILE%\Desktop`, `%USERPROFILE%\Documents`, `%LOCALAPPDATA%\Programs`

**Benign exclusions (false positive suppression):**
- Smilegate ProgramData, Windows Defender ProgramData, Package Cache, OneDrive AppData, Discord AppData, Chrome User Data, Edge User Data, Brave User Data, Firefox Profiles are skipped during heavy file scanning to avoid false positive noise

### B.2 Process and Module Scanning

**Process IOC matching:**
- `CAMPAIGN_PROCESS_NAMES` — exact process name hits for confirmed campaign executables
- `PROCESS_IOC_MARKERS` — substring search across process paths, command lines, and loaded module paths for 30+ campaign-specific strings (stealer family names, campaign filenames, staging paths)
- `MASQUERADE_EXECUTABLE_NAMES` — legitimate Windows executable names that are high-value masquerade targets; when running from non-system paths these score as `Paranoid Masquerade Process`

**Module scanning:**
- `SUSPICIOUS_DLL_NAMES` — four campaign-specific DLL names checked when loaded by any process
- `LOADER_CONTAINER_DLLS` — four DLL names (including `dbghelp.dll` and `pla.dll` outside system32) that indicate the HijackLoader container loading pattern
- Module scan is targeted to PIDs that already scored on other signals, avoiding a full module enumeration on all processes

**PowerShell profiling detection:**
- `POWERSHELL_VM_PROFILE_MARKERS` — 10 specific command fragments (Win32_BIOS, Win32_DiskDrive, EnumSystemFirmwareTables, etc.) that match the hardware profiling behavior documented in the Pragmata Trainer Hybrid Analysis sample
- `POWERSHELL_STEALTH_SWITCHES` — `-noprofile`, `-noninteractive`, `-windowstyle hidden` flagged as `Stealth Profiling Script Host`

**Startup-launched process correlation:**
- Processes whose path matches a known startup surface (shortcut target, autorun value, scheduled task execute path) score as `Startup-Launched Process` in the KILL bucket

**Safe/trusted process protection:**
- `SAFE_PROCESS_NAMES`, `TRUSTED_PROCESS_NAMES`, `PROTECTED_SECURITY_PROCESS_NAMES`, `PROTECTED_CORE_PROCESS_NAMES` — four tiers prevent killing legitimate security tools, system processes, and common user applications
- `TRUSTED_VENDOR_PATH_MARKERS`, `TRUSTED_COMPANY_TOKENS`, `TRUSTED_FILE_DESCRIPTION_TOKENS` — PE metadata checks gate automatic termination

### B.3 Network / C2 Detection

- `C2_IPS` — currently contains `78.40.193.126`, the confirmed ACR Stealer C2 from Cyderes's February 2026 report
- Active TCP connections to this IP score as `Active C2 Connection` — CRITICAL severity, auto-remediation eligible via process termination of the connecting process

### B.4 Startup, Shortcuts, and Persistence Surfaces

**Startup folder shortcuts:**
- `%AppData%\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\` enumerated
- `SUSPICIOUS_STARTUP_BASENAMES` — `discordsetup`, `executor_ctrl`, `interfacebroker`, `server` flagged
- `STARTUP_SCRIPT_EXTENSIONS` — shortcuts pointing to script hosts, scripts, or `.hta` files scored
- `STARTUP_DOWNLOADER_TOKENS` — shortcut targets or arguments containing download-style PowerShell, mshta, curl, wget, etc. scored higher

**Startup direct EXE drops:**
- Executable files dropped directly into the Startup folder (not shortcuts) are detected and scored as `Startup Persistence Artifact`

**StartupApproved disabled-startup residue:**
- `STARTUPAPPROVED_DISABLED_STATES` — `{0x01, 0x03, 0x09}` byte values in HKCU/HKLM StartupApproved indicate disabled startup entries; these are flagged as `Disabled Startup Artifact` for review

### B.5 Registry Autorun / Persistence Keys

**Covered registry surfaces:**
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- `HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\Run`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce`
- RunOnceEx (separate collector)
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run`

**IFEO (Image File Execution Options):**
- Debugger values in IFEO for any executable are flagged as `IFEO Persistence` — review-first

**AppInit DLLs:**
- `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows\AppInit_DLLs` reviewed; non-empty values flagged as `AppInit Persistence`

**AppCert DLLs:**
- `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\AppCertDlls` reviewed; flagged as `AppCert Persistence`

**KnownDLLs:**
- `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\KnownDLLs` reviewed for unexpected entries — `KnownDLLs Review`

**SafeBoot:**
- `HKLM\SYSTEM\CurrentControlSet\Control\SafeBoot` reviewed for minimal-mode or alternate-mode override entries — `SafeBoot Review`

**Session Manager:**
- `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager` BootExecute and other values reviewed — `Session Manager Review`

**Active Setup:**
- `HKLM\SOFTWARE\Microsoft\Active Setup\Installed Components` enumerated; StubPath values checked against known-benign updater arguments; non-benign entries flagged as `Active Setup Persistence`
- Benign updater switches (`--configure-user-settings`, `--system-level`, `--application-host=`, `--verbose-logging`) are excluded from auto-remediation

**Logon scripts:**
- `HKCU\Environment\UserInitMprLogonScript` and equivalent logon-script keys reviewed

**Shell and Winlogon hooks:**
- `HKCU\Software\Microsoft\Windows NT\CurrentVersion\Winlogon` Shell, Userinit, Notify values reviewed
- `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon` Shell, Userinit, Notify values reviewed
- Explorer load/run keys reviewed for `Explorer Hijack Review`

**Command history (RunMRU):**
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU` values checked for CLICKFIX_SHELL_MARKERS and CLICKFIX_DOWNLOAD_TOKENS
- Hits scored as `Command History Review` — review-first

**Policy persistence:**
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run`
- `HKLM\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run`
- Additional policy paths checked for persistent execution vectors

**Alternate Data Streams:**
- Suspicious ADS on already-flagged files checked for `SUSPICIOUS_STREAM_NAME_MARKERS` — flagged as `Alternate Data Stream Review`

### B.6 Scheduled Tasks

- Full `schtasks /query /fo CSV /v` enumeration
- Task Execute paths and Arguments checked against campaign IOC markers, temp staging paths, downloader tokens, and common lure keywords
- Godot app_userdata paths and `.asar` arguments in task definitions flagged
- Random-named executables launching from `%TEMP%`, `%APPDATA%`, or `%PROGRAMDATA%` in task context scored
- Task XML captured to recovery session before deletion for revert capability

### B.7 WMI Persistence

- CommandLineEventConsumer subscriptions enumerated; command templates checked against IOC markers and downloader tokens
- ActiveScriptEventConsumer subscriptions enumerated; script text reviewed
- WMI persistence hits scored as `WMI Persistence` — review-first due to broad impact of WMI changes

### B.8 Services

- Service binary paths checked against campaign IOC markers
- Service paths launching from `%TEMP%`, `%APPDATA%`, or similar user-writable locations scored
- NetSupport service detection: client32-family filenames outside trusted install paths (`\\program files\\netsupport\\`) scored as suspicious, specifically checking for `\\appdata\\roaming\\microsoft\\updates\\local\\` staging path

### B.9 Browser Policies and Extensions

**Browser policy review:**
- `SOFTWARE\Policies\Google\Chrome`, `SOFTWARE\Policies\Microsoft\Edge`, `SOFTWARE\Policies\BraveSoftware\Brave` registry keys enumerated
- Values matching `BROWSER_POLICY_SUSPICIOUS_VALUE_TOKENS` (ExtensionInstallForcelist, proxy, homepage, RestoreOnStartup, etc.) flagged as `Browser Policy Review`
- Both HKLM and HKCU policy hives checked

**Browser extension review (Chromium):**
- Chrome, Edge, Brave, Opera extension manifests enumerated from on-disk extension directories
- Campaign keyword hits in manifest JSON scored
- Extensions with risky permissions (`cookies`, `downloads`, `management`, `nativeMessaging`, `proxy`, `webRequest`, `webRequestBlocking`) AND non-official update URLs scored
- Impersonated extension names (`google docs`, `google drive`, `google sheets`, `google slides`) with non-official update URLs auto-flagged
- Chrome/Edge Preferences files parsed to catch extensions referenced in settings but not on-disk (orphaned malicious extension state)
- Extensions stored in user-writable paths that are not in the standard extension directory scored

**Firefox not covered for extension manifests** — gap noted below.

### B.10 Defender, Firewall, Proxy, Security Center

**Defender exclusions:**
- `Get-MpPreference -ExclusionPath/Process/Extension` checked; exclusions for paths/processes matching campaign IOCs scored as `Defender Exclusion`
- Exclusion removal is reversible (recovery entry preserved)

**Defender policy:**
- `DEFENDER_POLICY_VALUE_NAMES` — `DisableAntiSpyware`, `DisableRealtimeMonitoring`, `DisableBehaviorMonitoring`, `DisableIOAVProtection`, `DisableScriptScanning` in `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender` flagged as `Defender Policy Review`

**Defender protection state:**
- Security Center status for AV, firewall, and update state reviewed via WMI `AntiVirusProduct`

**Firewall rules:**
- `Get-NetFirewallRule` enumerated; rules for suspicious program paths (user-writable locations, campaign filenames) flagged as `Firewall Rule Review`
- Benign Windows/AppX capability rules, WinDefend rules, corenet/wifidirect/remoteassistance rules suppressed from noise
- Firewall rule state captured for revert before removal

**Proxy configuration:**
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings` ProxyServer, ProxyEnable, ProxyOverride reviewed for non-standard proxy settings
- WinHTTP proxy (via `netsh winhttp show proxy`) reviewed separately
- Both reviewed under `Proxy Configuration Review` and `WinHTTP Proxy Review`
- DNS flush performed after proxy reset to ensure settings settle

**Hosts file:**
- `C:\Windows\System32\drivers\etc\hosts` checked for `SENSITIVE_HOST_MARKERS` (steamcommunity.com, discord.com, accounts.google.com, login.live.com, etc.) — flagged as `Hosts Tampering Review`

**Security event logs:**
- Windows Defender Operational, CodeIntegrity Operational, SecurityCenter Operational, Firewall, and System event logs checked for recent entries — `Security Event Review`

### B.11 PowerShell History

- `%APPDATA%\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` read
- `CLICKFIX_DOWNLOAD_TOKENS` and `CLICKFIX_SHELL_MARKERS` checked in history content
- Hits scored as `Command History Review` — review-first, not auto-remediated

### B.12 Installed Programs

- `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` and `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` enumerated
- `FRST_REVIEW_PROGRAM_NAMES` — `netsupport`, `netsupport manager`, `netsupport school`, `onebrowser`, `one browser`, `urban vpn`, `urban vpn proxy` flagged as `Installed Program Review`

### B.13 Exposure and Session Surfaces

**Browser exposure reporting:**
- `EXPOSURE_DIRS` — Discord, Chrome, Edge, Brave, Opera, Opera GX, Firefox profile directories checked for existence; presence noted in exposure report to inform the user of what sessions were potentially accessible to a stealer

**Steam exposure:**
- Steam root detected via registry; `config/config.vdf`, `config/loginusers.vdf`, `htmlcache`, `appcache/httpcache` noted as exposure indicators

**Account lockdown (ACCOUNT LOCKDOWN button):**
- `SESSION_RESET_APPS` — Discord (+ Canary + PTB), Chrome, Edge, Brave, Opera, Opera GX, WebView2, Firefox, Steam
- Session material deleted per app: cookies, local storage, session storage, IndexedDB, cache, service worker storage, network state, trust tokens, extension state, sessions data
- Steam htmlcache, httpcache, and config session files cleared
- Firefox: cookies.sqlite, webappsstore.sqlite, sessionstore.jsonlz4, sessionCheckpoints.json, sessionstore-backups, storage/default, cache2, OfflineCache
- All apps killed first before clearing

### B.14 Quarantine, Rollback, and Recovery System

- Per-cleanup session manifest with unique timestamp session ID
- Files and directories moved to quarantine (not deleted in place) using `shutil.move`
- Quarantine path: `%PROGRAMDATA%\RenKill\Recovery\sessions\<session_id>\quarantine\`
- Executable-type files renamed with `.renkill-quarantine` suffix to neutralize them in-place
- Quarantined items hardened with `attrib +r +h +s`
- Registry deletions, task deletions, firewall rule removals, proxy resets, Defender exclusion removals all captured in manifest with enough data to reverse
- `revert_last_remediation()` can restore all reversible changes from the most recent un-reverted session
- Pre-cleanup persistence snapshot captured (startup entries before cleanup) for post-cleanup comparison
- `compare_post_cleanup_persistence()` — after reboot and rescan, checks which startup entries reappeared vs cleared
- `compare_post_cleanup_browser_state()` — checks whether suspicious browser extension state reappeared

### B.15 Post-Cleanup Confidence and Repair

**Repair defaults (`REPAIR DEFAULTS` button):**
- Proxy settings restored to direct
- WinHTTP proxy reset
- Defender exclusions removed for campaign-flagged paths
- Defender policy disablement registry values removed
- Firewall rules for suspicious program paths removed
- DNS cache flushed post-repair

**Updater:**
- GitHub Releases API checked for newer versions
- Downloaded update ZIP hashed and SHA256-verified before extraction and restart
- Update state file prevents repeated update prompts

---

## C. Threat Ecosystem Deep Dive

### C.1 Confirmed Infection Chain — RenEngine/HijackLoader/ACR

`[CONFIRMED]` Source: Cyderes Howler Cell (Feb 2026), Kaspersky Securelist (Feb 2026), BleepingComputer/SOCPrime summaries

**Stage 0 — Distribution:**
- Cracked game installers and mods on piracy sites (dodi-repacks, saglamindir, gamesleech, artistapirata, awdescargas, zdescargas, parapcc, hentakugames, filedownloads, mega, mediafire, go.zovo)
- Fake CorelDRAW and other productivity software crackers (confirmed by Kaspersky)
- Discord DM "try my game" lures (Malwarebytes Jan 2025)
- Fake game playtest invites via Steam messages and Discord DMs (Bitdefender March 2026)
- The delivery archive is a ZIP containing what looks like a normal Ren'Py game

**Stage 1 — RenEngine Loader (Instaler.exe / script.rpyc):**
- `Instaler.exe` is a legitimate Ren'Py launcher binary, not modified at the binary level
- The malicious logic is entirely inside `archive.rpa` as a compiled Python script (`script.rpyc`)
- The Ren'Py engine executes `script.rpyc` as part of normal archive loading
- `script.rpyc` decodes its configuration using Base64 + XOR
- Runs a multi-factor VM/sandbox scoring check: RAM, CPU cores, disk size, BIOS serials, registry key checks, known VM artifact checks — if score is too low, exits silently
- If real environment confirmed, decrypts an XOR-encrypted ZIP archive containing `W8CPbGQI.exe` (signed) and companion DLLs
- Extracts this ZIP to a hidden temp staging directory
- Also uses `.key` files as decryption material at various stages

**Stage 2 — HijackLoader:**
- `dbghelp.dll` is used as a memory container: overwritten in memory with shellcode decrypted from `gayal.asp` using `cc32290mt.dll` as the decryption library
- The resulting in-memory payload is HijackLoader
- HijackLoader configuration is stored in `Froodjurain.wkk` using a custom IDAT-style structure with XOR encryption
- HijackLoader loads up to 38 modules including:
  - ANTIVM, ANTIVMGPU, ANTIVMHYPERVISORNAMES, ANTIVMMACS — four separate anti-VM/hypervisor detection modules (3 are new/unreported prior to Cyderes's Feb 2026 report)
  - UAC bypass module
  - Scheduled task persistence module
  - Reverse shell module
  - DLL side-loading helpers
  - Call stack spoofing
  - Process hollowing via **Process Doppelgänging**
- HijackLoader injects the final payload into a legitimate host process

**Stage 3 — ACR Stealer (current primary payload):**
- Uses **dead drop resolver** technique: C2 address stored in Base64 on a public page (Steam profile, Telegram Telegraph, Google Forms, Google Slides)
- Steals: browser credentials, cookies, session tokens from all Chromium-based browsers + Firefox; Discord tokens; Steam session files; cryptocurrency wallet data (MetaMask, Exodus, Electrum, etc.); clipboard; system info/HWID; screenshots
- Exfiltration goes to resolved C2; campaign ID embedded for tracking
- `[CONFIRMED]` Known C2 IP: `78.40.193.126` (Cyderes Feb 2026)

**Persistence established by HijackLoader / campaign:**
- `%ProgramData%\broker_crypt_v4_i386\` with `d3dx9_43.dll`, `Froodjurain.wkk`, `Taig.gr`, `VSDebugScriptAgent170.dll`
- `%AppData%\Roaming\broker_crypt_v4_i386\chime.exe`
- `%LocalAppData%\ZoneInd.exe`
- Desktop `.lnk` shortcuts pointing at `chime.exe` or `ZoneInd.exe`
- Scheduled task launching stage 2 EXE
- `[COMMUNITY]` Startup folder direct EXE drops (newer variants, April 2026 FRST threads)
- `[COMMUNITY]` Startup folder `.lnk` shortcuts pointing into `%TEMP%\tmp-<digits>-<random>\`
- `[COMMUNITY]` Scheduled tasks launching from `%AppData%\Roaming\Godot\app_userdata\<id>\` with `.asar` arguments

### C.2 Payload Rotation and Successor Families

The campaign has rotated through multiple stealer families and will continue rotating. Current state as of May 2026:

**Lumma Stealer (LummaC2):**
- `[CONFIRMED]` Original payload in early RenEngine variants (Kaspersky: first seen March 2025)
- `[CONFIRMED]` LummaC2 infrastructure partially seized by law enforcement in May 2025 — disrupted but not eliminated
- Uses dead drop resolvers: Steam profiles, Telegram, and other services
- ABE (Application-Bound Encryption) bypass for Chrome cookie extraction is Lumma-specific

**ACR Stealer:**
- `[CONFIRMED]` Primary payload in current RenEngine/HijackLoader chains as of Feb 2026 (Cyderes, Kaspersky)
- `[CONFIRMED]` Uses Steam/Telegram/Google services as dead drop resolvers (AhnLab ASEC Feb 2025)
- Previously distributed via HijackLoader; still is
- `ACRSTEALER` token already in PROCESS_IOC_MARKERS — good

**Vidar / Vidar 2.0:**
- `[CONFIRMED]` Observed in some RenEngine chains (Kaspersky Feb 2026)
- `[CONFIRMED]` Vidar 2.0 (Acronis TRU, March 2026): polymorphic builds, multithreaded execution, advanced obfuscation, debugger detection, **C2 infrastructure hidden via Telegram bots and Steam profiles as dead drop resolvers**
- Targets: browser credentials, cookies, Azure tokens, crypto wallets, FTP/SSH credentials, Telegram data, Discord, local files
- `VIDAR` token already in PROCESS_IOC_MARKERS — good

**Rhadamanthys:**
- `[CONFIRMED]` Observed in some Cyderes-traced chains
- `RHADAMANTHYS` already in PROCESS_IOC_MARKERS — good

**Remus (Lumma successor, new):**
- `[CONFIRMED]` Gen Digital, April 2026: 64-bit Lumma successor, shares ABE bypass code, same string obfuscation patterns
- **New**: Uses EtherHiding — embeds C2 address in Ethereum smart contract; malware queries public blockchain endpoints to resolve C2
- Replaces Steam/Telegram dead drops entirely; resistant to sinkholing
- Observed since February 2026
- `[INFERRED]` Will start appearing in RenEngine-adjacent chains if it hasn't already
- **NOT currently covered in RenKill IOC sets**

**Acreed / ACR successor variants:**
- `[CONFIRMED]` Webz.io / Dark web analysis: Acreed dominated post-Lumma vacuum, became leading stealer log provider on Russian Market by mid-2026
- Uses Steam + BNB Smart Chain for C2 communication; JSON-based log format
- `[INFERRED]` Likely overlap with ACR Stealer family; ACR string already in IOC set

**AsyncRAT / XWorm:**
- `[CONFIRMED]` Observed in some Cyderes-adjacent chains
- Provide persistent backdoor access rather than one-shot stealer behavior
- Can persist independently of the loader chain
- `[INFERRED]` If HijackLoader drops a RAT payload instead of or in addition to a stealer, the machine may have remote operator access even after file cleanup

**NetSupport RAT:**
- `[CONFIRMED]` Common ClickFix final payload (SentinelOne, Microsoft Security Blog)
- Detection in RenKill: file staging detection outside `Program Files\NetSupport\`, metadata token matching, suspicious path check for `\appdata\roaming\microsoft\updates\local\`
- Installed program review also flags NetSupport

### C.3 Lure Surface Variants

**Cracked game/software installers:**
- Delivered via piracy sites; user downloads a ZIP, extracts, runs what looks like a setup EXE
- Current breadth: games (dodi-repacks, norland, any popular title), productivity software (CorelDRAW confirmed by Kaspersky), mods
- `[CONFIRMED]` Kaspersky: "dozens of different web resources" carry RenEngine under various lure names

**Fake game playtests (Discord/Steam):**
- `[CONFIRMED]` Bitdefender March 2026: attackers impersonate developers, create fake Discord servers with bots, send playtest invites via DM or Steam messages
- Victims download a "playtest build" ZIP or installer
- Fake Steam store pages replicated convincingly
- `[CONFIRMED]` BleepingComputer July 2025: Chemia game on Steam itself carried HijackLoader + Vidar + Fickle Stealer — attacker added malware to an early access game already on Steam; official Steam storefront trust exploited
- `[CONFIRMED]` Malwarebytes Jan 2025: Discord DM "can you try a game I made?" campaign; downloads from Dropbox, Catbox, Discord CDN via compromised accounts

**Fake game trainers and cheats:**
- `[CONFIRMED]` Hybrid Analysis: Pragmata_Trainer.exe shows same post-compromise behavior (hidden PowerShell profiling, C# compile staging, Discord aftermath)
- `[CONFIRMED]` Vidar 2.0 (Acronis TRU March 2026): GitHub repositories with fake game cheats, Reddit posts promoting fake cheat tools
- `[CONFIRMED]` ThreatLocker Feb 2026 Powercat campaign: fake Roblox/Minecraft/GTA cheat tools
- Cheats ask users to disable AV — users comply because real cheats behave similarly

**ClickFix / fake CAPTCHA:**
- `[CONFIRMED]` Microsoft Security Blog Aug 2025, Rapid7 March 2026, SentinelOne May 2025, multiple Feb 2026 sources
- Compromised websites inject fake Cloudflare CAPTCHA challenges
- Victim instructed to `Win+R` or open PowerShell and paste a command
- Command downloads and executes a payload (Lumma, NetSupport RAT, LummaC2, StealC, AsyncRAT, XWorm)
- `[CONFIRMED]` ClickFix variant uses Windows Terminal (`Win+X`) instead of Run dialog (Microsoft Threat Intel Feb 2026)
- `[CONFIRMED]` ClickFix persistence: modifies `RunMRU` registry key so PowerShell redeployment script executes at startup
- **RenKill already detects RunMRU abuse** — this is a real win

**Steam gift/trade/vote lures:**
- `[COMMUNITY]` Consistent pattern in Reddit threads: hijacked Steam account sends friends gift links or trade offers containing malicious links
- `[CONFIRMED]` Valve/Steam support: stolen accounts commonly spread via friend messages

**Already-hijacked account spread:**
- After initial infection, compromised Discord account sends the same lure to all contacts
- The message now appears to come from a known friend — trust is maximized
- `[CONFIRMED]` Malwarebytes Jan 2025: Discord CDN used for delivery because compromised accounts add upload credibility

### C.4 Anti-Analysis and Stealth Methods

**VM/sandbox scoring (RenEngine):**
- `[CONFIRMED]` Multi-factor score: RAM quantity, CPU core count, disk size, BIOS serial format, known VM registry artifacts, known VM-linked values
- Silent exit if score too low — AV sandbox analysis yields nothing
- `[CONFIRMED]` HijackLoader adds ANTIVMGPU (GPU-specific), ANTIVMHYPERVISORNAMES (hypervisor name checks), ANTIVMMACS (VM-linked MAC address checks) — three distinct anti-VM modules

**Process Doppelgänging:**
- `[CONFIRMED]` HijackLoader uses this to hollow and inject into legitimate processes, making in-memory payload appear as a trusted signed process

**DLL side-loading:**
- `[CONFIRMED]` `W8CPbGQI.exe` (signed) side-loads the malicious DLL chain — execution appears to originate from a trusted signed process

**Call stack spoofing:**
- `[CONFIRMED]` Cyderes/SOCPrime document this as part of HijackLoader's evasion capabilities
- Makes call stack analysis less useful for dynamic analysis

**Module stomping:**
- `[CONFIRMED]` SOCPrime summary: HijackLoader uses module stomping (overwrites legitimate DLL memory with payload)

**Memory-only execution:**
- `[CONFIRMED]` Microsoft Security Blog on ClickFix: final payloads are often fileless, loaded as .NET assemblies or CLR modules in memory by LOLBins — AV filesystem scans find nothing

**Dead drop resolver for C2:**
- `[CONFIRMED]` ACR Stealer, Vidar 2.0, Remus all use legitimate public services to store C2 addresses
- Services: Steam profiles, Telegram Telegraph, Google Forms, Google Slides, Ethereum smart contracts (Remus EtherHiding)
- Traffic to Steam/Google/Telegram looks normal from a firewall perspective

**Fake loading screen:**
- `[CONFIRMED]` Kaspersky: infected installer shows a fake game loading screen while malicious scripts execute in background — user sees expected behavior

**Stealer self-cleanup:**
- `[CONFIRMED]` CyberArk analysis: infostealers (e.g., RisePro) often copy data to a temp file for exfiltration and then delete the temp file — leaves less forensic residue

**Obfuscation and encoding:**
- Configuration decoded via Base64 + XOR (RenEngine)
- Remus uses Ethereum smart contracts for C2 — entirely external to traditional C2 detection

### C.5 Account Hijack Methods and Browser/Session Theft

See Section F for the full deep dive. The core mechanics:
- Stealer reads `%LOCALAPPDATA%\<Browser>\User Data\*\Network\Cookies` — SQLite database containing session cookies for all authenticated sites
- Stealer reads `%LOCALAPPDATA%\<Browser>\User Data\*\Login Data` — SQLite database of saved usernames and passwords (Chrome AES-encrypted with DPAPI; key in `Local State`)
- **Chromium Application-Bound Encryption (ABE):** Google introduced ABE in Chrome 127 to bind cookie encryption to the browser process. Lumma and its successor Remus bypass ABE by **injecting shellcode into the browser process itself** to decrypt cookies from within a trusted process context
- Discord tokens stored in `%AppData%\Roaming\Discord\Local Storage\leveldb\` — read directly from LevelDB files
- Steam session material in `config/config.vdf`, `config/loginusers.vdf`, and `htmlcache`

---

## D. Stable Behaviors vs Rotating IOCs

This is the most important section for detection strategy. Filenames rotate. Behavior does not.

### D.1 Fast-Rotating (Don't Rely On These Alone)

- Stage 2 EXE names: `dksyvguj.exe`, `w8cpbgqi.exe` — per-build random
- Stage payload data file names: `gayal.asp`, `hap.eml`, `zt5qwyucfl.txt` — per-build
- Stealer C2 IPs and domains — rotate constantly; `78.40.193.126` is confirmed but may already be dead or supplemented
- Dead drop resolver pages — new Steam/Telegram/Google pages created per campaign
- ClickFix domain infrastructure — new domains per campaign (`cptchbuild.bin` filename rotates)
- AV detection names across families — vendors rename detections

### D.2 Stable Behaviors (High-Confidence Long-Term Signals)

**Folder shape:**
- `[CONFIRMED]` Ren'Py bundle: `data/`, `lib/`, `renpy/` directories + `Instaler.exe` + `archive.rpa` + `script.rpyc` — this is the RenEngine launcher shape; it is stable across variants because it exploits the Ren'Py engine architecture
- `[CONFIRMED]` broker_crypt_v4_i386 directory: confirmed in Cyderes and Kaspersky; structurally stable

**DLL side-load pattern:**
- `[CONFIRMED]` Signed-exe + sideload-DLL + odd data files (`.asp`, `.eml`, `.wkk`, `.gr`) in a temp directory — this shape is HijackLoader's staging signature and is structurally required by its loading mechanism

**csc.exe temp compile workspace:**
- `[CONFIRMED]` Hybrid Analysis Pragmata_Trainer.exe: `%TEMP%\<random>\<sameName>.cmdline`, `<sameName>.0.cs`, `<sameName>.dll` — the C# compiler is invoked on-the-fly to compile a stage payload; the workspace structure is mechanically required by `csc.exe`'s output format

**Hidden PowerShell hardware profiling:**
- `[CONFIRMED]` Same Hybrid Analysis sample: PowerShell `-NoProfile -NonInteractive -WindowStyle Hidden` + `Get-CimInstance` against Win32_BIOS, Win32_ComputerSystem, Win32_DiskDrive, Win32_PhysicalMemory, Win32_PnPEntity, Win32_SoundDevice + `Add-Type -MemberDefinition` + `EnumSystemFirmwareTables/GetSystemFirmwareTable` — this is a VM scoring block; the specific CimInstance class names are what the scoring logic needs

**Godot app_userdata staging:**
- `[COMMUNITY]` Multiple April 2026 FRST threads: scheduled tasks launching from `%AppData%\Roaming\Godot\app_userdata\<id>\` with `.asar` payload arguments — legitimate Godot games do store data here but the combination of scheduled task + `.asar` in app_userdata is suspicious

**iMyFone signing metadata:**
- `[COMMUNITY]` April 2026 FRST threads: startup EXEs with "Shenzhen iMyFone Technology Co., Ltd" in version metadata — likely stolen/leaked code signing certificate; the specific company token is the signal, not the filename

**RunMRU ClickFix persistence:**
- `[CONFIRMED]` CyberProof/GBHackers Feb 2026: ClickFix infostealer modifies RunMRU to cause PowerShell redeployment script execution at startup — RunMRU containing PowerShell download commands is a direct and specific signal

**Startup folder direct EXE drops with known-suspicious basenames:**
- `[COMMUNITY]` April 2026 FRST threads: `discordsetup.exe`, `executor_ctrl.exe`, `interfacebroker.exe`, `server.exe` as direct startup EXE drops — the name set is expanding but these specific basenames are currently stable signals

**Dead drop resolver network behavior:**
- `[CONFIRMED]` ACR, Vidar 2.0: processes (not browsers) making HTTP requests to Steam profile URLs, Telegram Telegraph, Google Forms/Slides pages containing Base64 strings — behavioral signal, not a domain name
- `[INFERRED]` Remus: processes making HTTPS/JSON-RPC calls to Ethereum node endpoints (infura.io, eth.llamarpc.com, cloudflare-eth.com) — this is new and currently undetected by RenKill

**Browser-process memory injection:**
- `[CONFIRMED]` Remus, Lumma ABE bypass: shellcode injected into the Chrome/Edge/Brave process to decrypt ABE-protected cookies from within the process context — detectable as unexpected code injection into a browser process but requires endpoint-level process memory monitoring, beyond RenKill's current scope

---

## E. FRST / Addition.txt Parity Analysis

### E.1 What FRST Helpers Are Catching in the Wild

`[COMMUNITY]` Synthesized from Reddit/BleepingComputer FRST threads through April 26, 2026:

**From FRST.txt (main scan):**
- Autorun entries in `Run`/`RunOnce` for random-named EXEs in `%Temp%` or `%AppData%`
- StartupApproved disabled entries that are actually the malware persistence (disabled by a previous AV pass but not removed)
- Scheduled tasks with random names executing from `%Temp%` or `%AppData%`
- Defender exclusions for campaign artifact paths
- Recently modified files in `%Temp%`, `%AppData%`, `%ProgramData%` (FRST shows recently modified/created within 30 days)
- Suspicious signatures: unsigned EXEs from user-writable locations, EXEs with no company/description metadata

**From Addition.txt:**
- Startup folder `.lnk` shortcuts pointing at staging directories
- Direct EXE drops in Startup folder (names like `DiscordSetup.exe`)
- WMI subscriptions
- Installed programs (NetSupport, Urban VPN, OneBrowser)
- Loaded modules in running processes
- Defender/AV status
- Firewall rules for suspicious programs
- Hosts file content
- Proxy settings
- Browser extension state (via Chromium profile data)
- Security event log entries (Defender detections, service failures)
- Disabled startup residue

**Helper workflow patterns (April 2026 cases):**
1. Get FRST.txt + Addition.txt
2. Identify startup, task, WMI, Defender exclusion, and extension anomalies
3. Build fixlist.txt targeting specific entries
4. Run FRST Fix with EmptyTemp
5. Reboot → repeat scan
6. If persistence returns, deeper dig into extension state, firewall rules, and service residue

### E.2 What RenKill Already Mirrors

RenKill's detection surface is closely aligned with the Addition.txt coverage areas:
- ✅ Startup folder `.lnk` and direct EXE drops
- ✅ Run/RunOnce/RunOnceEx/Policy autoruns
- ✅ StartupApproved disabled-startup residue
- ✅ Scheduled tasks
- ✅ WMI subscriptions
- ✅ Shell / Winlogon / Explorer hooks
- ✅ IFEO / AppInit / AppCert / Active Setup / SafeBoot
- ✅ Defender exclusions and policy disablement
- ✅ Firewall rules
- ✅ Proxy and WinHTTP proxy
- ✅ Hosts file
- ✅ Installed programs (targeted set)
- ✅ Browser extensions (Chromium)
- ✅ RunMRU / PowerShell history

**Where FRST helpers still have an advantage:**

- **Recently modified/created file timeline.** FRST.txt shows files modified within 30 days by default, giving helpers a temporal view that RenKill lacks. Seeing a batch of files created at the exact time of infection is high-value context even if the filenames are random. RenKill does not currently record or use file creation/modification timestamps as a detection signal.

- **Loaded module context in FRST.txt.** FRST.txt shows what DLLs are loaded by processes in memory at scan time. RenKill's module scanning is targeted (only scans modules for processes that already scored on other signals) rather than a full process-module inventory.

- **Process digital signature and path context.** FRST.txt shows full paths and signature state for running processes inline. RenKill checks signatures during process evaluation but does not present them in a consolidated process list for human review.

- **Restore point / driver context (Addition.txt).** FRST shows available system restore points and device manager state. RenKill attempts to create a restore point but doesn't report on existing ones.

- **Firefox extension state.** FRST helpers often call out Firefox extensions directly. RenKill currently reviews Chromium-family extensions but does not have a comparable Firefox extension manifest reader.

### E.3 Where RenKill Can Safely Emulate FRST Context

The most valuable FRST context to add to RenKill output, without turning it into a dangerous generic fixlist runner:

1. **File creation timestamp display for flagged findings.** When RenKill flags a suspicious file or startup entry, show its creation timestamp. Clusters of artifacts created at the same time are strong corroboration.

2. **Process signature summary in the findings report.** For all running processes that score as suspicious, include their signing state and company metadata in the report display — the same info FRST.txt provides inline.

3. **Recently created files in staging directories.** When a suspicious staging directory is found, list files inside it with creation times in the report, even for files with unknown names.

4. **Firefox extension review.** Read Firefox `extensions.json` from all profile directories and flag extensions with suspicious names, non-Mozilla update URLs, or risky permissions. Same logic as the Chromium reader.

5. **Restore point creation with status reporting.** When RenKill creates a restore point before cleanup, report success/failure clearly. If creation fails (e.g., VSS disabled), call it out as a potential security posture issue.

The key safety constraint to preserve: RenKill's remediation should remain typed and bounded. FRST's power (and danger) is that it can apply arbitrary registry deletes, file deletions, and service stops from a fixlist. RenKill's typed remediation categories (process kill, registry value delete, task delete, file quarantine, etc.) are safer because each action is gated by its category's specific logic.

---

## F. Account Hijack / Session Theft Analysis

### F.1 What Browser/Session Theft Actually Means

A stealer does not need to know your passwords. It reads the decrypted session state from disk.

**Cookies and session tokens:**
- Every logged-in website stores an encrypted session cookie in the browser's `Cookies` SQLite file (Chromium: `Network/Cookies` in each profile)
- This cookie, if stolen before it expires, lets the attacker access your account **without your password and without triggering 2FA** because the session is already authenticated
- Cookie lifetime for many sites (Gmail, Discord, Steam) is days to weeks — a stolen cookie can remain valid long after the infection

**Chromium Application-Bound Encryption (ABE):**
- `[CONFIRMED]` Google introduced ABE in Chrome 127 to encrypt cookie data so it can only be decrypted by the browser process itself
- `[CONFIRMED]` Lumma and Remus (its successor) bypass this by injecting shellcode directly into the Chrome process to decrypt cookies from within Chrome's memory context
- This means ABE does not stop modern stealers — it only stops offline cookie file access

**Discord tokens:**
- Discord stores the auth token in `%AppData%\Roaming\Discord\Local Storage\leveldb\` as a plain (or lightly obfuscated) string in LevelDB files
- Stealing this token gives the attacker full access to the Discord account, including sending messages, joining servers, and accessing DMs — **without any password or 2FA check**, because the token represents an already-authenticated session
- Discord token theft is the direct cause of the "Mr. Beast crypto messages" symptom that characterizes these infections

**Saved passwords:**
- Chrome/Edge/Brave store passwords in `Login Data` SQLite file, AES-256-GCM encrypted using a key stored in `Local State` and further protected by DPAPI
- DPAPI protection is keyed to the current Windows user session — meaning any process running as the same user can decrypt it
- A stealer running in the victim's user context can decrypt and read all saved browser passwords

**Steam session files:**
- `config/config.vdf` contains the authentication token, `loginusers.vdf` contains remembered login data
- Steam's "remember me" session is stored here; stealing these files lets the attacker use the session on another machine with specific tools

### F.2 What "New Device Login via Email Code" Implies

When a Steam account or major service prompts "we sent a confirmation email to verify this new device," it means:

- A new session was initiated with the correct password (or a valid session token was used on a new machine)
- The attacker has either: the password itself, a valid session token from the stealer, or an active email session that can intercept the confirmation code

If the victim confirmed the email verification themselves during infection (thinking it was their own login), the attacker now has an established session on their controlled device.

**The email account tie-in:**
- `[CONFIRMED]` Valve/Steam documentation: Steam account compromises commonly follow compromise of the tied email account
- `[COMMUNITY]` Kaspersky Securelist comment from infected user (Feb 2026): "My email account was accessed without permission. Password reset codes were requested. Some accounts were taken over, including LinkedIn and Instagram."
- If the email account is compromised (via stolen email session cookie or saved email password), the attacker can reset passwords on any account that uses that email for recovery — **the email account is the master key**

**Critical implication for RenKill guidance:**
The recovery flow must be: **email first, everything else second**. Changing your Steam password from a machine whose email client still has a compromised session accomplishes nothing — the attacker can reset it again immediately.

### F.3 When the Tied Email Account Must Be Treated as Compromised

Treat the email account as compromised when any of these are true:
- Stealer ran on the machine with the email client or webmail session active
- `EXPOSURE_DIRS` in RenKill shows the browser profile was accessible
- Session was stored in a browser profile that was accessible at infection time
- User reports receiving unexpected password reset emails or 2FA codes
- User reports unauthorized access to accounts that use the same email for recovery

### F.4 What Recovery Steps Matter Most

In priority order:

1. **From a clean device (not the infected machine):** Change the tied email account password and immediately revoke all active sessions for that email account
2. **From a clean device:** Change Steam password
3. Deauthorize all Steam devices and sessions (Steam > Account > Manage Steam Guard > Deauthorize all other devices)
4. Review and revoke Steam Web API keys (Steam > Account > "Manage your Steam Web API keys") — API keys let attackers automate trade/offer actions even after password changes
5. Change Discord password from a clean device; use Discord's "Log out of all devices" option; review Authorized Apps and revoke anything unrecognized
6. Change all saved browser passwords for any account that was stored in the browser — use a clean device's password manager to do this systematically
7. For Google: review signed-in devices, sign out unfamiliar sessions, review third-party app access
8. For crypto wallets: assume any software wallet on the infected machine is fully compromised; move funds to a fresh wallet immediately
9. Enable hardware MFA (FIDO2/WebAuthn passkey or hardware security key) on all critical accounts where possible — this is more resistant to token theft than TOTP/SMS because the hardware key cannot be cloned from stored data

### F.5 What Local Cleanup Can and Cannot Solve

**Can solve:**
- Stopping the stealer process from continuing to run
- Removing persistence so the stealer does not re-run at next boot
- Clearing local session material so the stealer cannot extract future sessions from this machine
- Removing firewall/proxy modifications that could redirect traffic
- Repairing Defender posture so future threats are caught

**Cannot solve:**
- Undoing credentials or session tokens already stolen and exfiltrated
- Undoing actions taken by the attacker using stolen credentials
- Recovering accounts taken over before cleanup
- Invalidating stolen cookies that are still valid on the attacker's machine
- Recovering stolen cryptocurrency

**The user must understand:** a green "clean" result from RenKill means the local machine is no longer actively infected. It does not mean the accounts are safe. Session revocation and password changes from a clean device are mandatory regardless of scan result.

---

## G. Detection Opportunities

Prioritized list of concrete detection improvements for future RenKill versions. Each entry includes the signal, why it matters, FP risk, and recommended disposition.

---

**G.1 — File Creation Timestamp Clustering**

**Signal:** When multiple suspicious artifacts are found, compare their file creation timestamps. A cluster of files created within the same 60-second window is strong corroboration that they belong to the same infection event — even if their names are random.

**Why it matters:** Random-named staging files are the current evasion strategy. Their randomness defeats filename-based detection but their creation time is mechanically determined by the infection chain. Files that were all created at the same time are almost certainly related.

**FP risk:** Low. Timestamp comparison is only applied to already-suspicious files, not as a standalone signal.

**Disposition:** Report-only initially. Can graduate to corroboration scoring (boosting confidence of nearby findings) after validation.

---

**G.2 — Dead Drop Resolver Network Behavior**

**Signal:** Non-browser processes (especially those launched from temp staging directories or by scheduled tasks) making HTTP/HTTPS requests to Steam community profile URLs, Telegram Telegraph pages, or Google Forms/Slides pages that contain Base64-encoded strings.

**Why it matters:** `[CONFIRMED]` ACR Stealer, Vidar, and multiple other stealers in this ecosystem use legitimate public services to store and retrieve C2 addresses. This behavior is mechanically required and not obfuscatable at the network level — the malware must access these pages to function.

**FP risk:** Medium. Steam and Google are accessed legitimately by many applications. The signal requires: (a) the accessing process is not the legitimate Steam or Google application, and (b) the access comes from a known-suspicious process tree or path.

**Disposition:** Review-first when process context is suspicious; escalate to CRITICAL if combined with campaign IOC hits.

---

**G.3 — EtherHiding / Ethereum C2 Resolution Detection**

**Signal:** Processes (especially those launched from user-writable locations) making JSON-RPC calls to Ethereum node endpoints: `infura.io`, `eth.llamarpc.com`, `cloudflare-eth.com`, `ankr.com/rpc/eth`, or similar public Ethereum RPC endpoints.

**Why it matters:** `[CONFIRMED]` Remus (Lumma successor, Gen Digital April 2026) uses Ethereum smart contracts to store C2 addresses. This is new, completely resistant to sinkholing, and currently not detectable by any static IOC in RenKill. As Lumma successor families proliferate, EtherHiding will become more common.

**FP risk:** Low in consumer/gaming contexts. Legitimate applications rarely make Ethereum RPC calls.

**Disposition:** Review-first; CRITICAL when combined with process in user-writable location.

---

**G.4 — csc.exe Child Process with Temp Workspace (Compile-Stage Detection)**

**Signal:** `csc.exe` (C# compiler) launching with an argument pointing at `@"%TEMP%\<random>\<random>.cmdline"`, combined with the presence of `<random>.0.cs`, `<random>.dll` files with matching basename in the same temp directory.

**Why it matters:** `[CONFIRMED]` Hybrid Analysis Pragmata_Trainer.exe sample: this is the exact compile-stage behavior for inline payload staging. csc.exe is legitimately used by .NET apps, but the pattern of `@cmdline`-style invocation from a random temp directory with matching basename artifacts is specific to this pattern.

**FP risk:** Medium. Visual Studio, MSBuild, and .NET build tools use csc.exe. The random temp directory + matching basename + `@`-style cmdline pattern is distinguishing. Exclude known VS/MSBuild temp paths.

**Disposition:** Review-first as standalone; auto-remediate temp directory if combined with other campaign hits.

**Current coverage:** TEMP_COMPILE_STAGE_OPTIONAL_SUFFIXES covers detection of the temp workspace artifacts but does not explicitly detect the `csc.exe` invocation itself. The process scanner could add `csc.exe` launched from or pointing at a random temp path as a `Compiler Stage Process` finding.

---

**G.5 — Firefox Extension Manifest Review**

**Signal:** Read `%AppData%\Roaming\Mozilla\Firefox\Profiles\*\extensions.json` and enumerate installed extensions. Flag: extensions with `application/x-xpinstall` (`xpi`) URLs from non-Mozilla sources; extensions with names matching IMPERSONATED_EXTENSION_NAMES; extensions with suspicious permissions (`cookies`, `downloads`, `proxy`, `webRequestBlocking`).

**Why it matters:** `[COMMUNITY]` FRST helpers call out Firefox extension anomalies in cleanup threads. RenKill currently reads Firefox session files for ACCOUNT LOCKDOWN but does not review Firefox extensions for malicious state. Firefox has a meaningful share of the browser market and specifically appears in EXPOSURE_DIRS.

**FP risk:** Medium. Many legitimate extensions are not from addons.mozilla.org. Filter by permission set combined with non-official update URL.

**Disposition:** Review-first (Browser Extension Review category, same as Chromium).

---

**G.6 — Steam Web API Key Exposure Detection**

**Signal:** Check if Steam API keys are stored in common locations (some games/tools store API keys in config files); more importantly, include an explicit advisory in the account recovery guidance that Steam API keys must be reviewed and revoked.

**Why it matters:** `[COMMUNITY]` Steam Web API keys allow programmatic access to trade history, inventory, and offer management. An attacker with an API key can automate theft even after a password change. Multiple FRST threads mention this as a gap in victim recovery steps.

**FP risk:** N/A for advisory. File detection carries low FP risk since API key format is distinctive.

**Disposition:** Advisory in recovery guidance (already partially present); expand to explicit check with actionable link.

---

**G.7 — Telegram Desktop Session Detection**

**Signal:** Report presence of `%AppData%\Roaming\Telegram Desktop\tdata\` as an exposure surface, similar to how Discord and Steam exposure is currently reported.

**Why it matters:** `[CONFIRMED]` Vidar, Vidar 2.0, ACR Stealer, and most major stealer families explicitly target Telegram Desktop session data. The Telegram `tdata` directory contains session authentication state that allows account access without a password. Currently not reported in EXPOSURE_DIRS or SESSION_RESET_APPS.

**FP risk:** None for exposure reporting.

**Disposition:** Add to EXPOSURE_DIRS for reporting. Consider adding to SESSION_RESET_APPS for ACCOUNT LOCKDOWN (Telegram Desktop tdata session clearance).

---

**G.8 — Raw IP Download Pattern in Startup Scripts**

**Signal:** Startup scripts or scheduled task execute arguments containing a raw IPv4 address in an HTTP URL (e.g., `http://45.146.87.17/load`), especially combined with PowerShell download-execute tokens.

**Why it matters:** `[COMMUNITY]` April 2026 FRST thread: victim described startup PowerShell pulling from `45.146.87.17/load` — a raw IP download pattern used by rebuilder/dropper persistence. Raw IPs in download URLs are unusual in legitimate software and indicate operator-controlled infrastructure.

**FP risk:** Low. Legitimate software rarely specifies raw IPs in startup launch arguments.

**Current coverage:** IPV4_HTTP_REGEX and STARTUP_DOWNLOADER_TOKENS exist. The specific combination of an IP URL in a startup context needs to be scored as a standalone signal, not just as a corroboration marker.

**Disposition:** Score as `Startup Persistence Artifact` HIGH when raw IP URL appears in startup command arguments with download tokens. CRITICAL if IP matches known-bad list.

---

**G.9 — Cryptocurrency Wallet Paths in Exposure Reporting**

**Signal:** Check for presence of common cryptocurrency wallet data directories and include in exposure report:
- `%AppData%\Roaming\MetaMask\`
- `%AppData%\Local\Packages\*MetaMask*\`
- `%AppData%\Roaming\Exodus\`
- `%AppData%\Roaming\atomic\`
- `%AppData%\Local\Ledger Live\`
- Extension IDs for MetaMask, Exodus Web3 Wallet, etc. in browser extension directories

**Why it matters:** `[CONFIRMED]` ACR Stealer, Vidar, Lumma, Remus all explicitly target cryptocurrency wallet data. Including wallets in the exposure report helps victims understand the full scope of what the stealer could access.

**FP risk:** None for exposure reporting.

**Disposition:** Exposure report only — add to `_note_exposure()` calls alongside browser and Steam exposure.

---

**G.10 — HKCU\Software\Beep Fingerprinting Key**

**Signal:** Check for the presence of `HKCU\Software\Beep\{UUID}` registry key, which is used by the Powercat infostealer and similar families as a device fingerprint anchor.

**Why it matters:** `[CONFIRMED]` ThreatLocker Powercat analysis Feb 2026: `HKEY_CURRENT_USER\Software\Beep\{Unique_ID}` is created as a device fingerprint to correlate infection stages. This is a low-noise, specific signal.

**FP risk:** Very low. `HKCU\Software\Beep` is not a legitimate Windows key.

**Disposition:** Auto-remediate (Registry Persistence) when found in context of other campaign hits; review-first as standalone.

---

**G.11 — FileZilla / FTP Credential Exposure**

**Signal:** Report presence of `%AppData%\Roaming\FileZilla\recentservers.xml` and `sitemanager.xml` as exposure surfaces.

**Why it matters:** `[CONFIRMED]` Vidar 2.0, ACR Stealer target FTP/SSH credentials and specifically FileZilla. FileZilla stores saved server credentials including passwords in plaintext XML. If present, these were likely exfiltrated.

**FP risk:** None for exposure reporting.

**Disposition:** Exposure report advisory.

---

**G.12 — Discord Webhook C2 Exfiltration Pattern**

**Signal:** Processes (not `discord.exe`) making HTTPS requests to `discord.com/api/webhooks/*` endpoints.

**Why it matters:** `[CONFIRMED]` Malwarebytes Jan 2025: some stealers (Nova Stealer, others) use Discord webhook URLs as C2 exfiltration endpoints — data is POSTed directly to an attacker-controlled webhook and appears in a Discord channel. This is a cheap, resilient exfiltration channel.

**FP risk:** Low-medium. Some legitimate apps use webhooks for notifications. Key discriminator: the process making the webhook call should not be Discord itself and should be launched from a suspicious path.

**Disposition:** Review-first. CRITICAL if originating process is in a user-writable staging location.

---

**G.13 — Startup Persistence Reappearance Scoring**

**Signal:** Currently `compare_post_cleanup_persistence()` exists and compares pre/post cleanup startup state. Improve this by: (a) comparing against the pre-cleanup snapshot after every reboot, not just the immediate post-cleanup scan; (b) scoring a `suspicious_reappeared` finding as CRITICAL rather than INFO, since reappearance after cleanup is one of the strongest infection-still-active signals possible.

**Why it matters:** `[COMMUNITY]` FRST helpers repeat scans until persistence stops reappearing. The reappearance pattern is the clearest signal that cleanup was incomplete. RenKill has the infrastructure for this but currently does not treat reappearance findings with appropriate severity.

**Disposition:** Elevate reappeared suspicious startup entries to CRITICAL in post-cleanup scan mode.

---

**G.14 — ClickFix Windows Terminal (Win+X) Variant Detection**

**Signal:** RunMRU and PowerShell history currently check for `powershell` and `cmd.exe` invocations. Add detection for Windows Terminal (`wt.exe`) as a ClickFix execution shell — the Microsoft Threat Intel team documented a ClickFix variant using Windows Terminal instead of the Run dialog.

**Why it matters:** `[CONFIRMED]` Microsoft Security Blog Feb 2026: attacker replaced Run dialog with Windows Terminal for ClickFix command delivery. `wt.exe` is already in `CLICKFIX_SHELL_MARKERS` but may not be checked in history/MRU scanning paths.

**Disposition:** Verify `wt.exe` is included in the RunMRU and history scan pass. Review-first.

---

**G.15 — VPN Client Credential Exposure**

**Signal:** Report presence of NordVPN, Mullvad, OpenVPN config directories as exposure surfaces.

**Why it matters:** `[CONFIRMED]` ClickFix infostealer (CyberProof Feb 2026): explicitly targets NordVPN and Mullvad credential/config files. VPN configurations may contain credentials or private keys that grant network access.

**Disposition:** Exposure report advisory only.

---

## H. False Positive Traps

RenKill has good FP suppression but these are the areas where new detection additions need care.

### H.1 Windows and AppX Noise

- **AppX capability firewall rules** (`corenet-`, `remoteassistance-`, `netdis-`, `wifidirect-`, `dial-protocol-server-`, `allow-allcapabilities`, `allow-servercapability`) — RenKill already suppresses these. Any new firewall detection additions must also check against BENIGN_FIREWALL_RULE_PREFIXES and BENIGN_FIREWALL_RULE_TOKENS.

- **Windows Store app EXEs** running from `%LocalAppData%\Microsoft\WindowsApps\` — these are AppX package executables; paths containing `\WindowsApps\` should not be flagged as user-writable staging. RenKill already has BENIGN_FIREWALL_PROGRAM_ROOT_TOKENS for this.

- **WMI subscriptions from management tools** — some legitimate enterprise management tools use WMI subscriptions. In consumer contexts this is rare, but be aware.

### H.2 Legitimate Updater Flows

- **Active Setup** — Chrome, Edge, Brave, and Opera all use Active Setup with `--configure-user-settings`, `--system-level` arguments. RenKill already suppresses BENIGN_ACTIVE_SETUP_SWITCHES. Do not expand Active Setup auto-remediation without carefully checking against these patterns.

- **OneDrive** — OneDrive runs from `%LocalAppData%\Microsoft\OneDrive\` and uses Active Setup, Run keys, and startup entries. BENIGN_HEAVY_SUBTREES already covers the OneDrive path.

- **Discord updater** — Discord's update mechanism creates and removes files in `%AppData%\Roaming\Discord\` and `%AppData%\Local\Discord\`. Do not auto-flag temp files in the Discord local/roaming paths unless they match specific campaign signatures.

### H.3 Browser-Related FP Traps

- **Chrome/Edge/Brave update EXEs in user profiles** — `GoogleUpdate.exe`, `MicrosoftEdgeUpdate.exe`, `BraveUpdate.exe` run from user-profile subdirectories. TRUSTED_VENDOR_PATH_MARKERS covers the application paths.

- **Legitimate browser extension unpacked states** — developers working on browser extensions run unpacked extensions from local directories; these have unusual update URL states. The key discriminator is that developer extension paths typically live inside a project folder with `.git`, `package.json`, etc. PROJECT_INDICATOR_BASENAMES and PROJECT_INDICATOR_SUFFIXES already provide this context.

- **Browser policy set by enterprise MDM** — in enterprise/school/work environments, Group Policy legitimately sets browser policies. Report-only is the right disposition; never auto-remove browser policy keys.

- **Impersonated extension names + official update URLs** — `Google Docs` is a real extension with a legitimate extension ID (`mkaakpdehdafacodkgkpghoibnmamcme`). IMPERSONATED_EXTENSION_NAMES detection must check that the update URL is non-official; a Google Docs extension with the real `clients2.google.com` update URL is legitimate.

### H.4 Legitimate Steam/Game/Mod Artifacts

- **Steam game launch options** — Steam games can put arbitrary strings in their launch parameters; don't flag Steam's own game executable invocations.

- **Real Ren'Py games** — legitimate Ren'Py games have `data/`, `lib/`, `renpy/` folders. The discriminator is the presence of `Instaler.exe` specifically (or `archive.rpa` + `script.rpyc` in the same bundle). A `renpy/` tree without an `Instaler.exe` is probably just a real game.

- **Reshade** — RenKill already has `reshade` in BENIGN_TEMP_STAGE_DIR_BASENAMES. Reshade creates temp directories that look like staging dirs but are benign. Other GPU overlay tools (e.g., MSI Afterburner's RTSS) may create similar patterns.

- **Python from the Python Software Foundation** — `python.exe`, `pythonw.exe` signed by Python Software Foundation are already in PYTHON_COMPANY_TOKENS for exclusion. The fake Ren'Py bundle ships its own Python interpreter but it carries either no signature or a fake/stolen one.

### H.5 Build and Dev Artifacts

- **csc.exe invocations from MSBuild/Visual Studio** — when adding csc.exe compile-stage detection (G.4 above), exclude invocations where the argument path points into a known project directory (PROJECT_INDICATOR_BASENAMES/SUFFIXES signal) or a Visual Studio temp path (`%LOCALAPPDATA%\Temp\*\CSC*`, `%TEMP%\*\Microsoft.Build*`).

- **Local build processes for RenKill itself** — LOCAL_TOOL_CONTEXT_MARKERS and LOCAL_TOOL_TEMP_PREFIXES already handle `_mei` PyInstaller temp dirs and `renkill-update-*` temp dirs. If adding new detection patterns, keep verifying against `_is_local_tool_context()`.

### H.6 iMyFone / Third-Party Software

- **iMyFone technology is a real company** — they make iPhone management tools. "Shenzhen iMyFone Technology Co., Ltd" in file metadata is not inherently malicious. The suspicious signal is the specific combination: iMyFone-signed EXE in a startup persistence location with no corresponding legitimate install. Check for this combination rather than flagging the company name alone.

---

## I. Cleanup / Remediation Opportunities

### I.1 Remove the Creator, Not Just the Residue

The most common cleanup failure mode is removing the temp-stage artifacts (the extracted staging files) without removing the persistence that recreates them. Order of operations matters:

**Correct cleanup order:**
1. Kill active malicious processes first (stops new file writes and network activity)
2. Delete/quarantine persistence mechanisms (scheduled tasks, autoruns, startup shortcuts, WMI subscriptions, services) — the things that will re-launch the payload
3. Delete/quarantine the payload files themselves (staging directories, persistence staging files)
4. Delete/quarantine the source lure artifacts (the original ZIP/EXE that started the chain)
5. Repair protection posture (Defender exclusions, proxy, firewall rules)
6. Clear browser sessions
7. Reboot
8. Re-scan to verify persistence did not reappear

RenKill's `_run_remediation_bucket()` processes threats in severity order (CRITICAL → HIGH → MEDIUM → INFO), which approximately respects this ordering. The post-cleanup comparison logic is designed for step 8. This is correct.

**Key gap:** Step 4 (source lure artifact removal) is currently scored as `Source Lure Artifact` — review-first. This is appropriate because the "source" might be a file the user wants to examine. However, if other strong campaign IOCs are confirmed, the source lure should be auto-promoted to removable.

### I.2 Persistence-Breaking Order of Operations

- Kill processes before deleting the files they have open — otherwise file deletion may fail with "access denied" or the files may be recreated
- Disable scheduled tasks before deleting them — `schtasks /change /disable` before `/delete` reduces race conditions where the task fires mid-cleanup
- Remove startup entries before rebooting — if a startup entry points at a file that's being quarantined, removing the startup entry first prevents a "missing file at next boot" error that some persistence mechanisms use to rebuild
- For WMI subscriptions, the filter, consumer, and binding all need to be removed — removing only the consumer leaves orphaned filter/binding entries that FRST helpers will flag

### I.3 Quarantine Safety

Current quarantine approach is good (move-based, recovery manifest). Things to watch:
- `attrib +r +h +s` on quarantine items is correct but may need `subprocess.run` error handling — on paths with deeply nested files, attrib may fail on individual items
- The QUARANTINE_INERT_SUFFIX rename is a good safety measure but could be supplemented by a brief delay after process kill to ensure file handles are released before moving
- Long file paths (>260 chars) in quarantine can cause issues; adding `\\?\` prefix to paths >250 chars in the quarantine move would prevent this edge case

### I.4 Post-Clean Reboot/Rescan Logic

Currently implemented. Improvements:
- Add explicit UI guidance in the post-cleanup UI showing time since last reboot (if scan state indicates a reboot has not occurred since cleanup, prompt strongly)
- The `compare_post_cleanup_persistence()` result should be shown prominently as a CLEAN / NEEDS ATTENTION banner, not buried in the findings list
- If suspicious entries reappear, automatically elevate to CRITICAL and show a "persistence reappeared after cleanup" banner — this is the most important post-cleanup signal

### I.5 Browser Aftermath Cleanup

**Current ACCOUNT LOCKDOWN is comprehensive.** Potential improvements:
- Add explicit Telegram Desktop tdata session clearance (see G.7)
- For Chromium browsers in ACCOUNT LOCKDOWN: also clear `Login Data` and `Web Data` (saved passwords and autofill) since these were likely exfiltrated and should be treated as compromised
- After session clearing, include UI guidance to use browser sync password/passphrase reset (Google Sync, etc.) to invalidate any synced session state

### I.6 Account Lockdown Improvements

- Add explicit recovery step language to the UI for Steam Web API key revocation (currently partial coverage)
- Surface the "email account first" priority more prominently in the recovery guidance — currently in README and RESEARCH notes but should be in the in-app recovery panel
- Add guidance on checking for browser extension sync state — if Chrome Sync is active, malicious extensions can re-sync after manual removal; users need to turn off sync, clean extensions, then re-enable sync with fresh auth

### I.7 Protection Repair Improvements

- After REPAIR DEFAULTS, explicitly re-enable Defender real-time monitoring if it was disabled by malware policy
- Check whether Windows Security Center health service is running — some infections tamper with `wscsvc`
- Re-register Windows Security Center WMI providers if Defender protection state is showing as unknown after repair

### I.8 When Not to Delete Automatically

- **Never auto-delete files in `Program Files` or `Windows` paths** — already protected by PROTECTED_SYSTEM_PATH_MARKERS
- **Never auto-delete running security tool processes** — already protected by PROTECTED_SECURITY_PROCESS_NAMES
- **Never auto-delete firewall rules that protect security software** — BENIGN_FIREWALL_RULE_TOKENS covers WinDefend
- **Never auto-delete based on a standalone generic path marker** — only auto-remediate when the category is in FILE_REMEDIATION_CATEGORIES and the finding was derived from specific IOC matching
- **Review-first for anything in `%ProgramData%` that does not match a specific campaign IOC** — ProgramData has many legitimate applications
- **Review-first for all browser policy and extension state** — these can affect machine function significantly and enterprise-set policies should not be removed without confirmation

---

## J. Concrete Roadmap — 20 Items, Ordered by Value

These are implementation-oriented. Not marketing. No fluff.

---

**J.1 — Telegram Desktop Exposure + ACCOUNT LOCKDOWN coverage**
*Priority: HIGH | Effort: Low*

Add `Telegram Desktop` to `EXPOSURE_DIRS` and optionally to `SESSION_RESET_APPS`. The tdata directory contains session auth that stealers specifically target. This is a gap in exposure reporting that affects a significant fraction of victims.

---

**J.2 — File Creation Timestamp Corroboration**
*Priority: HIGH | Effort: Medium*

When flagging suspicious files, include `os.path.getctime()` / `os.path.getmtime()` in the finding. Add logic to boost confidence score when multiple flagged artifacts share creation timestamps within a short window. Expose creation timestamps in the findings display.

---

**J.3 — Firefox Extension Manifest Reader**
*Priority: HIGH | Effort: Medium*

Read `%AppData%\Roaming\Mozilla\Firefox\Profiles\*\extensions.json` and enumerate installed extensions. Apply same flagging logic as Chromium reader: non-official update URLs, impersonated names, risky permissions. Firefox is in EXPOSURE_DIRS already; extension review parity is the natural next step.

---

**J.4 — Startup Reappearance Severity Escalation**
*Priority: HIGH | Effort: Low*

In post-cleanup scan mode, when `compare_post_cleanup_persistence()` finds `suspicious_reappeared > 0`, emit those findings as CRITICAL (not INFO) and show a banner in the UI: "Persistence rebuilt after cleanup — infection may still be active." This is the single most important signal for "the job isn't done."

---

**J.5 — csc.exe Compile-Stage Process Detection**
*Priority: HIGH | Effort: Low*

Add `csc.exe` invoked with `@"%TEMP%\<random>\<random>.cmdline"` argument pattern to process detection. Currently the temp directory artifacts are detected but the process invocation that creates them is not. Score as `Compiler Stage Process` CRITICAL. Exclude MSBuild temp paths.

---

**J.6 — Raw IP in Startup Command Auto-Scoring**
*Priority: HIGH | Effort: Low*

In the startup scan, when a command contains an HTTP URL with a raw IPv4 address AND download tokens (PowerShell download, curl, mshta), score the finding as `Startup Persistence Artifact` HIGH rather than just a corroboration signal. The specific pattern `http://<ip>/load` or `http://<ip>/<path>` in a startup context has essentially no legitimate use.

---

**J.7 — HKCU\Software\Beep Fingerprint Key Detection**
*Priority: MEDIUM | Effort: Very Low*

Add `HKCU\Software\Beep` to the registry scan pass. Any value under this key is a stealer fingerprint artifact. Trivial to add, very low FP risk, removes a specific artifact left by Powercat-family infostealers.

---

**J.8 — Cryptocurrency Wallet Exposure Reporting**
*Priority: MEDIUM | Effort: Low*

Add MetaMask, Exodus, Atomic, Ledger Live directories to `_note_exposure()` calls in the exposure scan. No remediation needed — reporting only. Helps users understand the full scope of what was at risk.

---

**J.9 — EtherHiding / Ethereum RPC Detection**
*Priority: MEDIUM | Effort: Medium*

Add network connection monitoring for non-browser processes connecting to known Ethereum RPC endpoints (infura.io, eth.llamarpc.com, cloudflare-eth.com, etc.). Flag as `Active C2 Connection` review-first when originating process is in a user-writable location. Covers Remus and future EtherHiding-based families.

---

**J.10 — Steam Web API Key Recovery Guidance**
*Priority: MEDIUM | Effort: Low*

Add explicit Steam Web API key revocation step to the in-app recovery guidance panel. Include the direct URL (`steamcommunity.com/dev/apikey`). This is a common gap in victim recovery that allows trade/inventory manipulation to continue after password changes.

---

**J.11 — Discord Webhook Exfiltration Detection**
*Priority: MEDIUM | Effort: Medium*

Monitor active TCP connections for non-Discord processes connecting to `discord.com:443` with process path in user-writable locations. This catches stealers using Discord webhooks as C2 exfiltration. Score as `Active C2 Connection` HIGH when originating process is suspicious.

---

**J.12 — FileZilla + VPN Credential Exposure Reporting**
*Priority: MEDIUM | Effort: Very Low*

Add to `_note_exposure()`:
- `%AppData%\Roaming\FileZilla\recentservers.xml` (FTP server credentials)
- `%AppData%\Roaming\FileZilla\sitemanager.xml`
- NordVPN config directory
- OpenVPN config directory

Zero cleanup needed — exposure report only.

---

**J.13 — Disable-Then-Delete for Scheduled Tasks**
*Priority: MEDIUM | Effort: Low*

Before deleting a scheduled task, add `schtasks /change /tn <name> /disable` as a prior step. Reduces the race where the task fires during cleanup. Minor code change to `_capture_task_xml()` and the task deletion action.

---

**J.14 — Quarantine Long Path Safety**
*Priority: MEDIUM | Effort: Low*

In `_try_move_path_to_recovery()`, prepend `\\?\` to source and destination paths when either exceeds 250 characters. Prevents `shutil.move` failures on deeply nested staging directories (common when paths are under `%AppData%\Roaming\Godot\app_userdata\<long_id>\`).

---

**J.15 — Post-Cleanup UI Prominence Improvements**
*Priority: MEDIUM | Effort: Medium*

Redesign the post-cleanup scan result presentation:
- Show a large CLEAN / ATTENTION NEEDED banner at the top based on `compare_post_cleanup_persistence()` result
- List reappeared suspicious entries prominently as CRITICAL
- Include "time since cleanup" and "has machine rebooted?" status

---

**J.16 — Browser Sync Disable Advisory in ACCOUNT LOCKDOWN**
*Priority: MEDIUM | Effort: Low*

In the ACCOUNT LOCKDOWN UI, add explicit advisory text: "If Chrome Sync is enabled, also disable sync, clear synced data from Google's servers, then re-enable sync after cleanup. Otherwise removed extensions may re-sync automatically."

---

**J.17 — Login Data / Web Data Clearance in ACCOUNT LOCKDOWN**
*Priority: MEDIUM | Effort: Low*

Add `Login Data`, `Web Data`, `Bookmarks`, and `History` to the Chromium ACCOUNT LOCKDOWN session clear list (currently clears cookies, cache, sessions, extension state). Saved passwords and autofill data were likely exfiltrated; they should be treated as compromised and cleared to prevent stale re-use.

---

**J.18 — "Email Account First" Recovery Banner**
*Priority: MEDIUM | Effort: Very Low*

In the recovery guidance displayed after ACCOUNT LOCKDOWN, show the following at the top in large/prominent text:

> ⚠️ STEP 0 (DO FIRST, ON A DIFFERENT DEVICE): Change your email account password and revoke all email sessions before changing Steam, Discord, or any other passwords. If your email is compromised, all other password changes can be undone by the attacker.

Currently this guidance is in the README and research notes but not prominently in the in-app flow where victims need it most.

---

**J.19 — Vidar 2.0 / Remus C2 Resolver Strings in PROCESS_IOC_MARKERS**
*Priority: LOW | Effort: Very Low*

Add the following strings to PROCESS_IOC_MARKERS or a dedicated `DEAD_DROP_DOMAINS` set, used to check startup scripts and command history for references to known dead-drop infrastructure:
- `t.me/` (Telegram) — already partially in SCRIPT_LURE_REMOTE_MARKERS
- `telegra.ph/` (Telegram Telegraph, used for C2 storage)
- `docs.google.com/forms/` (Google Forms dead drop)
- `docs.google.com/presentation/` (Google Slides dead drop)
- `steamcommunity.com/id/` (Steam profile dead drop)

Flag references to these in startup scripts, RunMRU, and PowerShell history as evidence of dead-drop resolver use.

---

**J.20 — Remus / EtherHiding IOC String Set**
*Priority: LOW | Effort: Low*

Add Remus-family indicators to process and file IOC sets:
- Process: `remus` (as a path component or process name substring)
- File: check PROCESS_IOC_MARKERS for `etherhiding` / `ether_hiding` (current codename)
- Note in research docs that EtherHiding uses JSON-RPC calls to Ethereum endpoints — document specific RPC method signatures (`eth_call` with contract address targeting) that distinguish stealer C2 calls from legitimate blockchain apps if this detection is ever built into a network layer

---

## Source Links

All sources consulted or cited in this document:

**Primary Research (Confirmed):**
- Cyderes Howler Cell, "RenEngine Loader and HijackLoader: Dual-Stage Attack Chain Fueling Stealer Campaigns" (2026-02-04): https://www.cyderes.com/howler-cell/renengine-loader-hijackloader-attack-chain
- Kaspersky Securelist, "Active malicious campaign with the RenEngine loader" (2026-02-11): https://securelist.com/renengine-campaign-with-hijackloader-lumma-and-acr-stealer/118891/
- Kaspersky Press Release, "Kaspersky identifies RenEngine loader distributed through pirated games and software" (2026-02-23): https://me-en.kaspersky.com/about/press-releases/kaspersky-identifies-renengine-loader-distributed-through-pirated-games-and-software
- AhnLab ASEC, "February 2026 Infostealer Trend Report" (2026-03-11): https://asec.ahnlab.com/en/92902/
- Microsoft Security Intelligence, "Trojan:Win32/Amatera.A!AMTB" (2026-02-05): https://www.microsoft.com/en-us/wdsi/threats/malware-encyclopedia-description?Name=Trojan%3AWin32%2FAmatera.A%21AMTB
- Microsoft Security Blog, "Think before you Click(Fix)" (2025-08-21): https://www.microsoft.com/en-us/security/blog/2025/08/21/think-before-you-clickfix-analyzing-the-clickfix-social-engineering-technique/
- Hybrid Analysis, "Pragmata_Trainer.exe" (accessed 2026-04-30): https://hybrid-analysis.com/sample/8ade9f572270406bf61ac260e9c5b7abfa2d9a6f8eb7d849d8fa8464990d9665/
- Malwarebytes, "Can you try a game I made?" (2025-01-03): https://www.malwarebytes.com/blog/news/2025/01/can-you-try-a-game-i-made-fake-game-sites-lead-to-information-stealers
- Bitdefender, "The Fake Game Playtest Scam Explained" (2026-03-30): https://www.bitdefender.com/en-us/blog/hotforsecurity/fake-game-playtest-scam
- BleepingComputer, "Hacker sneaks infostealer malware into early access Steam game" (2025-07-24): https://www.bleepingcomputer.com/news/security/hacker-sneaks-infostealer-malware-into-early-access-steam-game/
- SentinelOne, "How ClickFix is Weaponizing Verification Fatigue" (2025-05-22): https://www.sentinelone.com/blog/how-clickfix-is-weaponizing-verification-fatigue-to-deliver-rats-infostealers/
- Acronis TRU, "New Vidar 2.0 Infostealer Spreads via Fake Game Cheats on GitHub, Reddit" (2026-03-17)
- Gen Digital / socprime, "Remus 64-bit Stealer: Lumma Successor Using EtherHiding" (2026-04): https://socprime.com/active-threats/remus-unpacking-the-64-bit-evolution-of-the-lumma-stealer/
- ThreatLocker, "Powercat malware campaign" (2026-03-26): https://www.threatlocker.com/blog/powercat-malware-campaign-fake-game-cheats-deliver-infostealer-targeting-discord-roblox-and-crypto-wallets
- Rapid7 / CSO Online, "ClickFix techniques evolve in new infostealer campaigns" (2026-03-16): https://www.csoonline.com/article/4145123/clickfix-techniques-evolve-in-new-infostealer-campaigns.html
- CyberProof/GBHackers, "ClickFix Infostealer Spreads via Fake CAPTCHA Traps" (2026-02-26): https://gbhackers.com/clickfix-infostealer/
- Webz.io, "Acreed Infostealer in 2026" (2026-03-20): https://webz.io/dwp/acreed-infostealer-everything-we-know-so-far/
- CyberArk, "Crumbled Security: Unmasking the Cookie-Stealing Malware Threat" (2025-01-16): https://www.cyberark.com/resources/threat-research-blog/crumbled-security-unmasking-the-cookie-stealing-malware-threat
- Infosecurity Magazine, "New Infostealer Campaign Uses Discord Videogame Lure" (2025-01-06): https://www.infosecurity-magazine.com/news/infostealer-campaign-discord/
- AhnLab ASEC / The Hacker News, "New Malware Campaign Uses Cracked Software" (2025-02-24): https://thehackernews.com/2025/02/new-malware-campaign-uses-cracked.html
- BleepingComputer, "FRST Tutorial" (updated 2025-09-11): https://www.bleepingcomputer.com/forums/t/781976/frst-tutorial-how-to-use-farbar-recovery-scan-tool/

**Community Sources (Reddit, FRST cleanup threads):**
- Reddit r/computerviruses — multiple April 2026 threads on Ren'Py instaler cleanup
- Reddit FRST cleanup threads showing iMyFone metadata, Godot app_userdata staging, raw IP download patterns

**Platform Security Guidance:**
- Discord Support, "My Discord Account was Hacked or Compromised": https://support.discord.com/hc/en-us/articles/24160905919511
- Valve Steam Support, stolen account guidance
- Google Account Help, device session review: https://support.google.com/accounts/answer/3067630
- Microsoft Defender Offline guidance: https://support.microsoft.com/en-us/windows/help-protect-my-pc-with-microsoft-defender-offline-9306d528-64bf-4668-5b80-ff533f183d6c

---

*Brief authored 2026-05-02. Reflects RenKill v1.5.4 codebase state. All code claims directly verified against renkill.py, reninspect.py, RESEARCH_RENENGINE_2026.md, README.md, and CHANGELOG.md.*
