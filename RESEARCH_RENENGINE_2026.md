# RenEngine / "RenLoader" Research Notes

Last updated: 2026-04-17

## Bottom line

What victims are calling "RenLoader" or the "Ren'Py `Instaler.exe` virus" matches current reporting on the `RenEngine Loader` campaign. The packaging in your screenshot is consistent with the Ren'Py launcher abuse described by Cyderes and Kaspersky: a small archive containing `Instaler.exe` plus `data`, `lib`, and `renpy` folders, with the real malicious logic hidden in `archive.rpa` and `script.rpyc`.

## What the campaign does

- Stage 1: Abuse a legitimate Ren'Py launcher (`Instaler.exe`) to execute a malicious compiled Python script from `archive.rpa`.
- Stage 2: Decrypt and hand off execution to HijackLoader.
- Stage 3: Establish persistence using `broker_crypt_v4_i386` directories and dropped loader files.
- Final payload: usually ACR Stealer, but Cyderes also observed Rhadamanthys, AsyncRAT, and XWorm in similar chains.

## Additional stage files seen in reporting

Kaspersky's February 11, 2026 write-up adds another useful layer for defenders. In one infection path, the malicious "game" unpacked a hidden `.temp` directory containing:

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

Those names are not all globally unique on every system, so they are strongest when found in `%TEMP%`, hidden `.temp` folders, or alongside the RenEngine/HijackLoader chain.

## High-confidence artifacts for RenKill to hunt

### Initial bundle

- `Instaler.exe`
- `archive.rpa`
- `script.rpyc`
- Ren'Py-style folder trio: `data`, `lib`, `renpy`
- Temp `.key` files used to decode the next stage

### Persistence-stage artifacts

- `%ProgramData%\broker_crypt_v4_i386\`
- `%ProgramData%\broker_crypt_v4_i386\d3dx9_43.dll`
- `%ProgramData%\broker_crypt_v4_i386\Froodjurain.wkk`
- `%ProgramData%\broker_crypt_v4_i386\Taig.gr`
- `%ProgramData%\broker_crypt_v4_i386\VSDebugScriptAgent170.dll`
- `%AppData%\Roaming\broker_crypt_v4_i386\chime.exe`
- `%AppData%\Local\ZoneInd.exe`
- Desktop `.lnk` shortcuts pointing at the above persistence chain

### Exact sample hashes from Cyderes

- ZIP package SHA256: `9e3b296339e25b1bae1f9d028a17f030dcf2ab25ad46221b37731ea4fdfde057`
- `Instaler.exe` SHA256: `7123e1514b939b165985560057fe3c761440a9fff9783a3b84e861fd2888d4ab`
- `d3dx9_43.dll` SHA256: `326ec5aeeafc4c31c234146dc604a849f20f1445e2f973466682cb33889b4e4c`
- `VSDebugScriptAgent170.dll` SHA256: `db4ccd0e8f03c6d282726bfb4ee9aa15aa41e7a5edcb49e13fbd0001452cdfa2`

## Why victims lose Discord even with 2FA

The payload families in this ecosystem steal browser credentials, cookies, auth tokens, wallet data, and session material. That means password changes alone are not enough. Session revocation is mandatory because stolen cookies can preserve access after 2FA.

## Notable behavioral signs

- "Game" installer does little or nothing visible.
- Browser sessions or Discord sessions get hijacked shortly after execution.
- Discord account starts sending spam, often fake MrBeast crypto/casino messages.
- Temp, AppData, and ProgramData receive randomly named executables or the `broker_crypt_v4_i386` persistence set.

## Recovery implications

- File cleanup helps stop reinfection and persistence.
- It does **not** undo stolen credentials, stolen cookies, or wallet compromise.
- Incident response still needs password resets from a clean device, session revocation, Discord authorized-app review, and possibly a full OS reinstall if trust is lost.

## Concrete remediation for already-infected users

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
- Malwarebytes, "Can you try a game I made? Fake game sites lead to information stealers" (2025-01-03): https://www.malwarebytes.com/it/blog/news/2025/01/can-you-try-a-game-i-made-fake-game-sites-lead-to-information-stealers
- Malwarebytes, "Can you test my game? Fake itch.io pages spread hidden malware to gamers" (2025-10-24): https://www.malwarebytes.com/blog/threat-intel/2025/10/can-you-test-my-game-fake-itch-io-pages-spread-hidden-malware-to-gamers
- Discord Support, "My Discord Account was Hacked or Compromised" (accessed 2026-04-17): https://support.discord.com/hc/en-us/articles/24160905919511-My-Discord-Account-was-Hacked-or-Compromised
- Discord Safety, "Tips to Prevent Spam and Hacking" (accessed 2026-04-17): https://discord.com/safety/360044104071-Tips-against-spam-and-hacking
- Google Account Help, "See devices with account access" (accessed 2026-04-17): https://support.google.com/accounts/answer/3067630?hl=en
- Google Chrome Help, "Sign in and sync in Chrome" (accessed 2026-04-17): https://support.google.com/chrome/answer/185277?hl=en
- Microsoft Support, "Virus and Threat Protection in the Windows Security App" (accessed 2026-04-17): https://support.microsoft.com/en-us/windows/help-protect-my-pc-with-microsoft-defender-offline-9306d528-64bf-4668-5b80-ff533f183d6c
