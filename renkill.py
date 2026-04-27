#!/usr/bin/env python3
"""RenKill.

Windows cleanup tool for the fake Ren'Py "Instaler.exe" / RenEngine loader chain.
"""

import os
import sys
import time
import shutil
import threading
import datetime
import subprocess
import ctypes
import hashlib
import json
import re
import base64
import csv
import tempfile
import traceback
import urllib.error
import urllib.request
import zipfile
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog

# Windows-only imports
try:
    import winreg
    WINREG_OK = True
except ImportError:
    WINREG_OK = False

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False


# IOC definitions

VERSION = "1.4.15"
TOOL_NAME = "RenKill"
UPDATE_REPO_OWNER = "CloudyCodez"
UPDATE_REPO_NAME = "RenKill"
UPDATE_API_URL = f"https://api.github.com/repos/{UPDATE_REPO_OWNER}/{UPDATE_REPO_NAME}/releases/latest"
UPDATE_RELEASES_URL = f"https://github.com/{UPDATE_REPO_OWNER}/{UPDATE_REPO_NAME}/releases"
UPDATE_ASSET_SUFFIX = "-windows.zip"
UPDATE_STATE_FILE = "update_state.txt"

MALICIOUS_FILENAMES = {
    "instaler.exe",
    "instaler.py",
    "instaler.pyo",
    "instaler.pyc",
    "lnstaier.exe",
    "iviewers.dll",
    "script.rpyc",
    "archive.rpa",
}

RENENGINE_FOLDER_SET = {"renpy", "data", "lib"}

CAMPAIGN_DIR_MARKERS = {
    "broker_crypt_v4_i386",
}

CAMPAIGN_FILENAMES = {
    "froodjurain.wkk",
    "taig.gr",
    "vsdebugscriptagent170.dll",
    "chime.exe",
    "zoneind.exe",
    "d3dx9_43.dll",
}

CAMPAIGN_PROCESS_NAMES = {
    "instaler.exe",
    "lnstaier.exe",
    "chime.exe",
    "zoneind.exe",
    "w8cpbgqi.exe",
    "dksyvguj.exe",
}

PROCESS_IOC_MARKERS = {
    "broker_crypt_v4_i386",
    "froodjurain",
    "taig.gr",
    "vsdebugscriptagent170",
    "iviewers.dll",
    "archive.rpa",
    "script.rpyc",
    "instaler",
    "lnstaier",
    "renpy",
    "acr",
    "acrstealer",
    "lumma",
    "rhadamanthys",
    "vidar",
    "doppelgang",
    "doppelganging",
    "cc32290mt.dll",
    "gayal.asp",
    "hap.eml",
    "w8cpbgqi.exe",
    "zt5qwyucfl.txt",
    "dksyvguj.exe",
    "dbghelp.dll",
    "pla.dll",
    "instsatp_",
    "t11_asm",
    "amatera",
    "amaterastealer",
    "antivmgpu",
    "antivmhypervisornames",
    "antivmmacs",
    "rshell",
    "esal",
    "modtask",
    "moduac",
}

SUSPICIOUS_DLL_NAMES = {
    "iviewers.dll",
    "vsdebugscriptagent170.dll",
    "d3dx9_43.dll",
    "cc32290mt.dll",
}

HIJACKLOADER_STAGE_FILES = {
    "dksyvguj.exe",
    "cc32290mt.dll",
    "gayal.asp",
    "hap.eml",
    "w8cpbgqi.exe",
    "zt5qwyucfl.txt",
}

LOADER_CONTAINER_DLLS = {
    "dbghelp.dll",
    "pla.dll",
    "borlndmm.dll",
    "cc32290mt.dll",
}

NETSUPPORT_STAGE_FILENAMES = {
    "client32.exe",
    "client32.ini",
    "client32u.ini",
    "nsm.lic",
    "htctl32.dll",
    "pcicl32.dll",
}

NETSUPPORT_TRUSTED_PATH_MARKERS = (
    "\\program files\\netsupport\\",
    "\\program files (x86)\\netsupport\\",
)

NETSUPPORT_SUSPICIOUS_PATH_MARKERS = (
    "\\appdata\\roaming\\microsoft\\updates\\local\\",
    "\\microsoft\\updates\\local\\",
)

NETSUPPORT_METADATA_TOKENS = (
    "netsupport ltd",
    "netsupport manager",
    "netsupport client application",
    "client32",
)

HIJACKLOADER_STAGE_DIR_SIGNATURES = (
    {"dksyvguj.exe", "cc32290mt.dll", "gayal.asp", "dbghelp.dll"},
    {"hap.eml", "pla.dll", "w8cpbgqi.exe", "zt5qwyucfl.txt"},
    {"w8cpbgqi.exe", "d3dx9_43.dll", "vsdebugscriptagent170.dll"},
)

KNOWN_SHA256_IOCS = {
    "9e3b296339e25b1bae1f9d028a17f030dcf2ab25ad46221b37731ea4fdfde057": "Cyderes sample malicious ZIP package",
    "7123e1514b939b165985560057fe3c761440a9fff9783a3b84e861fd2888d4ab": "Cyderes sample exploited Instaler.exe",
    "326ec5aeeafc4c31c234146dc604a849f20f1445e2f973466682cb33889b4e4c": "Cyderes sample d3dx9_43.dll",
    "db4ccd0e8f03c6d282726bfb4ee9aa15aa41e7a5edcb49e13fbd0001452cdfa2": "Cyderes sample VSDebugScriptAgent170.dll",
}

HASH_CANDIDATE_NAMES = {
    "instaler.exe",
    "d3dx9_43.dll",
    "vsdebugscriptagent170.dll",
}

MAX_IOC_HASH_BYTES = 200 * 1024 * 1024

BENIGN_HEAVY_SUBTREES = (
    "\\programdata\\smilegate\\",
    "\\programdata\\microsoft\\windows defender\\",
    "\\programdata\\package cache\\",
    "\\appdata\\local\\microsoft\\onedrive\\",
    "\\appdata\\local\\discord\\",
    "\\appdata\\local\\google\\chrome\\user data\\",
    "\\appdata\\local\\microsoft\\edge\\user data\\",
    "\\appdata\\local\\bravesoftware\\brave-browser\\user data\\",
    "\\appdata\\roaming\\mozilla\\firefox\\profiles\\",
)

USER_WRITABLE_DIR_MARKERS = (
    "\\appdata\\local\\temp\\",
    "\\temp\\",
    "\\tmp\\",
    "\\appdata\\roaming\\",
    "\\appdata\\local\\",
    "\\programdata\\",
    "\\downloads\\",
    "\\desktop\\",
    "\\documents\\",
)

SOURCE_LURE_KEYWORDS = {
    "renpy",
    "renengine",
    "renloader",
    "instaler",
    "lnstaier",
    "broker_crypt",
    "froodjurain",
    "zoneind",
    "chime",
    "iviewers",
    "acr",
    "acrstealer",
    "lumma",
    "rhadamanthys",
    "vidar",
    "crack",
    "cracked",
    "keygen",
    "repack",
    "mrbeast",
    "crypto",
    "dodi-repacks",
    "mediafire",
    "mega",
    "go.zovo",
    "coreldraw",
    "artistapirata",
    "awdescargas",
    "filedownloads",
    "gamesleech",
    "parapcc",
    "saglamindir",
    "zdescargas",
    "hentakugames",
}

SOURCE_LURE_FILENAME_STRONG = {
    "renpy",
    "renengine",
    "renloader",
    "instaler",
    "lnstaier",
    "broker_crypt",
    "froodjurain",
    "zoneind",
    "chime",
    "iviewers",
    "acrstealer",
    "lumma",
    "rhadamanthys",
    "vidar",
    "crack",
    "cracked",
    "keygen",
    "repack",
    "mrbeast",
    "crypto",
    "dodi-repacks",
    "mediafire",
    "mega",
    "go.zovo",
    "coreldraw",
}

GENERIC_LAUNCHER_KEYWORDS = (
    "activator",
    "crack",
    "fix",
    "install",
    "installer",
    "launcher",
    "loader",
    "patch",
    "repair",
    "setup",
    "unlock",
    "update",
)

RENPY_LAUNCHER_SCRIPT_EXTENSIONS = {".py", ".pyc", ".pyo"}
RENPY_PAYLOAD_INDICATOR_EXTENSIONS = {".key", ".rpa", ".rpyc"}

SOURCE_LURE_EXTENSIONS = {
    ".zip", ".rar", ".7z", ".iso", ".lnk", ".url", ".html", ".htm",
    ".bat", ".cmd", ".ps1", ".vbs", ".js", ".exe",
}

EXPOSURE_DIRS = (
    ("Discord", os.path.join("AppData", "Roaming", "Discord")),
    ("Chrome", os.path.join("AppData", "Local", "Google", "Chrome", "User Data")),
    ("Edge", os.path.join("AppData", "Local", "Microsoft", "Edge", "User Data")),
    ("Brave", os.path.join("AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data")),
    ("Opera", os.path.join("AppData", "Roaming", "Opera Software", "Opera Stable")),
    ("Firefox", os.path.join("AppData", "Roaming", "Mozilla", "Firefox", "Profiles")),
)

CHROMIUM_SESSION_SUBPATHS = (
    os.path.join("Network", "Cookies"),
    os.path.join("Network", "Cookies-journal"),
    "Cookies",
    "Sessions",
    "Session Storage",
    "Local Storage",
    "IndexedDB",
    "Service Worker",
    "WebStorage",
    "SharedStorage",
)

DISCORD_SESSION_SUBPATHS = (
    os.path.join("Network", "Cookies"),
    os.path.join("Network", "Cookies-journal"),
    "Cookies",
    "Local Storage",
    "Session Storage",
    "Cache",
    "Code Cache",
    "GPUCache",
    "Service Worker",
    "Partitions",
)

FIREFOX_SESSION_FILES = (
    "cookies.sqlite",
    "webappsstore.sqlite",
    "sessionstore.jsonlz4",
    "sessionCheckpoints.json",
)

FIREFOX_SESSION_DIRS = (
    "sessionstore-backups",
    os.path.join("storage", "default"),
    "cache2",
    "OfflineCache",
)

SESSION_RESET_APPS = (
    {
        "label": "Discord",
        "kind": "flat",
        "processes": {"discord.exe", "discordcanary.exe", "discordptb.exe"},
        "roots": (
            os.path.join("AppData", "Roaming", "Discord"),
            os.path.join("AppData", "Roaming", "discordcanary"),
            os.path.join("AppData", "Roaming", "discordptb"),
        ),
        "subpaths": DISCORD_SESSION_SUBPATHS,
    },
    {
        "label": "Chrome",
        "kind": "chromium",
        "processes": {"chrome.exe"},
        "roots": (os.path.join("AppData", "Local", "Google", "Chrome", "User Data"),),
    },
    {
        "label": "Edge",
        "kind": "chromium",
        "processes": {"msedge.exe"},
        "roots": (os.path.join("AppData", "Local", "Microsoft", "Edge", "User Data"),),
    },
    {
        "label": "Brave",
        "kind": "chromium",
        "processes": {"brave.exe"},
        "roots": (os.path.join("AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data"),),
    },
    {
        "label": "Opera",
        "kind": "flat",
        "processes": {"opera.exe"},
        "roots": (os.path.join("AppData", "Roaming", "Opera Software", "Opera Stable"),),
        "subpaths": CHROMIUM_SESSION_SUBPATHS,
    },
    {
        "label": "Firefox",
        "kind": "firefox",
        "processes": {"firefox.exe"},
        "roots": (os.path.join("AppData", "Roaming", "Mozilla", "Firefox", "Profiles"),),
    },
)

SAFE_PROCESS_NAMES = {
    "code.exe",
    "code - insiders.exe",
    "cmd.exe",
    "conhost.exe",
    "discord.exe",
    "explorer.exe",
    "firefox.exe",
    "git.exe",
    "msedge.exe",
    "notepad.exe",
    "opera.exe",
    "powershell.exe",
    "pwsh.exe",
    "python.exe",
    "pythonw.exe",
    "steam.exe",
    "taskmgr.exe",
    "wininit.exe",
    "winlogon.exe",
}

TRUSTED_PROCESS_NAMES = {
    "avastsvc.exe",
    "avastui.exe",
    "avgsvc.exe",
    "avgui.exe",
    "bdservicehost.exe",
    "brave.exe",
    "chrome.exe",
    "crashpad_handler.exe",
    "discordsystemhelper.exe",
    "ekrn.exe",
    "egui.exe",
    "launcherservice.exe",
    "mbam.exe",
    "mbamservice.exe",
    "mbamtray.exe",
    "mcshield.exe",
    "mfefire.exe",
    "mfemms.exe",
    "mpcmdrun.exe",
    "mpdefendercoreservice.exe",
    "msmpeng.exe",
    "nissrv.exe",
    "onedrive.exe",
    "savservice.exe",
    "sentinelagent.exe",
    "securityhealthservice.exe",
    "securityhealthsystray.exe",
    "smartscreen.exe",
    "sophoshealth.exe",
    "sophosui.exe",
    "steamservice.exe",
    "steamwebhelper.exe",
    "wrsa.exe",
    "avp.exe",
    "csfalconservice.exe",
}

PROTECTED_SECURITY_PROCESS_NAMES = {
    "avastsvc.exe",
    "avastui.exe",
    "avgsvc.exe",
    "avgui.exe",
    "bdservicehost.exe",
    "ekrn.exe",
    "egui.exe",
    "mbam.exe",
    "mbamservice.exe",
    "mbamtray.exe",
    "mcshield.exe",
    "mfefire.exe",
    "mfemms.exe",
    "msmpeng.exe",
    "mpdefendercoreservice.exe",
    "mpcmdrun.exe",
    "nissrv.exe",
    "savservice.exe",
    "securityhealthservice.exe",
    "securityhealthsystray.exe",
    "sentinelagent.exe",
    "smartscreen.exe",
    "sophoshealth.exe",
    "sophosui.exe",
    "wrsa.exe",
    "avp.exe",
    "csfalconservice.exe",
}

PROTECTED_CORE_PROCESS_NAMES = {
    "cmd.exe",
    "conhost.exe",
    "explorer.exe",
    "powershell.exe",
    "pwsh.exe",
    "taskmgr.exe",
    "wininit.exe",
    "winlogon.exe",
    "wscript.exe",
    "cscript.exe",
    "mshta.exe",
    "rundll32.exe",
}

TRUSTED_VENDOR_PATH_MARKERS = (
    "\\program files\\avast software\\",
    "\\programdata\\avast software\\",
    "\\program files\\avg\\",
    "\\programdata\\avg\\",
    "\\program files\\bitdefender\\",
    "\\programdata\\bitdefender\\",
    "\\program files\\crowdstrike\\",
    "\\programdata\\microsoft\\windows defender\\",
    "\\programdata\\microsoft\\windows defender advanced threat protection\\",
    "\\program files\\eset\\",
    "\\programdata\\eset\\",
    "\\program files\\kaspersky lab\\",
    "\\programdata\\kaspersky lab\\",
    "\\program files\\malwarebytes\\",
    "\\programdata\\malwarebytes\\",
    "\\program files\\mcafee\\",
    "\\programdata\\mcafee\\",
    "\\programdata\\smilegate\\",
    "\\program files\\sentinelone\\",
    "\\programdata\\sentinelone\\",
    "\\program files\\sophos\\",
    "\\programdata\\sophos\\",
    "\\program files\\trellix\\",
    "\\programdata\\trellix\\",
    "\\program files\\webroot\\",
    "\\programdata\\webroot\\",
    "\\appdata\\local\\microsoft\\onedrive\\",
    "\\program files\\microsoft onedrive\\",
    "\\appdata\\local\\discord\\",
    "\\appdata\\roaming\\discord\\",
    "\\appdata\\local\\google\\chrome\\application\\",
    "\\appdata\\local\\microsoft\\edge\\application\\",
    "\\appdata\\local\\bravesoftware\\brave-browser\\application\\",
    "\\appdata\\local\\programs\\opera gx\\",
    "\\appdata\\roaming\\opera software\\",
    "\\programdata\\obs-studio-hook\\",
    "\\program files\\windows defender\\",
    "\\program files\\netsupport\\",
    "\\program files (x86)\\netsupport\\",
)

TRUSTED_COMPANY_TOKENS = (
    "advanced micro devices",
    "avast",
    "avg",
    "bitdefender",
    "brave software",
    "crowdstrike",
    "discord",
    "eset",
    "google",
    "intel",
    "kaspersky",
    "malwarebytes",
    "mcafee",
    "microsoft",
    "mozilla",
    "nvidia",
    "obs project",
    "opera",
    "sentinelone",
    "smilegate",
    "sophos",
    "trellix",
    "valve",
    "webroot",
)

TRUSTED_FILE_DESCRIPTION_TOKENS = (
    "antivirus",
    "bitdefender",
    "discord",
    "endpoint security",
    "eset",
    "kaspersky",
    "malwarebytes",
    "microsoft defender",
    "microsoft edge",
    "obs",
    "onedrive",
    "security agent",
    "sentinel",
    "sophos",
    "steam",
    "windows security",
    "webroot",
)

PROTECTED_SYSTEM_PATH_MARKERS = (
    "\\windows\\",
    "\\program files\\",
    "\\program files (x86)\\",
)

NON_REMOVABLE_DIR_BASENAMES = {
    "",
    "appdata",
    "desktop",
    "documents",
    "downloads",
    "local",
    "program files",
    "program files (x86)",
    "programdata",
    "profiles",
    "roaming",
    "startup",
    "system32",
    "syswow64",
    "temp",
    "tmp",
    "user data",
    "users",
    "windows",
}

STRONG_CAMPAIGN_MARKERS = {
    "amatera",
    "archive.rpa",
    "antivmgpu",
    "antivmhypervisornames",
    "antivmmacs",
    "broker_crypt_v4_i386",
    "cc32290mt.dll",
    "chime.exe",
    "d3dx9_43.dll",
    "dksyvguj.exe",
    "froodjurain",
    "gayal.asp",
    "hap.eml",
    "instaler",
    "iviewers.dll",
    "lnstaier",
    "renengine",
    "renloader",
    "renpy",
    "script.rpyc",
    "instsatp_",
    "taig.gr",
    "t11_asm",
    "vsdebugscriptagent170",
    "w8cpbgqi.exe",
    "zoneind.exe",
    "zt5qwyucfl.txt",
}

MANUAL_REVIEW_CATEGORIES = {
    "Active Setup Persistence",
    "Alternate Data Stream Review",
    "Browser Extension Review",
    "Browser Policy Review",
    "Defender Protection Review",
    "Defender Policy Review",
    "Explorer Hijack Review",
    "Firewall Rule Review",
    "Hosts Tampering Review",
    "Installed Program Review",
    "KnownDLLs Review",
    "Proxy Configuration Review",
    "SafeBoot Review",
    "Security Center Review",
    "Security Event Review",
    "Session Manager Review",
    "Shell Persistence Review",
    "Source Lure Artifact",
    "Startup Correlation Review",
    "Suspicious Loader Stage Directory",
    "Suspicious RenPy Loader Bundle",
    "Winlogon Notify Review",
    "WinHTTP Proxy Review",
}

C2_IPS = {"78.40.193.126"}

PARANOID_NAME_TOKENS = ("update", "helper", "service", "runtime", "host")
COMMON_USERLAND_EXEC_MARKERS = (
    "\\programdata\\",
    "\\appdata\\roaming\\",
    "\\appdata\\local\\temp\\",
    "\\temp\\",
    "\\downloads\\",
)
TEMP_STAGE_DIR_REGEX = re.compile(r"\\(?:appdata\\local\\)?temp\\tmp-\d+-[a-z0-9_-]{6,}\\", re.IGNORECASE)
DRIVE_PATH_REGEX = re.compile(r"[A-Za-z]:\\[^\"'\r\n]+", re.IGNORECASE)
IPV4_HTTP_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:/[^\s\"']*)?", re.IGNORECASE)
VERSION_TAG_REGEX = re.compile(r"v?(\d+)\.(\d+)\.(\d+)", re.IGNORECASE)
GODOT_APP_USERDATA_MARKER = "\\appdata\\roaming\\godot\\app_userdata\\"
ASAR_ARGUMENT_MARKERS = ("node_modules.asar", ".asar")
IMYFONE_COMPANY_TOKENS = (
    "imyfone",
    "shenzhen imyfone technology",
)
PYTHON_COMPANY_TOKENS = (
    "python software foundation",
)
LOCAL_TOOL_CONTEXT_MARKERS = (
    "renkill.py",
    "renkill.exe",
    "renkill.spec",
    "renengine_hunter.py",
    "build.bat",
)
SCRIPT_LURE_REMOTE_MARKERS = (
    "http://",
    "https://",
    "discord.gg",
    "dropbox",
    "go.zovo",
    "mediafire",
    "mega",
    "pastebin",
    "telegram.me",
    "t.me/",
    "vyroget.com",
)
STARTUP_SCRIPT_EXTENSIONS = {".bat", ".cmd", ".exe", ".hta", ".js", ".ps1", ".py", ".pyw", ".url", ".vbs"}
STARTUP_DOWNLOADER_TOKENS = (
    "downloadstring",
    "invoke-webrequest",
    "iwr ",
    "start-bitstransfer",
    "mshta",
    "powershell",
    "curl ",
    "wget ",
    "/load",
)
SUSPICIOUS_STREAM_NAME_MARKERS = (
    "appdata",
    "asar",
    "bat",
    "cmd",
    "dll",
    "download",
    "exe",
    "hta",
    "js",
    "key",
    "loader",
    "payload",
    "ps1",
    "rar",
    "rpa",
    "rpyc",
    "run",
    "start",
    "vbs",
    "zip",
)
SUSPICIOUS_STARTUP_BASENAMES = {
    "discordsetup",
    "executor_ctrl",
    "interfacebroker",
    "server",
}
TEMP_STAGE_SIDELOAD_EXTENSIONS = {".asp", ".asar", ".dll", ".eml", ".key", ".txt"}
SAFE_SCRIPT_CONTENT_MARKERS = (
    "build script",
    "doctype html",
    "<html",
    "<head",
    "<body",
    "githubdesktop",
    "pip install",
    "pyinstaller",
    "python -m py_compile",
    "renengine_hunter.py",
    "renkill.py",
)
PROJECT_INDICATOR_BASENAMES = (
    ".git",
    ".vscode",
    "node_modules",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "readme.md",
    "readme.txt",
    "index.html",
)
PROJECT_INDICATOR_SUFFIXES = (
    ".sln",
    ".csproj",
    ".pyproj",
    ".vcxproj",
)
FRST_REVIEW_PROGRAM_NAMES = {
    "netsupport",
    "netsupport manager",
    "netsupport school",
    "urban vpn",
    "urban vpn proxy",
}

BROWSER_POLICY_ROOTS = (
    ("Chrome", r"SOFTWARE\Policies\Google\Chrome"),
    ("Edge", r"SOFTWARE\Policies\Microsoft\Edge"),
    ("Brave", r"SOFTWARE\Policies\BraveSoftware\Brave"),
)

BROWSER_POLICY_SUSPICIOUS_VALUE_TOKENS = (
    "extensioninstallforcelist",
    "extensionsettings",
    "homepage",
    "homepagelocation",
    "proxy",
    "restoreonstartupurls",
    "restoreonstartup",
    "webappinstallforcelist",
)

SECURITY_EVENT_LOG_SPECS = (
    ("Microsoft-Windows-Windows Defender/Operational", 7, "Defender", ()),
    ("Microsoft-Windows-CodeIntegrity/Operational", 7, "CodeIntegrity", ()),
    ("Microsoft-Windows-SecurityCenter/Operational", 7, "SecurityCenter", ()),
    ("Microsoft-Windows-Windows Firewall With Advanced Security/Firewall", 7, "Firewall", ()),
    ("System", 3, "ServiceControlManager", ("Service Control Manager",)),
)
DEFENDER_POLICY_VALUE_NAMES = {
    "disableantispyware",
    "disablerealtimemonitoring",
    "disablebehaviormonitoring",
    "disableioavprotection",
    "disablescriptscanning",
    "submitconsent",
    "spynetreporting",
}
SUSPICIOUS_EXTENSION_PERMISSIONS = {
    "cookies",
    "downloads",
    "management",
    "nativeMessaging",
    "proxy",
    "webRequest",
    "webRequestBlocking",
}
OFFICIAL_EXTENSION_UPDATE_URL_MARKERS = (
    "clients2.google.com/service/update2/crx",
    "clients2.googleusercontent.com/service/update2/crx",
    "edge.microsoft.com/extensionwebstorebase/v1/crx",
    "extension-updates.opera.com",
)
IMPERSONATED_EXTENSION_NAMES = {
    "google docs",
    "google docs offline",
    "google drive",
    "google sheets",
    "google slides",
}

SENSITIVE_HOST_MARKERS = {
    "accounts.google.com",
    "discord.com",
    "login.live.com",
    "login.microsoftonline.com",
    "steamcommunity.com",
    "store.steampowered.com",
    "wallet",
}

SHORTCUT_SCRIPT_HOSTS = {
    "cmd.exe",
    "cscript.exe",
    "mshta.exe",
    "powershell.exe",
    "pwsh.exe",
    "rundll32.exe",
    "wscript.exe",
}

BROWSER_SHORTCUT_TOKENS = (
    "brave",
    "chrome",
    "discord",
    "edge",
    "firefox",
    "steam",
)

KNOWN_BROWSER_TARGETS = {
    "brave.exe",
    "chrome.exe",
    "discord.exe",
    "firefox.exe",
    "msedge.exe",
    "steam.exe",
}

STARTUPAPPROVED_DISABLED_STATES = {0x01, 0x03, 0x09}
STARTUP_NAME_SAFE_TOKENS = (
    "amd",
    "audio",
    "brave",
    "chrome",
    "discord",
    "edge",
    "firefox",
    "microsoft",
    "onedrive",
    "opera",
    "security",
    "steam",
    "update",
    "vertex",
    "windows",
)

CHROMIUM_EXTENSION_REVIEW_ROOTS = (
    ("Chrome", os.path.join("AppData", "Local", "Google", "Chrome", "User Data")),
    ("Edge", os.path.join("AppData", "Local", "Microsoft", "Edge", "User Data")),
    ("Brave", os.path.join("AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data")),
    ("Opera", os.path.join("AppData", "Roaming", "Opera Software", "Opera Stable")),
)

PERSISTENCE_THREAT_CATEGORIES = {
    "Active Setup Persistence",
    "AppCert Persistence",
    "AppInit Persistence",
    "Disabled Startup Artifact",
    "Explorer Hijack Review",
    "HijackLoader Stage Directory",
    "Suspicious Loader Stage Directory",
    "Suspicious Temp Stage Directory",
    "IFEO Persistence",
    "Injected/Sideloaded DLL",
    "Loader Container DLL",
    "Logon Script Persistence",
    "Malicious Scheduled Task",
    "Malicious Service",
    "Persistence Artifact",
    "Persistence Staging Directory",
    "Policy Persistence",
    "Registry Persistence",
    "RunOnceEx Persistence",
    "SafeBoot Review",
    "Shell Persistence Review",
    "Startup-Launched Process",
    "Startup Correlation Review",
    "Startup Persistence Artifact",
    "Winlogon Notify Review",
    "WMI Persistence",
}

RENLOADER_CORRELATION_CATEGORIES = {
    "Active C2 Connection",
    "Active Setup Persistence",
    "AppCert Persistence",
    "AppInit Persistence",
    "Campaign IOC Process",
    "Defender Exclusion",
    "Execution Trace Anomaly",
    "Exact IOC Hash",
    "Explorer Hijack Review",
    "HijackLoader Stage Artifact",
    "HijackLoader Stage Directory",
    "IFEO Persistence",
    "Injected/Sideloaded DLL",
    "Logon Script Persistence",
    "Loader Container DLL",
    "Malicious Archive/Script",
    "Malicious File",
    "Malicious Process",
    "Malicious Scheduled Task",
    "Malicious Service",
    "Policy Persistence",
    "Persistence Artifact",
    "Persistence Process",
    "Persistence Staging Directory",
    "Registry Persistence",
    "RunOnceEx Persistence",
    "RenEngine Bundle",
    "SafeBoot Review",
    "Startup-Launched Process",
    "Stealer Script Host",
    "Suspicious Loader Stage Directory",
    "Suspicious Temp Stage Directory",
    "Suspicious RenPy Loader Bundle",
    "Winlogon Notify Review",
    "WMI Persistence",
}

PROCESS_REMEDIATION_CATEGORIES = {
    "Active C2 Connection",
    "Campaign IOC Process",
    "Execution Trace Anomaly",
    "Injected/Sideloaded DLL",
    "Malicious Child Process",
    "Malicious Process",
    "Malicious Service",
    "Paranoid Masquerade Process",
    "Paranoid Networked Process",
    "Paranoid Script Host",
    "Persistence Process",
    "Process in Temp",
    "Startup-Launched Process",
    "Stealer Script Host",
    "Suspicious Process",
    "Suspicious Userland Process",
    "WMI Persistence",
}

FILE_REMEDIATION_CATEGORIES = {
    "AppCert Persistence",
    "AppInit Persistence",
    "Defender Exclusion",
    "Disabled Startup Artifact",
    "Dropped Executable",
    "Exact IOC Hash",
    "Firewall Rule Review",
    "HijackLoader Stage Artifact",
    "HijackLoader Stage Directory",
    "Hijacked Module Init",
    "IFEO Persistence",
    "Loader Container DLL",
    "Malicious Archive/Script",
    "Malicious File",
    "Malicious Shortcut",
    "Payload Key File",
    "Persistence Artifact",
    "Persistence Staging Directory",
    "Policy Persistence",
    "Proxy Configuration Review",
    "RenEngine Bundle",
    "Startup Persistence Artifact",
    "Suspicious Temp Stage Directory",
}

CORRELATED_FILE_REMEDIATION_CATEGORIES = {
    "Suspicious Loader Stage Directory",
    "Suspicious Temp Stage Directory",
    "Suspicious RenPy Loader Bundle",
}

PROTECTION_REPAIR_CATEGORIES = {
    "Defender Exclusion",
    "Defender Policy Review",
    "Defender Protection Review",
    "Firewall Rule Review",
    "Proxy Configuration Review",
    "WinHTTP Proxy Review",
}

SUSPICIOUS_REG_PATTERNS = [
    "instaler",
    "lnstaier",
    r"\renpy\\",
    "iviewers",
    "uis4tq7p",
    "hijackloader",
    "broker_crypt_v4_i386",
    "froodjurain",
    "vsdebugscriptagent170",
    "zoneind",
    "chime.exe",
    "taig.gr",
    "cc32290mt.dll",
    "gayal.asp",
    "hap.eml",
    "w8cpbgqi.exe",
    "zt5qwyucfl.txt",
]


def _build_scan_roots():
    roots = []
    for key in ("TEMP", "TMP", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA"):
        val = os.environ.get(key, "")
        if val and os.path.exists(val):
            roots.append(val)
    profile = os.environ.get("USERPROFILE", "")
    for sub in ("Downloads", "Desktop", "Documents", "AppData\\Local\\Programs"):
        p = os.path.join(profile, sub)
        if os.path.exists(p):
            roots.append(p)
    return list(dict.fromkeys(roots))


SCAN_ROOTS = _build_scan_roots()

RECOVERY_DIRNAME = "Recovery"
RECOVERY_SESSIONS_DIR = "sessions"
RECOVERY_LATEST_FILE = "latest_session.txt"
RESTORE_CONFLICT_SUFFIX = ".renkill_restore"
RECOVERY_QUARANTINE_DIR = "quarantine"
QUARANTINE_NEUTRAL_EXTENSIONS = {
    ".7z",
    ".appx",
    ".appxbundle",
    ".asar",
    ".bat",
    ".cmd",
    ".com",
    ".cpl",
    ".dll",
    ".exe",
    ".hta",
    ".iso",
    ".js",
    ".lnk",
    ".msi",
    ".msix",
    ".msixbundle",
    ".pif",
    ".ps1",
    ".py",
    ".pyc",
    ".pyo",
    ".rar",
    ".rpa",
    ".rpyc",
    ".scr",
    ".vbs",
    ".zip",
}
QUARANTINE_INERT_SUFFIX = ".renkill-quarantine"

if WINREG_OK:
    HIVE_NAME_TO_CONST = {
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
    }
    HIVE_CONST_TO_NAME = {value: key for key, value in HIVE_NAME_TO_CONST.items()}
    REG_TYPE_NAMES = {
        winreg.REG_BINARY: "REG_BINARY",
        winreg.REG_DWORD: "REG_DWORD",
        winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
        winreg.REG_MULTI_SZ: "REG_MULTI_SZ",
        winreg.REG_QWORD: "REG_QWORD",
        winreg.REG_SZ: "REG_SZ",
    }
    REG_NAME_TO_TYPE = {value: key for key, value in REG_TYPE_NAMES.items()}
else:
    HIVE_NAME_TO_CONST = {}
    HIVE_CONST_TO_NAME = {}
    REG_TYPE_NAMES = {}
    REG_NAME_TO_TYPE = {}


def sanitize_for_display(text):
    if text is None:
        return ""
    out = str(text)
    profile = os.environ.get("USERPROFILE", "")
    username = os.environ.get("USERNAME", "")

    if profile:
        sanitized_profile = os.path.join(os.path.dirname(profile), "USERNAME")
        out = re.sub(re.escape(profile), lambda _: sanitized_profile, out, flags=re.IGNORECASE)

    if username:
        out = re.sub(r"(?i)(\\users\\)" + re.escape(username) + r"(?=\\|$)", lambda m: f"{m.group(1)}USERNAME", out)

    return out


# Admin elevation

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate_if_needed():
    if sys.platform != "win32":
        return
    if not is_admin():
        args = " ".join(f'"{a}"' for a in sys.argv)
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)
        if ret > 32:
            sys.exit(0)


# Threat model

class Threat:
    SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}

    def __init__(self, severity, category, description, path=None, action=None):
        self.severity = severity
        self.category = category
        self.description = description
        self.path = path or ""
        self.action = action
        self.remediated = False
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __lt__(self, other):
        return self.SEVERITY_ORDER.get(self.severity, 99) < self.SEVERITY_ORDER.get(other.severity, 99)


# Scanner engine

class ScanEngine:
    def __init__(self, log_cb, progress_cb, paranoid=False):
        self.log = log_cb
        self.progress = progress_cb
        self.paranoid = paranoid
        self.threats: list = []
        self.killed = 0
        self.removed = 0
        self._stop = False
        self.last_summary = None
        self.cleanup_assessment = None
        self.exposure_notes = []
        self.post_cleanup_scan = False
        self.rebooted_after_cleanup = False
        self.post_cleanup_persistence_summary = None
        self.post_cleanup_browser_summary = None
        self._tool_roots = self._compute_local_tool_roots()
        self._file_meta_cache = {}
        self._module_scan_pid_targets = set()
        self._shortcut_scan_rows = None
        self._scheduled_task_rows = None
        self._autorun_rows = None
        self._runonceex_rows = None
        self._policy_rows = None
        self._active_setup_rows = None
        self._disabled_startup_rows = None
        self._wmi_rows = None
        self._shell_rows = None
        self._logon_rows = None
        self._explorer_hijack_rows = None
        self._reset_recovery_state()

    def _add(self, severity, category, description, path=None, action=None):
        t = Threat(severity, category, description, path, action)
        self.threats.append(t)
        self.log(f"{description}", severity)
        return t

    def _note_exposure(self, description, path=None):
        note = (description, path or "")
        if note not in self.exposure_notes:
            self.exposure_notes.append(note)
            self.log(description if not path else f"{description}: {path}", "WARN")

    def _recovery_root(self):
        candidates = [
            os.path.join(os.environ.get("PROGRAMDATA", ""), TOOL_NAME, RECOVERY_DIRNAME),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), TOOL_NAME, RECOVERY_DIRNAME),
            os.path.join(os.getcwd(), f"{TOOL_NAME}_{RECOVERY_DIRNAME}"),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                os.makedirs(os.path.join(candidate, RECOVERY_SESSIONS_DIR), exist_ok=True)
                return candidate
            except Exception:
                continue
        return ""

    def _latest_recovery_pointer(self):
        root = self._recovery_root()
        return os.path.join(root, RECOVERY_LATEST_FILE) if root else ""

    def _session_dir(self, session_id):
        root = self._recovery_root()
        if not root or not session_id:
            return ""
        return os.path.join(root, RECOVERY_SESSIONS_DIR, session_id)

    def _write_manifest_dict(self, manifest):
        session_id = str(manifest.get("session_id") or "")
        session_dir = self._session_dir(session_id)
        if not session_dir:
            return False
        try:
            os.makedirs(session_dir, exist_ok=True)
            manifest_path = os.path.join(session_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(manifest, handle, indent=2)
            return True
        except Exception:
            return False

    def _persist_recovery_session(self):
        if not self._recovery_session:
            return False
        if not self._write_manifest_dict(self._recovery_session):
            return False
        pointer = self._latest_recovery_pointer()
        if pointer:
            try:
                with open(pointer, "w", encoding="utf-8") as handle:
                    handle.write(self._recovery_session["session_id"])
            except Exception:
                pass
        self._recovery_manifest_path = os.path.join(self._session_dir(self._recovery_session["session_id"]), "manifest.json")
        return True

    def _begin_recovery_session(self):
        if self._recovery_session:
            return True
        root = self._recovery_root()
        if not root:
            if not self._recovery_warning_emitted:
                self.log("Recovery snapshot could not be created. Revert will be unavailable for this cleanup.", "WARN")
                self._recovery_warning_emitted = True
            return False

        session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self._session_dir(session_id)
        try:
            os.makedirs(os.path.join(session_dir, "paths"), exist_ok=True)
            os.makedirs(os.path.join(session_dir, "tasks"), exist_ok=True)
            os.makedirs(os.path.join(session_dir, RECOVERY_QUARANTINE_DIR), exist_ok=True)
        except Exception:
            if not self._recovery_warning_emitted:
                self.log("Recovery snapshot could not be created. Revert will be unavailable for this cleanup.", "WARN")
                self._recovery_warning_emitted = True
            return False

        self._recovery_session = {
            "session_id": session_id,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tool_version": VERSION,
            "entries": [],
            "notes": [],
        }
        self._persist_recovery_session()
        self.log("Recovery snapshot started for this cleanup session.", "INFO")
        return True

    def _startup_snapshot_entries(self):
        entries = []

        def add(surface, location, command):
            cmd = self._normalize_cmdline(command).strip()
            if not cmd or self._is_local_tool_context(cmd):
                return
            target = self._extract_command_target(cmd)
            signal = self._startup_signal_for_command(cmd)
            entries.append(
                {
                    "surface": surface,
                    "location": str(location or ""),
                    "command": cmd,
                    "target": self._normalized_path(target) or cmd.lower(),
                    "signal": bool(signal),
                }
            )

        for row in self._collect_run_autorun_rows():
            add("autorun", f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]", row.get("Value"))
        for row in self._collect_runonceex_rows():
            add("runonceex", f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]", row.get("Value"))
        for row in self._collect_policy_persistence_rows():
            add("policy", f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]", row.get("Value"))
        for row in self._collect_active_setup_rows():
            add("active-setup", f"{row.get('HiveName')}\\{row.get('Subkey')}[StubPath]", row.get("StubPath"))
        for row in self._collect_shell_persistence_rows():
            add("shell", f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]", row.get("Value"))
        for row in self._collect_logon_persistence_rows():
            add("logon", f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]", row.get("Value"))
        for row in self._collect_shortcut_rows():
            add("shortcut", row.get("Path"), " ".join(part for part in (row.get("TargetPath"), row.get("Arguments")) if part))
        for row in self._iter_startup_file_rows():
            add("startup-file", row.get("Path"), row.get("Path"))
        for row in self._collect_scheduled_task_rows():
            add("task", f"{row.get('TaskPath') or ''}{row.get('TaskName') or ''}", " ".join(part for part in (row.get("Execute"), row.get("Arguments")) if part))
        for row in self._collect_wmi_persistence_rows():
            if str(row.get("ClassName") or "") == "CommandLineEventConsumer":
                add("wmi", str(row.get("Name") or ""), row.get("CommandLineTemplate") or row.get("ExecutablePath"))
            elif str(row.get("ClassName") or "") == "ActiveScriptEventConsumer":
                add("wmi-script", str(row.get("Name") or ""), row.get("ScriptText"))

        return entries

    def _capture_pre_cleanup_snapshot(self):
        if not self._begin_recovery_session():
            return False
        snapshot = {
            "captured_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entries": self._startup_snapshot_entries(),
            "browser_entries": self._browser_snapshot_entries(),
        }
        self._recovery_session["pre_cleanup_snapshot"] = snapshot
        self._persist_recovery_session()
        return True

    def _record_recovery_entry(self, entry):
        if not self._begin_recovery_session():
            return False
        payload = dict(entry)
        payload.setdefault("recorded_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._recovery_session["entries"].append(payload)
        self._persist_recovery_session()
        return True

    def _record_recovery_note(self, note):
        if not self._begin_recovery_session():
            return False
        text = str(note or "").strip()
        if not text:
            return False
        self._recovery_session["notes"].append(text)
        self._persist_recovery_session()
        return True

    def _load_latest_recovery_manifest(self):
        pointer = self._latest_recovery_pointer()
        if not pointer or not os.path.isfile(pointer):
            return None
        try:
            with open(pointer, "r", encoding="utf-8") as handle:
                session_id = handle.read().strip()
        except Exception:
            return None
        if not session_id:
            return None
        manifest_path = os.path.join(self._session_dir(session_id), "manifest.json")
        if not os.path.isfile(manifest_path):
            return None
        try:
            with open(manifest_path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
        except Exception:
            return None
        if manifest.get("reverted_at"):
            return None
        if not manifest.get("entries"):
            return None
        return manifest

    def get_latest_recovery_summary(self):
        manifest = self._load_latest_recovery_manifest()
        if not manifest:
            return {
                "available": False,
                "created_at": "",
                "session_id": "",
                "reversible_count": 0,
                "note_count": 0,
                "restore_point": {},
            }
        return {
            "available": True,
            "created_at": str(manifest.get("created_at") or ""),
            "session_id": str(manifest.get("session_id") or ""),
            "reversible_count": len(manifest.get("entries") or []),
            "note_count": len(manifest.get("notes") or []),
            "restore_point": manifest.get("restore_point") or {},
        }

    def compare_post_cleanup_persistence(self):
        if not self.post_cleanup_scan:
            self.post_cleanup_persistence_summary = None
            return None

        manifest = self._load_latest_recovery_manifest()
        snapshot = (manifest or {}).get("pre_cleanup_snapshot") or {}
        previous_entries = snapshot.get("entries") or []
        if not previous_entries:
            self.post_cleanup_persistence_summary = None
            return None

        current_entries = self._startup_snapshot_entries()
        current_targets = {}
        for entry in current_entries:
            current_targets.setdefault(entry.get("target") or "", []).append(entry)

        reappeared = []
        cleared = 0
        suspicious_reappeared = 0
        for entry in previous_entries:
            target = entry.get("target") or ""
            matches = current_targets.get(target) or []
            if matches:
                reappeared.append(
                    {
                        "target": target,
                        "before": entry,
                        "after": matches[0],
                    }
                )
                if entry.get("signal") or matches[0].get("signal"):
                    suspicious_reappeared += 1
            else:
                cleared += 1

        summary = {
            "before_count": len(previous_entries),
            "current_count": len(current_entries),
            "cleared_count": cleared,
            "reappeared_count": len(reappeared),
            "suspicious_reappeared_count": suspicious_reappeared,
            "reappeared": reappeared[:8],
        }
        self.post_cleanup_persistence_summary = summary
        return summary

    def _browser_review_entries(self):
        findings = []
        seen = set()

        def add(label, path, target, description, signal=True):
            path_text = str(path or "")
            target_text = str(target or "").strip().lower()
            finding_key = (label, path_text, target_text, description)
            if finding_key in seen:
                return
            seen.add(finding_key)
            findings.append(
                {
                    "label": str(label or ""),
                    "path": path_text,
                    "target": target_text or path_text.lower(),
                    "description": str(description or ""),
                    "signal": bool(signal),
                }
            )

        for label, manifest_path in self._iter_chromium_extension_manifests():
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    manifest = json.load(handle)
            except Exception:
                continue

            blob = json.dumps(manifest, ensure_ascii=True).lower()
            permissions = {
                str(value).lower()
                for section in ("permissions", "host_permissions", "optional_permissions")
                for value in (manifest.get(section) or [])
            }
            keyword_hit = self._contains_marker(
                blob,
                {
                    "acrstealer",
                    "broker_crypt",
                    "chime",
                    "froodjurain",
                    "instaler",
                    "lumma",
                    "renengine",
                    "renloader",
                    "rhadamanthys",
                    "vidar",
                    "vsdebugscriptagent170",
                    "zoneind",
                },
            )
            remote_lure_hit = self._contains_marker(blob, {"go.zovo", "mediafire", "mega", "dodi-repacks"})
            risky_permissions = bool(permissions & {perm.lower() for perm in SUSPICIOUS_EXTENSION_PERMISSIONS})
            update_url = str(
                manifest.get("update_url")
                or manifest.get("browser_specific_settings", {}).get("gecko", {}).get("update_url")
                or ""
            )
            update_url_lower = update_url.lower()
            extension_name = str(manifest.get("name") or os.path.basename(os.path.dirname(manifest_path)))
            extension_name_lower = extension_name.lower()
            suspicious_update_url = bool(update_url_lower) and not any(
                marker in update_url_lower for marker in OFFICIAL_EXTENSION_UPDATE_URL_MARKERS
            )
            impersonation_hit = extension_name_lower in IMPERSONATED_EXTENSION_NAMES

            if not (
                self._has_strong_campaign_context(blob, manifest_path)
                or remote_lure_hit
                or (keyword_hit and risky_permissions)
                or (impersonation_hit and suspicious_update_url)
                or (suspicious_update_url and risky_permissions and self._contains_remote_loader_marker(update_url_lower))
            ):
                continue

            target = f"{label}:{extension_name_lower}:{update_url_lower or manifest_path.lower()}"
            add(label, manifest_path, target, f"{label} extension needs review: {extension_name}")

        profile = os.environ.get("USERPROFILE", "")
        for label, rel_root in CHROMIUM_EXTENSION_REVIEW_ROOTS:
            root = os.path.join(profile, rel_root)
            for profile_dir in self._chromium_profile_dirs(root):
                preferences_path = os.path.join(profile_dir, "Preferences")
                if not os.path.isfile(preferences_path):
                    continue
                try:
                    with open(preferences_path, "r", encoding="utf-8", errors="ignore") as handle:
                        preferences = json.load(handle)
                except Exception:
                    continue

                settings = (((preferences or {}).get("extensions") or {}).get("settings") or {})
                if not isinstance(settings, dict):
                    continue

                for ext_id, entry in settings.items():
                    if not isinstance(entry, dict):
                        continue

                    state = int(entry.get("state") or 0)
                    if state <= 0:
                        continue

                    manifest = entry.get("manifest") or {}
                    extension_name = str(manifest.get("name") or ext_id)
                    extension_name_lower = extension_name.lower()
                    update_url = str(entry.get("update_url") or manifest.get("update_url") or "")
                    update_url_lower = update_url.lower()
                    suspicious_update_url = bool(update_url_lower) and not any(
                        marker in update_url_lower for marker in OFFICIAL_EXTENSION_UPDATE_URL_MARKERS
                    )
                    impersonation_hit = extension_name_lower in IMPERSONATED_EXTENSION_NAMES
                    profile_ext_dir = os.path.join(profile_dir, "Extensions", ext_id)
                    installed_on_disk = os.path.isdir(profile_ext_dir)
                    path_value = str(entry.get("path") or "")
                    normalized_path = self._normalized_path(path_value)
                    risky_state = (
                        (impersonation_hit and suspicious_update_url)
                        or (suspicious_update_url and self._contains_remote_loader_marker(update_url_lower))
                        or (normalized_path and self._path_in_user_writable_exec_zone(normalized_path) and not self._is_local_tool_path(normalized_path))
                    )
                    if not risky_state:
                        continue

                    target_root = normalized_path or profile_ext_dir or ext_id
                    target = f"{label}:{ext_id.lower()}:{target_root.lower()}:{update_url_lower}"
                    if not installed_on_disk:
                        add(
                            label,
                            preferences_path,
                            target,
                            f"{label} profile still references a missing suspicious extension: {extension_name}",
                        )
                    else:
                        add(
                            label,
                            preferences_path,
                            target,
                            f"{label} extension state needs review: {extension_name}",
                        )

        return findings

    def _browser_snapshot_entries(self):
        entries = []
        for finding in self._browser_review_entries():
            entries.append(
                {
                    "browser": finding.get("label") or "",
                    "path": finding.get("path") or "",
                    "target": finding.get("target") or "",
                    "description": finding.get("description") or "",
                    "signal": bool(finding.get("signal")),
                }
            )
        return entries

    def compare_post_cleanup_browser_state(self):
        if not self.post_cleanup_scan:
            self.post_cleanup_browser_summary = None
            return None

        manifest = self._load_latest_recovery_manifest()
        snapshot = (manifest or {}).get("pre_cleanup_snapshot") or {}
        previous_entries = snapshot.get("browser_entries") or []
        if not previous_entries:
            self.post_cleanup_browser_summary = None
            return None

        current_entries = self._browser_snapshot_entries()
        current_targets = {}
        for entry in current_entries:
            current_targets.setdefault(entry.get("target") or "", []).append(entry)

        reappeared = []
        cleared = 0
        for entry in previous_entries:
            target = entry.get("target") or ""
            matches = current_targets.get(target) or []
            if matches:
                reappeared.append(
                    {
                        "target": target,
                        "before": entry,
                        "after": matches[0],
                    }
                )
            else:
                cleared += 1

        summary = {
            "before_count": len(previous_entries),
            "current_count": len(current_entries),
            "cleared_count": cleared,
            "reappeared_count": len(reappeared),
            "reappeared": reappeared[:8],
        }
        self.post_cleanup_browser_summary = summary
        return summary

    @staticmethod
    def _safe_backup_name(path):
        base = os.path.basename(os.path.normpath(path or "")) or "item"
        return re.sub(r"[^A-Za-z0-9._-]+", "_", base)

    @staticmethod
    def _needs_inert_quarantine_name(path, *, is_dir=False):
        if is_dir:
            return True
        ext = os.path.splitext(str(path or ""))[1].lower()
        return ext in QUARANTINE_NEUTRAL_EXTENSIONS

    def _build_quarantine_backup_name(self, path, counter):
        safe_name = self._safe_backup_name(path)
        is_dir = os.path.isdir(path)
        if self._needs_inert_quarantine_name(path, is_dir=is_dir):
            safe_name += QUARANTINE_INERT_SUFFIX
        return f"{counter:04d}_{safe_name}"

    @staticmethod
    def _harden_quarantine_path(path):
        try:
            subprocess.run(
                ["attrib", "+r", "+h", "+s", path],
                capture_output=True,
                creationflags=0x08000000,
                timeout=10,
            )
        except Exception:
            return False
        return True

    def _quarantine_summary(self, session=None):
        session = session or self._recovery_session or {}
        entries = session.get("entries") or []
        quarantined = [entry for entry in entries if entry.get("kind") == "path_move"]
        neutralized = sum(
            1 for entry in quarantined
            if str(entry.get("backup_name") or "").lower().endswith(QUARANTINE_INERT_SUFFIX)
        )
        return {
            "items": len(quarantined),
            "files": sum(1 for entry in quarantined if not entry.get("is_dir")),
            "dirs": sum(1 for entry in quarantined if entry.get("is_dir")),
            "neutralized": neutralized,
        }

    @staticmethod
    def _format_removal_failure(action, path, reason):
        path = str(path or "")
        reason = str(reason or "unknown reason")
        return f"Could not {action}: {path} ({reason})"

    @staticmethod
    def _result_failure_reason(result, fallback="operation failed"):
        if result is None:
            return fallback
        parts = []
        stdout = str(getattr(result, "stdout", "") or "").strip()
        stderr = str(getattr(result, "stderr", "") or "").strip()
        if stderr:
            parts.append(stderr)
        if stdout and stdout not in parts:
            parts.append(stdout)
        if not parts:
            parts.append(f"exit code {getattr(result, 'returncode', 'unknown')}")
        return "; ".join(parts)

    def _try_move_path_to_recovery(self, path):
        if not os.path.exists(path):
            return None, "path no longer exists"
        if not self._begin_recovery_session():
            return None, "recovery snapshot is unavailable"
        session_dir = self._session_dir(self._recovery_session["session_id"])
        counter = len(self._recovery_session["entries"]) + 1
        backup_name = self._build_quarantine_backup_name(path, counter)
        backup_path = os.path.join(session_dir, RECOVERY_QUARANTINE_DIR, backup_name)
        try:
            shutil.move(path, backup_path)
        except PermissionError:
            try:
                subprocess.run(["attrib", "-r", "-s", "-h", path], capture_output=True, creationflags=0x08000000)
                shutil.move(path, backup_path)
            except PermissionError:
                return None, "access denied or file is locked by another process"
            except Exception as exc:
                return None, str(exc)
        except Exception as exc:
            return None, str(exc)

        self._harden_quarantine_path(backup_path)
        entry = {
            "kind": "path_move",
            "original_path": path,
            "backup_path": backup_path,
            "is_dir": bool(os.path.isdir(backup_path)),
            "quarantined": True,
            "backup_name": backup_name,
        }
        self._record_recovery_entry(entry)
        return backup_path, ""

    def _move_path_to_recovery(self, path):
        backup_path, _reason = self._try_move_path_to_recovery(path)
        return backup_path

    @staticmethod
    def _serialize_reg_data(value, reg_type):
        if WINREG_OK and reg_type == winreg.REG_BINARY:
            return {
                "encoding": "base64",
                "value": base64.b64encode(bytes(value)).decode("ascii"),
            }
        if WINREG_OK and reg_type == winreg.REG_MULTI_SZ:
            return {
                "encoding": "list",
                "value": list(value),
            }
        if WINREG_OK and reg_type in (winreg.REG_DWORD, winreg.REG_QWORD):
            return {
                "encoding": "int",
                "value": int(value),
            }
        return {
            "encoding": "str",
            "value": str(value),
        }

    @staticmethod
    def _deserialize_reg_data(payload):
        encoding = str((payload or {}).get("encoding") or "")
        value = (payload or {}).get("value")
        if encoding == "base64":
            try:
                return base64.b64decode(value or "")
            except Exception:
                return b""
        if encoding == "list":
            return list(value or [])
        if encoding == "int":
            try:
                return int(value)
            except Exception:
                return 0
        return str(value or "")

    def _capture_reg_value_entry(self, hive, subkey, name):
        if not WINREG_OK:
            return None
        hive_name = HIVE_CONST_TO_NAME.get(hive, "")
        if not hive_name:
            return None
        try:
            key = winreg.OpenKey(hive, subkey)
            value, reg_type = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
        except Exception:
            return None
        return {
            "kind": "reg_delete",
            "hive": hive_name,
            "subkey": subkey,
            "name": name,
            "type_name": REG_TYPE_NAMES.get(reg_type, "REG_SZ"),
            "data": self._serialize_reg_data(value, reg_type),
        }

    def _capture_reg_state(self, hive, subkey, name):
        if not WINREG_OK:
            return None
        hive_name = HIVE_CONST_TO_NAME.get(hive, "")
        if not hive_name:
            return None
        try:
            key = winreg.OpenKey(hive, subkey)
        except (FileNotFoundError, PermissionError):
            return {
                "hive": hive_name,
                "subkey": subkey,
                "name": name,
                "exists": False,
            }
        try:
            value, reg_type = winreg.QueryValueEx(key, name)
            snapshot = {
                "hive": hive_name,
                "subkey": subkey,
                "name": name,
                "exists": True,
                "type_name": REG_TYPE_NAMES.get(reg_type, "REG_SZ"),
                "data": self._serialize_reg_data(value, reg_type),
            }
        except OSError:
            snapshot = {
                "hive": hive_name,
                "subkey": subkey,
                "name": name,
                "exists": False,
            }
        try:
            winreg.CloseKey(key)
        except Exception:
            pass
        return snapshot

    def _restore_reg_state(self, snapshot):
        if not WINREG_OK or not snapshot:
            return False
        hive = HIVE_NAME_TO_CONST.get(str(snapshot.get("hive") or ""))
        subkey = str(snapshot.get("subkey") or "")
        name = str(snapshot.get("name") or "")
        if hive is None or not subkey or not name:
            return False
        try:
            key = winreg.CreateKeyEx(hive, subkey, 0, winreg.KEY_SET_VALUE)
            if snapshot.get("exists"):
                reg_type = REG_NAME_TO_TYPE.get(str(snapshot.get("type_name") or ""), winreg.REG_SZ)
                data = self._deserialize_reg_data(snapshot.get("data"))
                winreg.SetValueEx(key, name, 0, reg_type, data)
            else:
                try:
                    winreg.DeleteValue(key, name)
                except OSError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def _capture_task_xml(self, task_name):
        if not task_name or not self._begin_recovery_session():
            return None
        try:
            result = subprocess.run(
                [self._schtasks_path(), "/query", "/tn", task_name, "/xml"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=0x08000000,
            )
        except Exception:
            return None
        if result.returncode != 0 or not (result.stdout or "").strip():
            return None
        session_dir = self._session_dir(self._recovery_session["session_id"])
        backup_name = f"{len(self._recovery_session['entries']) + 1:04d}_{self._safe_backup_name(task_name)}.xml"
        xml_path = os.path.join(session_dir, "tasks", backup_name)
        try:
            with open(xml_path, "w", encoding="utf-16") as handle:
                handle.write(result.stdout)
        except Exception:
            try:
                with open(xml_path, "w", encoding="utf-8") as handle:
                    handle.write(result.stdout)
            except Exception:
                return None
        return {
            "kind": "task_delete",
            "task_name": task_name,
            "xml_path": xml_path,
        }

    def _capture_firewall_rule(self, rule_name):
        if not rule_name:
            return None
        escaped = rule_name.replace("'", "''")
        rows = self._run_powershell_json(
            "$rule = Get-NetFirewallRule -Name '" + escaped + "' -ErrorAction SilentlyContinue | Select-Object -First 1; "
            "if ($rule) { "
            "$app = $rule | Get-NetFirewallApplicationFilter -ErrorAction SilentlyContinue | Select-Object -First 1; "
            "$port = $rule | Get-NetFirewallPortFilter -ErrorAction SilentlyContinue | Select-Object -First 1; "
            "$addr = $rule | Get-NetFirewallAddressFilter -ErrorAction SilentlyContinue | Select-Object -First 1; "
            "$svc = $rule | Get-NetFirewallServiceFilter -ErrorAction SilentlyContinue | Select-Object -First 1; "
            "[pscustomobject]@{ "
            "Name=$rule.Name; DisplayName=$rule.DisplayName; Description=$rule.Description; "
            "Direction=[string]$rule.Direction; Action=[string]$rule.Action; Profile=[string]$rule.Profile; "
            "Enabled=[string]$rule.Enabled; Program=$app.Program; Service=$svc.Service; "
            "Protocol=$port.Protocol; LocalPort=$port.LocalPort; RemotePort=$port.RemotePort; "
            "LocalAddress=$addr.LocalAddress; RemoteAddress=$addr.RemoteAddress "
            "} | ConvertTo-Json -Compress }",
            timeout=20,
        )
        if not rows:
            return None
        return {
            "kind": "firewall_rule_remove",
            "rule": rows[0],
        }

    @staticmethod
    def _powershell_quote(value):
        return "'" + str(value or "").replace("'", "''") + "'"

    def _restore_path_entry(self, entry):
        original_path = str(entry.get("original_path") or "")
        backup_path = str(entry.get("backup_path") or "")
        if not original_path or not backup_path or not os.path.exists(backup_path):
            return False, ""

        target_path = original_path
        if os.path.exists(original_path):
            candidate = original_path + RESTORE_CONFLICT_SUFFIX
            suffix = 1
            while os.path.exists(candidate):
                suffix += 1
                candidate = f"{original_path}{RESTORE_CONFLICT_SUFFIX}_{suffix}"
            target_path = candidate

        try:
            try:
                subprocess.run(
                    ["attrib", "-r", "-s", "-h", backup_path],
                    capture_output=True,
                    creationflags=0x08000000,
                    timeout=10,
                )
            except Exception:
                pass
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.move(backup_path, target_path)
            return True, target_path
        except Exception:
            return False, ""

    def _restore_task_entry(self, entry):
        task_name = str(entry.get("task_name") or "")
        xml_path = str(entry.get("xml_path") or "")
        if not task_name or not xml_path or not os.path.isfile(xml_path):
            return False
        try:
            result = subprocess.run(
                [self._schtasks_path(), "/create", "/tn", task_name, "/xml", xml_path, "/f"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=0x08000000,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _restore_firewall_entry(self, entry):
        rule = entry.get("rule") or {}
        if not rule:
            return False
        params = []
        for key in ("Name", "DisplayName", "Description", "Direction", "Action", "Profile"):
            value = str(rule.get(key) or "")
            if value and value.lower() not in {"any", "notconfigured"}:
                params.append(f"-{key} {self._powershell_quote(value)}")
        enabled = str(rule.get("Enabled") or "")
        if enabled.lower() in {"true", "false"}:
            params.append(f"-Enabled {enabled}")
        for key in ("Program", "Service", "LocalPort", "RemotePort", "LocalAddress", "RemoteAddress"):
            value = str(rule.get(key) or "")
            if value and value.lower() not in {"any", "notconfigured"}:
                params.append(f"-{key} {self._powershell_quote(value)}")
        protocol = str(rule.get("Protocol") or "")
        if protocol and protocol.lower() not in {"any", "notconfigured"}:
            params.append(f"-Protocol {self._powershell_quote(protocol)}")
        if not params:
            return False
        script = "try { New-NetFirewallRule " + " ".join(params) + " -ErrorAction Stop | Out-Null } catch { exit 1 }"
        result = self._run_powershell(script, timeout=20)
        return bool(result is not None and result.returncode == 0)

    def _restore_defender_exclusion_entry(self, entry):
        kind = str(entry.get("exclusion_kind") or "")
        value = str(entry.get("value") or "")
        if not kind or not value:
            return False
        quoted = self._powershell_quote(value)
        if kind == "Path":
            script = f"try {{ Add-MpPreference -ExclusionPath {quoted} -ErrorAction Stop }} catch {{ exit 1 }}"
        elif kind == "Process":
            script = f"try {{ Add-MpPreference -ExclusionProcess {quoted} -ErrorAction Stop }} catch {{ exit 1 }}"
        elif kind == "Extension":
            script = f"try {{ Add-MpPreference -ExclusionExtension {quoted} -ErrorAction Stop }} catch {{ exit 1 }}"
        else:
            return False
        result = self._run_powershell(script, timeout=20)
        return bool(result is not None and result.returncode == 0)

    def _restore_proxy_entry(self, entry):
        snapshots = entry.get("snapshots") or []
        restored_any = False
        for snapshot in snapshots:
            restored_any = self._restore_reg_state(snapshot) or restored_any
        return restored_any

    def _restore_winhttp_proxy_entry(self, entry):
        mode = str(entry.get("mode") or "").lower()
        if mode == "direct":
            result = subprocess.run(
                ["netsh", "winhttp", "reset", "proxy"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=0x08000000,
            )
            return result.returncode == 0

        proxy = str(entry.get("proxy") or "").strip()
        if not proxy:
            return False

        command = ["netsh", "winhttp", "set", "proxy", f"proxy-server={proxy}"]
        bypass = str(entry.get("bypass") or "").strip()
        if bypass:
            command.append(f"bypass-list={bypass}")
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=0x08000000,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _restore_defender_pref_entry(self, entry):
        settings = entry.get("settings") or {}
        if not settings:
            return False

        params = []
        for key in ("DisableRealtimeMonitoring", "DisableIOAVProtection", "DisableScriptScanning"):
            if key not in settings:
                continue
            params.append(f"-{key} ${str(bool(settings.get(key))).lower()}")
        if not params:
            return False

        result = self._run_powershell(
            "try { Set-MpPreference " + " ".join(params) + " -ErrorAction Stop } catch { exit 1 }",
            timeout=25,
        )
        return bool(result is not None and result.returncode == 0)

    def revert_last_remediation(self):
        manifest = self._load_latest_recovery_manifest()
        if not manifest:
            return {
                "restored": 0,
                "failed": 0,
                "conflicts": 0,
                "notes": [],
            }

        restored = 0
        failed = 0
        conflicts = 0
        for entry in reversed(manifest.get("entries") or []):
            kind = str(entry.get("kind") or "")
            ok = False
            conflict_target = ""
            if kind == "path_move":
                ok, conflict_target = self._restore_path_entry(entry)
                if ok and conflict_target and conflict_target != entry.get("original_path"):
                    conflicts += 1
                    self.log(
                        f"Restored quarantined item to conflict-safe path: {conflict_target}",
                        "WARN",
                    )
            elif kind == "reg_delete":
                ok = self._restore_reg_state(entry)
            elif kind == "proxy_reset":
                ok = self._restore_proxy_entry(entry)
            elif kind == "winhttp_proxy_reset":
                ok = self._restore_winhttp_proxy_entry(entry)
            elif kind == "defender_exclusion_remove":
                ok = self._restore_defender_exclusion_entry(entry)
            elif kind == "defender_pref_restore":
                ok = self._restore_defender_pref_entry(entry)
            elif kind == "firewall_rule_remove":
                ok = self._restore_firewall_entry(entry)
            elif kind == "task_delete":
                ok = self._restore_task_entry(entry)

            if ok:
                restored += 1
            else:
                failed += 1
                self.log(f"Could not restore recorded change: {kind}", "WARN")

        manifest["reverted_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        manifest["revert_result"] = {
            "restored": restored,
            "failed": failed,
            "conflicts": conflicts,
        }
        self._write_manifest_dict(manifest)

        pointer = self._latest_recovery_pointer()
        if pointer and os.path.isfile(pointer):
            try:
                os.remove(pointer)
            except Exception:
                pass

        for note in manifest.get("notes") or []:
            self.log(f"Not reversible: {note}", "WARN")

        return {
            "restored": restored,
            "failed": failed,
            "conflicts": conflicts,
            "notes": manifest.get("notes") or [],
        }

    @staticmethod
    def _clamp_score(value, lower=5, upper=98):
        return max(lower, min(upper, int(value)))

    def _reset_recovery_state(self):
        self._recovery_session = None
        self._recovery_manifest_path = ""
        self._recovery_warning_emitted = False

    def _active_file_remediation_categories(self):
        categories = set(FILE_REMEDIATION_CATEGORIES)
        if self._has_renloader_corroboration():
            categories.update(CORRELATED_FILE_REMEDIATION_CATEGORIES)
        return categories

    def _run_remediation_bucket(self, categories):
        for threat in sorted(self.threats):
            if threat.category in categories and threat.action and not threat.remediated:
                try:
                    result = threat.action()
                    threat.remediated = bool(result)
                    if not result:
                        self.log(
                            f"Remediation action did not complete for {threat.category}: {threat.path or threat.description}",
                            "WARN",
                        )
                except Exception as exc:
                    self.log(
                        f"Remediation error in {threat.category}: {exc} | {threat.path or threat.description}",
                        "CRITICAL",
                    )
                    self.log(traceback.format_exc().strip(), "WARN")

    def _log_recovery_snapshot_summary(self):
        if not self._recovery_session:
            return
        reversible_count = len(self._recovery_session.get("entries") or [])
        note_count = len(self._recovery_session.get("notes") or [])
        restore_point = self._recovery_session.get("restore_point") or {}
        quarantine = self._quarantine_summary(self._recovery_session)
        self.log(
            f"Recovery snapshot recorded {reversible_count} reversible change(s) and {note_count} note(s).",
            "INFO",
        )
        if restore_point:
            status = str(restore_point.get("status") or "")
            if status == "created":
                self.log("System Restore point is available for this cleanup session.", "INFO")
            elif status == "recently_created":
                self.log("Windows already had a recent System Restore point, so no new one was created.", "INFO")
            elif status == "unavailable":
                detail = str(restore_point.get("detail") or "")
                message = "System Restore point was unavailable for this cleanup session."
                if detail:
                    message += f" {detail}"
                self.log(message, "WARN")
        if quarantine["items"]:
            self.log(
                f"Quarantine summary  : {quarantine['items']} item(s) isolated - {quarantine['files']} file(s), {quarantine['dirs']} directorie(s), {quarantine['neutralized']} inert payload copy/copies.",
                "INFO",
            )

    @staticmethod
    def _report_group_name(category):
        startup_categories = {
            "Active Setup Persistence",
            "AppCert Persistence",
            "Explorer Hijack Review",
            "KnownDLLs Review",
            "Disabled Startup Artifact",
            "Logon Script Persistence",
            "Malicious Scheduled Task",
            "Malicious Shortcut",
            "Policy Persistence",
            "Registry Persistence",
            "RunOnceEx Persistence",
            "SafeBoot Review",
            "Session Manager Review",
            "Shell Persistence Review",
            "Startup-Launched Process",
            "Startup Correlation Review",
            "Startup Persistence Artifact",
            "Winlogon Notify Review",
            "WMI Persistence",
        }
        process_categories = {
            "Active C2 Connection",
            "Campaign IOC Process",
            "Execution Trace Anomaly",
            "Injected/Sideloaded DLL",
            "Malicious Child Process",
            "Paranoid Masquerade Process",
            "Paranoid Networked Process",
            "Paranoid Script Host",
            "Process in Temp",
            "Suspicious Process",
            "Suspicious Userland Process",
        }
        posture_categories = {
            "Browser Extension Review",
            "Browser Policy Review",
            "Defender Exclusion",
            "Defender Policy Review",
            "Defender Protection Review",
            "Firewall Rule Review",
            "Hosts Tampering Review",
            "Installed Program Review",
            "Proxy Configuration Review",
            "Security Center Review",
            "Security Event Review",
            "WinHTTP Proxy Review",
        }
        filesystem_categories = {
            "Alternate Data Stream Review",
            "Exact IOC Hash",
            "HijackLoader Stage Artifact",
            "HijackLoader Stage Directory",
            "Loader Container DLL",
            "Malicious Archive/Script",
            "Malicious File",
            "Persistence Artifact",
            "Persistence Staging Directory",
            "RenEngine Bundle",
            "Source Lure Artifact",
            "Suspicious Loader Stage Directory",
            "Suspicious RenPy Loader Bundle",
        }

        if category in startup_categories:
            return "Startup / Persistence"
        if category in process_categories:
            return "Process / Memory / Network"
        if category in filesystem_categories:
            return "Files / Staging"
        if category in posture_categories:
            return "System Posture / Policy"
        return "Other Findings"

    def assess_account_exposure(self):
        exposure_count = len(self.exposure_notes)
        summary = self.last_summary or self.summarize_threats()
        profile = self._threat_confidence_profile()

        score = 8
        if summary["confidence"] in {"high", "medium"}:
            score += 24
        if profile["generic_stealer_hits"] >= 2:
            score += 26
        elif profile["generic_stealer_hits"] >= 1:
            score += 14
        if "Active C2 Connection" in profile["categories"]:
            score += 16
        if "Defender Exclusion" in profile["categories"]:
            score += 8
        if "Browser Extension Review" in profile["categories"] or "Browser Policy Review" in profile["categories"]:
            score += 8
        if exposure_count:
            score += min(32, exposure_count * 10)

        score = self._clamp_score(score, lower=0, upper=98)

        if score >= 70:
            label = "High account/session compromise risk"
            detail = "Browser or app session material may already be exposed. Treat this like a full account-compromise incident from a clean device."
            color = RED
        elif score >= 40:
            label = "Moderate account/session compromise risk"
            detail = "Local signs point to possible session or credential exposure. Review accounts, revoke sessions, and rotate sensitive credentials from a clean device."
            color = AMBER
        else:
            label = "Low confirmed account/session compromise risk"
            detail = "This scan did not surface strong signs of account-session theft, but clean-device review is still smart if the user ran the malware."
            color = YELLOW

        return {
            "score": score,
            "label": label,
            "detail": detail,
            "color": color,
        }

    def finding_breakdown(self):
        confirmed_categories = PERSISTENCE_THREAT_CATEGORIES | PROCESS_REMEDIATION_CATEGORIES | FILE_REMEDIATION_CATEGORIES
        confirmed = 0
        review = 0
        other = 0

        for threat in self.threats:
            if threat.category in MANUAL_REVIEW_CATEGORIES:
                review += 1
            elif threat.category in confirmed_categories or threat.severity in {"CRITICAL", "HIGH"}:
                confirmed += 1
            else:
                other += 1

        return {
            "confirmed": confirmed,
            "review": review,
            "other": other,
        }

    def build_account_recovery_plan(self, exposure=None):
        exposure = exposure or self.assess_account_exposure()
        notes_blob = " ".join(f"{desc} {path}".lower() for desc, path in self.exposure_notes)
        touched_discord = "discord" in notes_blob
        touched_browser = any(token in notes_blob for token in ("chrome", "edge", "firefox", "brave", "opera"))
        touched_wallet = any(token in notes_blob for token in ("wallet", "metamask", "crypto"))

        lines = [
            "ACCOUNT RECOVERY PLAN (do this from a CLEAN device)",
            "",
            "Core steps:",
            "  1. Change passwords for anything saved in the browser.",
            "  2. Revoke active sessions, not just passwords.",
            "  3. Re-enable MFA after passwords and sessions are reset.",
            "  4. Reboot the infected PC and run RenKill again before trusting it.",
        ]

        if touched_browser or exposure["score"] >= 25:
            lines += [
                "",
                "Browser / account steps:",
                "  1. Review signed-in Google, Microsoft, Steam, and banking sessions.",
                "  2. Turn off browser sync and clear synced data if suspicious state keeps returning.",
                "  3. Review extensions and saved payment details before signing back in.",
            ]

        if touched_discord or exposure["score"] >= 25:
            lines += [
                "",
                "Discord / social steps:",
                "  1. Revoke Discord sessions and review Authorized Apps.",
                "  2. Rotate the email passwords tied to Discord, Instagram, and socials.",
                "  3. Warn friends if spam links were sent from the account.",
            ]

        if touched_wallet or exposure["score"] >= 50:
            lines += [
                "",
                "Wallet / high-value steps:",
                "  1. Move assets to a fresh wallet with a new seed phrase.",
                "  2. Do not reuse the old wallet even if the PC looks clean.",
            ]

        lines += [
            "",
            f"Current account-risk readout: {exposure['score']}% - {exposure['label']}",
            exposure["detail"],
        ]
        return sanitize_for_display("\n".join(lines))

    def _threat_confidence_profile(self):
        categories = [t.category for t in self.threats]
        text_blob = " ".join(f"{t.category} {t.description} {t.path}".lower() for t in self.threats)

        renloader_markers = (
            "instaler", "lnstaier", "renpy", "archive.rpa", "script.rpyc",
            "iviewers.dll", "broker_crypt_v4_i386", "froodjurain",
            "vsdebugscriptagent170", "zoneind.exe", "chime.exe",
            "amatera", "instsatp_", "t11_asm", "antivmgpu",
            "antivmhypervisornames", "antivmmacs",
        )
        generic_markers = (
            "acr", "acrstealer", "lumma", "rhadamanthys", "vidar",
            "active c2 connection", "malicious scheduled task", "registry persistence"
        )

        renloader_hits = sum(1 for marker in renloader_markers if marker in text_blob)
        generic_stealer_hits = sum(1 for marker in generic_markers if marker in text_blob)

        renloader_hits += sum(1 for cat in categories if cat in {
            "Active Setup Persistence",
            "AppCert Persistence",
            "AppInit Persistence",
            "Explorer Hijack Review",
            "IFEO Persistence",
            "KnownDLLs Review",
            "Logon Script Persistence",
            "RenEngine Bundle",
            "Malicious File",
            "Malicious Archive/Script",
            "Malicious Service",
            "Hijacked Module Init",
            "Policy Persistence",
            "Persistence Artifact",
            "Persistence Process",
            "Persistence Staging Directory",
            "RunOnceEx Persistence",
            "SafeBoot Review",
            "Session Manager Review",
            "Startup-Launched Process",
            "Suspicious Temp Stage Directory",
            "Suspicious Loader Stage Directory",
            "Malicious Shortcut",
            "Campaign IOC Process",
            "Injected/Sideloaded DLL",
            "Execution Trace Anomaly",
            "Exact IOC Hash",
            "HijackLoader Stage Directory",
            "HijackLoader Stage Artifact",
            "Loader Container DLL",
            "Startup-Launched Process",
            "Suspicious Temp Stage Directory",
            "Winlogon Notify Review",
            "WMI Persistence",
            "Suspicious RenPy Loader Bundle",
        })
        generic_stealer_hits += sum(1 for cat in categories if cat in {
            "Active C2 Connection",
            "Defender Exclusion",
            "Disabled Startup Artifact",
            "Firewall Rule Review",
            "Malicious Scheduled Task",
            "Registry Persistence",
            "Stealer Script Host",
            "Paranoid Networked Process",
            "Startup Persistence Artifact",
            "Startup-Launched Process",
        })

        startup_layers = sum(1 for cat in categories if cat in {
            "Active Setup Persistence",
            "AppCert Persistence",
            "Startup Correlation Review",
            "Disabled Startup Artifact",
            "Explorer Hijack Review",
            "KnownDLLs Review",
            "Logon Script Persistence",
            "Malicious Scheduled Task",
            "Malicious Shortcut",
            "Policy Persistence",
            "Registry Persistence",
            "RunOnceEx Persistence",
            "SafeBoot Review",
            "Session Manager Review",
            "Shell Persistence Review",
            "Startup-Launched Process",
            "Winlogon Notify Review",
            "WMI Persistence",
        })
        persistence_layers = sum(1 for cat in categories if cat in PERSISTENCE_THREAT_CATEGORIES)
        review_layers = sum(1 for cat in categories if cat in MANUAL_REVIEW_CATEGORIES)

        if self._has_renloader_corroboration():
            renloader_hits += 2
        if "Startup Correlation Review" in categories:
            renloader_hits += 2
            generic_stealer_hits += 1
        if startup_layers >= 3:
            renloader_hits += 2
            generic_stealer_hits += 1
        elif startup_layers >= 2:
            renloader_hits += 1
        if persistence_layers >= 4:
            renloader_hits += 2
        elif persistence_layers >= 2:
            renloader_hits += 1

        suspicious_only = all(cat in {
            "Suspicious Userland Process",
            "Paranoid Masquerade Process",
            "Paranoid Script Host",
            "Suspicious Process",
            "Malicious Child Process",
            "Process in Temp",
        } for cat in categories)

        return {
            "categories": categories,
            "renloader_hits": renloader_hits,
            "generic_stealer_hits": generic_stealer_hits,
            "startup_layers": startup_layers,
            "persistence_layers": persistence_layers,
            "review_layers": review_layers,
            "suspicious_only": suspicious_only,
        }

    def summarize_threats(self):
        if not self.threats:
            self.last_summary = {
                "label": "No threats detected",
                "detail": "No malware-like artifacts matched the current RenKill rules.",
                "confidence": "clean",
                "color": GREEN,
            }
            return self.last_summary

        profile = self._threat_confidence_profile()
        renloader_hits = profile["renloader_hits"]
        generic_stealer_hits = profile["generic_stealer_hits"]
        suspicious_only = profile["suspicious_only"]
        startup_layers = profile["startup_layers"]

        if renloader_hits >= 6:
            label = "Probably RenLoader / RenEngine"
            if startup_layers >= 3:
                detail = "Multiple campaign-specific artifacts matched, with layered startup persistence consistent with the RenEngine/HijackLoader chain."
            else:
                detail = "Multiple campaign-specific artifacts matched the RenEngine/HijackLoader chain."
            confidence = "high"
            color = RED
        elif renloader_hits >= 3:
            label = "Possible RenLoader / RenEngine"
            if startup_layers >= 2:
                detail = "Some campaign-specific artifacts matched, and the startup state shows layered persistence that needs review."
            else:
                detail = "Some campaign-specific artifacts matched, but the chain is not fully confirmed."
            confidence = "medium"
            color = AMBER
        elif generic_stealer_hits >= 2:
            label = "Possible infostealer activity"
            detail = "Behavior looks malicious, but it does not clearly fingerprint RenLoader."
            confidence = "medium"
            color = AMBER
        elif suspicious_only:
            label = "Suspicious activity, weak RenLoader match"
            detail = "Only generic suspicious-process heuristics fired. Review before deleting everything."
            confidence = "low"
            color = YELLOW
        else:
            label = "Something else suspicious"
            detail = "Threats were found, but they do not strongly match the RenLoader profile."
            confidence = "low"
            color = YELLOW

        self.last_summary = {
            "label": label,
            "detail": detail,
            "confidence": confidence,
            "color": color,
            "renloader_hits": renloader_hits,
            "generic_hits": generic_stealer_hits,
            "startup_layers": startup_layers,
        }
        return self.last_summary

    def assess_cleanup_state(self):
        categories = {t.category for t in self.threats}
        critical = sum(1 for t in self.threats if t.severity == "CRITICAL")
        high = sum(1 for t in self.threats if t.severity == "HIGH")
        profile = self._threat_confidence_profile()
        persistence_compare = self.compare_post_cleanup_persistence()
        browser_compare = self.compare_post_cleanup_browser_state()
        renloader_hits = profile["renloader_hits"]
        startup_layers = profile["startup_layers"]
        persistence_layers = profile["persistence_layers"]
        review_layers = profile["review_layers"]

        if not self.threats:
            if self.post_cleanup_scan and self.rebooted_after_cleanup:
                if persistence_compare and persistence_compare["reappeared_count"]:
                    assessment = {
                        "score": 72,
                        "label": "Post-clean rescan is cleaner, but persistence drift returned",
                        "detail": "No direct malware hits remain, but one or more startup or persistence targets reappeared after cleanup and reboot.",
                        "color": AMBER,
                    }
                    self.cleanup_assessment = assessment
                    return assessment
                if browser_compare and browser_compare["reappeared_count"]:
                    assessment = {
                        "score": 84,
                        "label": "Post-clean rescan is cleaner, but browser residue came back",
                        "detail": "No direct malware hits remain, but suspicious browser extension or profile-state residue still reappeared after cleanup and reboot.",
                        "color": AMBER,
                    }
                    self.cleanup_assessment = assessment
                    return assessment
                assessment = {
                    "score": 96,
                    "label": "Post-clean rescan passed",
                    "detail": "No active RenLoader-style artifacts matched after cleanup, reboot, and rescan.",
                    "color": GREEN,
                }
            elif self.post_cleanup_scan:
                assessment = {
                    "score": 82,
                    "label": "Looks clean, reboot still pending",
                    "detail": "No active artifacts matched, but a reboot and one more scan are still recommended before calling the machine clean.",
                    "color": AMBER,
                }
            else:
                assessment = {
                    "score": 90,
                    "label": "No active artifacts found",
                    "detail": "This scan did not match active RenLoader-style files, processes, or persistence artifacts.",
                    "color": GREEN,
                }
            self.cleanup_assessment = assessment
            return assessment

        score = 100
        score -= min(48, critical * 12)
        score -= min(24, high * 4)
        score -= min(20, len(self.threats) * 2)

        if categories & PERSISTENCE_THREAT_CATEGORIES:
            score -= 24
        if categories & MANUAL_REVIEW_CATEGORIES:
            score -= 8
        if {"Active C2 Connection", "Defender Exclusion", "Malicious Service", "WMI Persistence"} & categories:
            score -= 14
        if startup_layers >= 3:
            score -= 16
        elif startup_layers >= 2:
            score -= 8
        if persistence_layers >= 4:
            score -= 10
        if renloader_hits >= 6:
            score -= 10
        elif renloader_hits >= 3:
            score -= 5
        if review_layers >= 4:
            score -= 4
        if self.post_cleanup_scan and self.rebooted_after_cleanup:
            score -= 12
            label = "Artifacts remain after reboot and rescan"
            detail = "Persistence or malware-linked artifacts are still being found after cleanup and reboot. Local eradication is not complete."
        elif self.post_cleanup_scan:
            score = min(score, 60)
            label = "Cleanup incomplete or reboot pending"
            detail = "Artifacts are still present, or the machine has not yet been rebooted and rescanned after cleanup."
        else:
            label = "Cleanup still has work to do"
            detail = "This scan still sees malware-linked artifacts or persistence. Do not consider the machine clean yet."

        if persistence_compare and self.post_cleanup_scan:
            if persistence_compare["suspicious_reappeared_count"] >= 2:
                score -= 14
                label = "Persistence reappeared after cleanup"
                detail = "Multiple startup or persistence targets came back after cleanup. The infection or its relaunch path is still alive."
            elif persistence_compare["reappeared_count"] >= 1:
                score -= 8
                detail += " A startup or persistence target reappeared after cleanup, so trust should stay low."
            elif persistence_compare["cleared_count"] >= 3 and self.rebooted_after_cleanup:
                score += 4
        if browser_compare and self.post_cleanup_scan:
            if browser_compare["reappeared_count"] >= 2:
                score -= 8
                detail += " Suspicious browser extension or profile-state residue also came back after cleanup."
            elif browser_compare["reappeared_count"] == 1:
                score -= 4
                detail += " One suspicious browser-state item came back after cleanup."
            elif browser_compare["cleared_count"] >= 2 and self.rebooted_after_cleanup:
                score += 2

        assessment = {
            "score": self._clamp_score(score),
            "label": label,
            "detail": detail,
            "color": RED if score < 50 else AMBER,
        }
        self.cleanup_assessment = assessment
        return assessment

    def _temp_paths(self):
        out = []
        for k in ("TEMP", "TMP"):
            v = os.environ.get(k, "")
            if v:
                out.append(v.lower())
        lapp = os.environ.get("LOCALAPPDATA", "")
        if lapp:
            out.append(os.path.join(lapp, "Temp").lower())
        return out

    def _in_temp(self, path):
        pl = path.lower()
        return any(t in pl for t in self._temp_paths() if t)

    @staticmethod
    def _startup_persistence_roots():
        roots = []
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("PROGRAMDATA", "")
        for candidate in (
            os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup") if appdata else "",
            os.path.join(programdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup") if programdata else "",
        ):
            if candidate:
                roots.append(candidate)
        return roots

    def _in_startup_persistence_root(self, path):
        normalized = self._normalized_path(path)
        if not normalized:
            return False
        for root in self._startup_persistence_roots():
            root_normalized = self._normalized_path(root).rstrip("\\/")
            if root_normalized and (normalized == root_normalized or normalized.startswith(root_normalized + "\\")):
                return True
        return False

    def _looks_like_suspicious_temp_stage_dir(self, dirpath, file_names_lower):
        normalized = self._normalized_path(dirpath)
        if not normalized or not self._in_temp(normalized):
            return False

        names = {str(name or "").lower() for name in (file_names_lower or []) if name}
        if not names:
            return False
        if self._is_local_tool_context(dirpath):
            return False
        if self._looks_like_hijackloader_stage_dir(dirpath, names):
            return True

        exe_names = [name for name in names if name.endswith(".exe")]
        sidecars = {os.path.splitext(name)[1] for name in names if os.path.splitext(name)[1]}
        if any(name in CAMPAIGN_FILENAMES or name in HIJACKLOADER_STAGE_FILES for name in names):
            return True
        if any(os.path.splitext(name)[0] in SUSPICIOUS_STARTUP_BASENAMES for name in exe_names):
            return True
        if self._contains_marker(" ".join(names), PROCESS_IOC_MARKERS):
            return True
        if exe_names and sidecars & TEMP_STAGE_SIDELOAD_EXTENSIONS:
            random_exe = any(self._looks_random(os.path.splitext(name)[0]) for name in exe_names)
            if random_exe or TEMP_STAGE_DIR_REGEX.search(normalized):
                return True
        return False

    @staticmethod
    def _version_tuple(value):
        match = VERSION_TAG_REGEX.search(str(value or ""))
        if not match:
            return ()
        return tuple(int(part) for part in match.groups())

    @staticmethod
    def _sha256_file(path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest().lower()

    @staticmethod
    def _normalize_cmdline(cmdline):
        if not cmdline:
            return ""
        if isinstance(cmdline, (list, tuple)):
            return " ".join(str(part) for part in cmdline if part)
        return str(cmdline)

    @staticmethod
    def _contains_marker(path, markers):
        pl = path.lower()
        return any(marker in pl for marker in markers)

    @staticmethod
    def _normalized_path(path):
        if not path:
            return ""
        try:
            return os.path.normcase(os.path.abspath(os.path.expandvars(path))).lower()
        except Exception:
            return str(path).lower()

    def _compute_local_tool_roots(self):
        candidates = {
            os.getcwd(),
            os.path.dirname(os.path.abspath(__file__)),
        }
        if getattr(sys, "executable", ""):
            candidates.add(os.path.dirname(os.path.abspath(sys.executable)))
        recovery_root = self._recovery_root()
        if recovery_root:
            candidates.add(recovery_root)

        roots = []
        for candidate in candidates:
            normalized = self._normalized_path(candidate).rstrip("\\/")
            if normalized:
                roots.append(normalized)
        return tuple(sorted(set(roots)))

    def _is_local_tool_path(self, path):
        normalized = self._normalized_path(path).rstrip("\\/")
        if not normalized:
            return False
        return any(normalized == root or normalized.startswith(root + "\\") for root in self._tool_roots)

    def _is_local_tool_context(self, *values):
        normalized_roots = self._tool_roots
        for value in values:
            raw = str(value or "").lower()
            if not raw:
                continue
            if any(root and root in raw for root in normalized_roots):
                return True
            if any(marker in raw for marker in LOCAL_TOOL_CONTEXT_MARKERS):
                return True
        return False

    def _is_project_like_path(self, path):
        current = self._normalized_path(path)
        if not current:
            return False

        probe = current if os.path.isdir(path) else os.path.dirname(current)
        for _ in range(4):
            if not probe or probe.endswith(":"):
                break
            try:
                for entry in os.listdir(probe):
                    lower = entry.lower()
                    if lower in PROJECT_INDICATOR_BASENAMES or lower.endswith(PROJECT_INDICATOR_SUFFIXES):
                        return True
            except Exception:
                pass
            parent = os.path.dirname(probe)
            if parent == probe:
                break
            probe = parent
        return False

    @staticmethod
    def _powershell_path():
        windir = os.environ.get("WINDIR", r"C:\Windows")
        return os.path.join(windir, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")

    @staticmethod
    def _schtasks_path():
        windir = os.environ.get("WINDIR", r"C:\Windows")
        candidates = [
            os.path.join(windir, "System32", "schtasks.exe"),
            os.path.join(windir, "Sysnative", "schtasks.exe"),
            os.path.join(windir, "SysWOW64", "schtasks.exe"),
            shutil.which("schtasks"),
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return "schtasks"

    @staticmethod
    def _extract_command_target(command_text):
        raw = (command_text or "").strip()
        if not raw:
            return ""
        if raw.startswith('"'):
            parts = raw.split('"')
            if len(parts) > 1:
                return parts[1]
        match = re.match(r"([A-Za-z]:\\[^ ]+\.(?:exe|dll|bat|cmd|ps1|vbs|js))", raw, re.IGNORECASE)
        return match.group(1) if match else raw.split()[0]

    @staticmethod
    def _split_command_text(command_text):
        raw = (command_text or "").strip()
        if not raw:
            return "", ""
        if raw.startswith('"'):
            parts = raw.split('"', 2)
            if len(parts) >= 2:
                target = parts[1]
                args = parts[2].strip() if len(parts) > 2 else ""
                return target, args
        match = re.match(r"([A-Za-z]:\\[^ ]+\.(?:exe|dll|bat|cmd|ps1|vbs|js))\s*(.*)", raw, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2).strip()
        parts = raw.split(None, 1)
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]

    @staticmethod
    def _is_pathlike_command_target(target):
        raw = str(target or "").strip()
        if not raw:
            return False
        if raw.startswith('"'):
            raw = raw.strip('"')
        return "\\" in raw or "/" in raw or bool(re.match(r"^[A-Za-z]:", raw))

    def _run_powershell(self, script, timeout=45):
        powershell = self._powershell_path()
        try:
            return subprocess.run(
                [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=0x08000000,
            )
        except FileNotFoundError:
            return None
        except Exception:
            return None

    def _run_powershell_json(self, script, timeout=45):
        result = self._run_powershell(script, timeout=timeout)
        if result is None:
            return None
        payload = (result.stdout or "").strip()
        if not payload:
            return []
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else [data]

    def _try_create_restore_point(self, label):
        if not is_admin():
            self.log("System Restore point skipped - administrator rights are required.", "WARN")
            return False

        description = f"{TOOL_NAME} {label}".strip()
        if len(description) > 60:
            description = description[:60]

        script = (
            "try { "
            f"Checkpoint-Computer -Description {self._powershell_quote(description)} "
            "-RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop; "
            "'OK' "
            "} catch { "
            "$msg = $_.Exception.Message; "
            "if (-not $msg) { $msg = $_.ToString() }; "
            "Write-Output $msg; "
            "exit 1 "
            "}"
        )
        result = self._run_powershell(script, timeout=120)
        if result is None:
            self.log("System Restore point could not be created because PowerShell was unavailable.", "WARN")
            self._record_recovery_note("system restore point was unavailable before cleanup")
            return False

        output = " ".join(
            part.strip()
            for part in ((result.stdout or "").strip(), (result.stderr or "").strip())
            if part and part.strip()
        )
        output_lower = output.lower()
        if result.returncode == 0:
            self.log("System Restore point created before changes.", "INFO")
            if self._recovery_session is not None:
                self._recovery_session["restore_point"] = {
                    "status": "created",
                    "description": description,
                    "recorded_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                self._persist_recovery_session()
            return True

        if "already been created within the past" in output_lower:
            self.log("System Restore point was skipped because Windows recently created one already.", "INFO")
            if self._recovery_session is not None:
                self._recovery_session["restore_point"] = {
                    "status": "recently_created",
                    "description": description,
                    "detail": output,
                    "recorded_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                self._persist_recovery_session()
            return False

        detail = output or "unknown Windows error"
        self.log(f"System Restore point could not be created: {detail}", "WARN")
        self._record_recovery_note(f"system restore point unavailable before cleanup: {detail}")
        if self._recovery_session is not None:
            self._recovery_session["restore_point"] = {
                "status": "unavailable",
                "description": description,
                "detail": detail,
                "recorded_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._persist_recovery_session()
        return False

    def _list_file_streams(self, path):
        quoted = self._powershell_quote(path)
        rows = self._run_powershell_json(
            "Get-Item -LiteralPath "
            + quoted
            + " -Stream * -ErrorAction SilentlyContinue | "
              "Select-Object Stream,Length | ConvertTo-Json -Compress",
            timeout=20,
        )
        if rows is None:
            return None
        streams = []
        for row in rows:
            name = str(row.get("Stream") or "").strip()
            if not name:
                continue
            lowered = name.lower()
            if lowered in {"::$data", "$data"}:
                continue
            if lowered.startswith("zone.identifier"):
                continue
            try:
                length = int(row.get("Length") or 0)
            except Exception:
                length = 0
            streams.append({"name": name, "length": length})
        return streams

    def _file_metadata(self, path):
        normalized = self._normalized_path(path)
        if not normalized or normalized in self._file_meta_cache:
            return self._file_meta_cache.get(normalized, {})
        if not os.path.isfile(path):
            self._file_meta_cache[normalized] = {}
            return {}

        escaped = path.replace("'", "''")
        rows = self._run_powershell_json(
            "$item = Get-Item -LiteralPath '" + escaped + "' -ErrorAction SilentlyContinue; "
            "if ($item -and $item.VersionInfo) { "
            "[pscustomobject]@{ "
            "CompanyName=$item.VersionInfo.CompanyName; "
            "FileDescription=$item.VersionInfo.FileDescription; "
            "ProductName=$item.VersionInfo.ProductName; "
            "OriginalFilename=$item.VersionInfo.OriginalFilename "
            "} | ConvertTo-Json -Compress }",
            timeout=15,
        )
        meta = rows[0] if rows else {}
        cleaned = {
            "company": str(meta.get("CompanyName") or "").strip().lower(),
            "description": str(meta.get("FileDescription") or "").strip().lower(),
            "product": str(meta.get("ProductName") or "").strip().lower(),
            "original": str(meta.get("OriginalFilename") or "").strip().lower(),
        }
        self._file_meta_cache[normalized] = cleaned
        return cleaned

    def _has_trusted_file_metadata(self, path):
        if not path or self._has_strong_campaign_context(path):
            return False
        meta = self._file_metadata(path)
        if not meta:
            return False

        company_blob = " ".join(filter(None, (meta["company"], meta["product"])))
        if any(token in company_blob for token in TRUSTED_COMPANY_TOKENS):
            return True

        descriptor_blob = " ".join(filter(None, (meta["description"], meta["original"])))
        return any(token in descriptor_blob for token in TRUSTED_FILE_DESCRIPTION_TOKENS)

    def _file_metadata_matches(self, path, tokens):
        if not path:
            return False
        meta = self._file_metadata(path)
        if not meta:
            return False
        blob = " ".join(filter(None, (meta["company"], meta["product"], meta["description"], meta["original"])))
        return any(token in blob for token in tokens)

    def _has_strong_campaign_context(self, *values):
        blob = " ".join(str(value).lower() for value in values if value)
        if not blob:
            return False
        if self._contains_marker(blob, STRONG_CAMPAIGN_MARKERS):
            return True
        for token in re.split(r"[\\/\s\"']+", blob):
            base = os.path.basename(token).lower()
            if base in MALICIOUS_FILENAMES or base in CAMPAIGN_FILENAMES or base in HIJACKLOADER_STAGE_FILES:
                return True
        return False

    def _is_trusted_vendor_path(self, path):
        pl = self._normalized_path(path)
        return bool(pl) and any(marker in pl for marker in TRUSTED_VENDOR_PATH_MARKERS)

    def _is_legit_netsupport_install_path(self, path):
        normalized = self._normalized_path(path)
        return bool(normalized) and any(marker in normalized for marker in NETSUPPORT_TRUSTED_PATH_MARKERS)

    def _looks_like_suspicious_netsupport_path(self, path, allow_metadata=False):
        normalized = self._normalized_path(path)
        if not normalized:
            return False
        if self._is_legit_netsupport_install_path(normalized):
            return False

        base = os.path.basename(normalized).lower()
        metadata_hit = bool(allow_metadata and self._file_metadata_matches(path, NETSUPPORT_METADATA_TOKENS))
        name_hit = base in NETSUPPORT_STAGE_FILENAMES or "netsupport" in normalized
        if not name_hit and not metadata_hit:
            return False

        suspicious_location = (
            any(marker in normalized for marker in NETSUPPORT_SUSPICIOUS_PATH_MARKERS)
            or self._path_in_user_writable_exec_zone(normalized)
        )
        return suspicious_location

    def _is_protected_system_path(self, path):
        pl = self._normalized_path(path)
        return bool(pl) and any(marker in pl for marker in PROTECTED_SYSTEM_PATH_MARKERS)

    def _should_consider_metadata_trust(self, path):
        normalized = self._normalized_path(path)
        if not normalized or self._has_strong_campaign_context(normalized):
            return False
        if self._is_trusted_vendor_path(normalized) or self._is_protected_system_path(normalized):
            return False
        return any(marker in normalized for marker in COMMON_USERLAND_EXEC_MARKERS)

    def _is_safe_process_context(self, pname, pexe, cmdline="", allow_metadata=False):
        if self._has_strong_campaign_context(pname, pexe, cmdline):
            return False
        if self._is_local_tool_context(pexe, cmdline):
            return True
        if pname in TRUSTED_PROCESS_NAMES:
            return True
        if self._is_trusted_vendor_path(pexe) or self._is_protected_system_path(pexe):
            return True
        if pname in SAFE_PROCESS_NAMES:
            if not pexe:
                return True
            return not self._path_in_user_writable_exec_zone(self._normalized_path(pexe))
        if allow_metadata and self._should_consider_metadata_trust(pexe):
            return self._has_trusted_file_metadata(pexe)
        return False

    def _is_broad_directory_target(self, path):
        norm = self._normalized_path(path)
        if not norm:
            return True
        base = os.path.basename(os.path.normpath(norm)).lower()
        if base in NON_REMOVABLE_DIR_BASENAMES:
            return True

        protected_roots = [
            os.environ.get("WINDIR", ""),
            os.environ.get("PROGRAMDATA", ""),
            os.environ.get("APPDATA", ""),
            os.environ.get("LOCALAPPDATA", ""),
            os.environ.get("USERPROFILE", ""),
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
        ]
        return any(root and norm == self._normalized_path(root) for root in protected_roots)

    def _should_block_path_remediation(self, path, *, is_dir=False):
        if not path:
            return True
        if is_dir and self._is_broad_directory_target(path):
            return True
        if self._has_strong_campaign_context(path):
            return False
        return self._is_trusted_vendor_path(path) or self._is_protected_system_path(path)

    def _log_safety_block(self, action, target):
        self.log(f"Safety block: refusing to {action}: {target}", "WARN")

    @staticmethod
    def _startup_shortcut_roots():
        roots = []
        profile = os.environ.get("USERPROFILE", "")
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("PROGRAMDATA", "")
        public_root = os.environ.get("PUBLIC", "")

        for candidate in (
            os.path.join(profile, "Desktop") if profile else "",
            os.path.join(public_root, "Desktop") if public_root else "",
            os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup") if appdata else "",
            os.path.join(programdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup") if programdata else "",
        ):
            if candidate and os.path.isdir(candidate):
                roots.append(candidate)
        return roots

    @staticmethod
    def _is_disabled_startupapproved_value(data):
        if not isinstance(data, (bytes, bytearray)) or not data:
            return False
        return data[0] in STARTUPAPPROVED_DISABLED_STATES

    def _looks_suspicious_startup_item_name(self, item_name):
        raw = str(item_name or "").strip()
        if not raw:
            return False
        stem_raw = os.path.splitext(os.path.basename(raw))[0]
        stem = stem_raw.lower()
        if not stem:
            return False
        if any(token in stem for token in STARTUP_NAME_SAFE_TOKENS):
            return False
        if self._has_strong_campaign_context(stem):
            return True
        if self._looks_random(stem_raw):
            return True
        if stem_raw.isalnum() and 7 <= len(stem_raw) <= 16:
            has_upper = any(char.isupper() for char in stem_raw)
            has_lower = any(char.islower() for char in stem_raw)
            vowels = sum(1 for char in stem if char in "aeiou")
            if has_upper and has_lower and vowels <= max(2, len(stem) // 5):
                return True
        return False

    @staticmethod
    def _contains_remote_loader_marker(text):
        lowered = str(text or "").lower()
        if not lowered:
            return False
        return any(marker in lowered for marker in SCRIPT_LURE_REMOTE_MARKERS) or bool(IPV4_HTTP_REGEX.search(lowered))

    def _looks_like_startup_script_dropper(self, path):
        path = str(path or "")
        ext = os.path.splitext(path)[1].lower()
        if ext not in STARTUP_SCRIPT_EXTENSIONS:
            return False
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                sample = handle.read(8192)
        except Exception:
            return False

        lowered = sample.lower()
        if any(marker in lowered for marker in SAFE_SCRIPT_CONTENT_MARKERS):
            return False
        if not self._contains_remote_loader_marker(lowered):
            return False
        return any(token in lowered for token in STARTUP_DOWNLOADER_TOKENS) or self._has_strong_campaign_context(lowered)

    def _evaluate_startup_file_entry(self, path):
        path = str(path or "")
        if not path:
            return None
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        stem = os.path.splitext(name)[0]
        normalized = self._normalized_path(path)
        if self._is_local_tool_context(path):
            return None
        if self._has_strong_campaign_context(path):
            return "CRITICAL", "Startup Persistence Artifact", f"Startup folder payload references campaign artifacts: {path}"
        if self._looks_like_startup_script_dropper(path):
            return "CRITICAL", "Startup Persistence Artifact", f"Startup script or launcher appears to download or launch a remote payload: {path}"
        if ext in STARTUP_SCRIPT_EXTENSIONS and self._contains_remote_loader_marker(path):
            return "HIGH", "Startup Persistence Artifact", f"Startup entry contains a remote URL or IP loader marker: {path}"
        if ext == ".exe":
            if self._is_safe_process_context(name.lower(), path, allow_metadata=True):
                return None
            if (
                stem.lower() in SUSPICIOUS_STARTUP_BASENAMES
                or self._looks_random(stem)
                or self._in_temp(normalized)
            ):
                return "HIGH", "Startup Persistence Artifact", f"Direct executable in Startup folder looks suspicious and should be removed: {path}"
        return None

    def _collect_shortcut_rows(self):
        if self._shortcut_scan_rows is not None:
            return self._shortcut_scan_rows

        roots = self._startup_shortcut_roots()
        if not roots:
            self._shortcut_scan_rows = []
            return self._shortcut_scan_rows

        escaped_roots = ", ".join("'" + root.replace("'", "''") + "'" for root in roots)
        rows = self._run_powershell_json(
            "$roots = @(" + escaped_roots + "); "
            "$roots = $roots | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique; "
            "if (-not $roots) { return }; "
            "$shell = New-Object -ComObject WScript.Shell; "
            "$items = foreach ($root in $roots) { "
            "Get-ChildItem -LiteralPath $root -Filter *.lnk -File -ErrorAction SilentlyContinue | ForEach-Object { "
            "try { "
            "$shortcut = $shell.CreateShortcut($_.FullName); "
            "[pscustomobject]@{ "
            "Path=$_.FullName; "
            "Name=$_.Name; "
            "TargetPath=$shortcut.TargetPath; "
            "Arguments=$shortcut.Arguments; "
            "WorkingDirectory=$shortcut.WorkingDirectory "
            "} "
            "} catch { } "
            "} "
            "}; "
            "$items | ConvertTo-Json -Compress",
            timeout=45,
        )
        self._shortcut_scan_rows = rows or []
        return self._shortcut_scan_rows

    def _evaluate_shortcut_entry(self, path, name, target_path, arguments="", working_directory=""):
        path = str(path or "")
        name = str(name or "")
        target_path = str(target_path or "")
        arguments = str(arguments or "")
        working_directory = str(working_directory or "")
        blob = " ".join(part for part in (path, name, target_path, arguments, working_directory) if part)
        if not blob:
            return None

        if self._has_strong_campaign_context(blob):
            return (
                "CRITICAL",
                "Malicious Shortcut",
                f"Shortcut references RenEngine/HijackLoader artifacts: {path}",
            )

        target_exe = os.path.basename(target_path).lower()
        normalized_target = self._normalized_path(target_path)
        args_lower = arguments.lower()
        name_lower = name.lower()
        base_name = os.path.splitext(target_exe)[0]
        temp_launcher_score = self._score_startup_temp_launcher(target_path, arguments, working_directory)

        if self._is_startup_shortcut_path(path) and temp_launcher_score >= 3:
            severity = "CRITICAL" if temp_launcher_score >= 5 else "HIGH"
            description = f"Startup shortcut points to temp-stage launcher: {path} -> {target_path}"
            if self._file_metadata_matches(target_path, IMYFONE_COMPANY_TOKENS):
                description += "  (iMyFone-signed temp launcher pattern)"
            return severity, "Malicious Shortcut", description

        if target_exe in SHORTCUT_SCRIPT_HOSTS and (
            self._has_strong_campaign_context(arguments)
            or self._contains_remote_loader_marker(arguments)
            or any(marker in args_lower for marker in COMMON_USERLAND_EXEC_MARKERS)
            or any(ext in args_lower for ext in (".bat", ".cmd", ".hta", ".js", ".ps1", ".vbs"))
        ):
            return (
                "HIGH",
                "Malicious Shortcut",
                f"Shortcut launches a script host with suspicious arguments: {path}",
            )

        risky_target = (
            target_path
            and self._path_in_user_writable_exec_zone(normalized_target)
            and (
                self._contains_marker(normalized_target, PROCESS_IOC_MARKERS)
                or self._in_temp(normalized_target)
                or self._looks_random(base_name)
            )
        )
        if risky_target:
            if not self._is_safe_process_context(target_exe, target_path, arguments, allow_metadata=True):
                return (
                    "HIGH",
                    "Malicious Shortcut",
                    f"Shortcut target points to suspicious user-writable executable: {path} -> {target_path}",
                )

        if any(token in name_lower for token in BROWSER_SHORTCUT_TOKENS) and target_exe in SHORTCUT_SCRIPT_HOSTS:
            return (
                "HIGH",
                "Malicious Shortcut",
                f"Browser-style shortcut is routed through a script host: {path}",
            )

        if any(token in name_lower for token in BROWSER_SHORTCUT_TOKENS):
            if target_exe not in KNOWN_BROWSER_TARGETS and risky_target:
                return (
                    "HIGH",
                    "Malicious Shortcut",
                    f"Browser-style shortcut target is redirected to suspicious executable: {path}",
                )

        return None

    def _is_risky_defender_exclusion(self, kind, value):
        raw = str(value or "").strip()
        if not raw:
            return False
        if self._has_strong_campaign_context(raw):
            return True

        normalized = self._normalized_path(raw)
        risky_roots = {
            self._normalized_path(os.environ.get("PROGRAMDATA", "")),
            self._normalized_path(os.environ.get("APPDATA", "")),
            self._normalized_path(os.environ.get("LOCALAPPDATA", "")),
            self._normalized_path(os.environ.get("TEMP", "")),
            self._normalized_path(os.environ.get("TMP", "")),
            self._normalized_path(os.environ.get("USERPROFILE", "")),
        }
        risky_roots.discard("")

        if kind == "Extension":
            return raw.lower() in {".bat", ".cmd", ".dll", ".exe", ".hta", ".js", ".ps1", ".vbs"}

        target = self._extract_command_target(raw)
        normalized_target = self._normalized_path(target)
        if normalized_target in risky_roots:
            return True

        if kind == "Process":
            target_name = os.path.basename(normalized_target)
            return bool(
                normalized_target
                and self._path_in_user_writable_exec_zone(normalized_target)
                and not self._is_safe_process_context(target_name, target, raw, allow_metadata=True)
            )

        return bool(normalized and normalized in risky_roots)

    def _get_process_context(self, pid):
        if not PSUTIL_OK:
            return "", "", ""
        try:
            proc = psutil.Process(pid)
            pname = self._safe_proc_name(proc)
            pexe = self._safe_proc_exe(proc)
            cmdline = self._safe_proc_cmdline(proc)
            return pname, pexe, cmdline
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "", "", ""
        except Exception:
            return "", "", ""

    @staticmethod
    def _safe_proc_name(proc):
        try:
            return (proc.name() or "").lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            return ""
        except Exception:
            return ""

    @staticmethod
    def _safe_proc_ppid(proc):
        try:
            return proc.ppid() or 0
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            return 0
        except Exception:
            return 0

    @staticmethod
    def _safe_proc_exe(proc):
        try:
            return proc.exe() or ""
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            return ""
        except Exception:
            return ""

    def _safe_proc_cmdline(self, proc):
        try:
            return self._normalize_cmdline(proc.cmdline())
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            return ""
        except Exception:
            return ""

    def _should_block_process_remediation(self, pid):
        pname, pexe, cmdline = self._get_process_context(pid)
        target = pexe or cmdline or pname or f"PID {pid}"
        if not (pname or pexe or cmdline):
            return False, target
        if self._is_local_tool_context(pexe, cmdline):
            return True, target
        if self._is_protected_core_process(pname, pexe) or self._is_protected_security_process(pname, pexe):
            return True, target
        if self._has_strong_campaign_context(pname, pexe, cmdline):
            return False, target
        return self._is_safe_process_context(pname, pexe, cmdline, allow_metadata=True), target

    @staticmethod
    def _is_user_visible_root(root):
        rl = root.lower()
        return any(token in rl for token in ("\\downloads", "\\desktop", "\\documents"))

    @staticmethod
    def _file_contains_ascii_or_utf16le(path, needles):
        try:
            with open(path, "rb") as handle:
                data = handle.read(65536).lower()
            for needle in needles:
                raw = needle.lower().encode("ascii", "ignore")
                if raw and (raw in data or raw.decode("ascii").encode("utf-16le") in data):
                    return True
        except Exception:
            return False
        return False

    @staticmethod
    def _read_small_text_blob(path, limit=131072):
        try:
            with open(path, "rb") as handle:
                data = handle.read(limit)
        except Exception:
            return ""

        if not data:
            return ""

        if b"\x00" in data:
            try:
                return data.decode("utf-16le", "ignore").lower()
            except Exception:
                return ""
        return data.decode("utf-8", "ignore").lower()

    def _script_has_lure_content(self, path):
        if self._is_local_tool_path(path) or self._is_project_like_path(path):
            return False

        text = self._read_small_text_blob(path)
        if not text:
            return False
        if any(marker in text for marker in SAFE_SCRIPT_CONTENT_MARKERS):
            return False

        strong_hits = sum(1 for token in SOURCE_LURE_KEYWORDS if token in text)
        remote_hit = any(marker in text for marker in SCRIPT_LURE_REMOTE_MARKERS)
        ext = os.path.splitext(str(path or "").lower())[1]
        if ext in {".html", ".htm", ".url"}:
            return remote_hit and strong_hits >= 1
        return strong_hits >= 2 or (remote_hit and strong_hits >= 1)

    def _value_has_malware_signal(self, value):
        raw = self._normalize_cmdline(value)
        lowered = raw.lower()
        target = self._extract_command_target(raw)
        normalized_target = self._normalized_path(target)

        if self._is_local_tool_context(raw, target):
            return False
        if self._has_strong_campaign_context(raw):
            return True
        if normalized_target and not self._is_trusted_vendor_path(normalized_target) and not self._has_trusted_file_metadata(target):
            if any(marker in normalized_target for marker in COMMON_USERLAND_EXEC_MARKERS):
                base = os.path.splitext(os.path.basename(normalized_target))[0]
                if (
                    self._looks_random(base)
                    and any(ext in normalized_target for ext in (".exe", ".dll", ".cmd", ".bat", ".ps1", ".vbs", ".js"))
                ) or self._contains_marker(normalized_target, PROCESS_IOC_MARKERS):
                    return True
        if GODOT_APP_USERDATA_MARKER in normalized_target and any(marker in lowered for marker in ASAR_ARGUMENT_MARKERS):
            return True
        if normalized_target and self._looks_like_suspicious_netsupport_path(normalized_target, allow_metadata=True):
            return True
        if self._looks_like_temp_stage_launcher(normalized_target):
            return True
        return any(pattern in lowered for pattern in SUSPICIOUS_REG_PATTERNS)

    @staticmethod
    def _looks_like_temp_stage_launcher(path):
        normalized = str(path or "").lower()
        if not normalized.endswith(".exe"):
            return False
        return bool(TEMP_STAGE_DIR_REGEX.search(normalized))

    @staticmethod
    def _is_startup_shortcut_path(path):
        normalized = str(path or "").lower()
        return "\\start menu\\programs\\startup\\" in normalized

    def _score_startup_temp_launcher(self, target_path, arguments="", working_directory=""):
        normalized_target = self._normalized_path(target_path)
        if not self._looks_like_temp_stage_launcher(normalized_target):
            return 0

        score = 2
        target_name = os.path.splitext(os.path.basename(normalized_target))[0]
        if self._looks_random(target_name):
            score += 1

        normalized_workdir = self._normalized_path(working_directory)
        target_dir = os.path.dirname(normalized_target)
        if normalized_workdir and normalized_workdir == target_dir:
            score += 1

        args_lower = self._normalize_cmdline(arguments).lower()
        if args_lower and (
            self._contains_marker(args_lower, PROCESS_IOC_MARKERS)
            or any(ext in args_lower for ext in (".asar", ".dll", ".ps1", ".vbs", ".js"))
        ):
            score += 1

        if self._file_metadata_matches(target_path, IMYFONE_COMPANY_TOKENS):
            score += 2

        return score

    def _looks_like_godot_asar_task(self, executable, arguments, working_directory=""):
        normalized_executable = self._normalized_path(executable)
        if GODOT_APP_USERDATA_MARKER not in normalized_executable:
            return False

        argument_blob = self._normalize_cmdline(arguments).lower()
        if not any(marker in argument_blob for marker in ASAR_ARGUMENT_MARKERS):
            return False

        normalized_workdir = self._normalized_path(working_directory)
        if normalized_workdir and GODOT_APP_USERDATA_MARKER not in normalized_workdir and not self._path_in_user_writable_exec_zone(normalized_workdir):
            return False

        return normalized_executable.endswith(".exe")

    def _looks_suspicious_service(self, service_name, display_name, path_name):
        blob = " ".join(part for part in (service_name, display_name, path_name) if part)
        executable = self._extract_command_target(path_name)
        normalized_executable = self._normalized_path(executable)
        base = os.path.splitext(os.path.basename(normalized_executable))[0]

        if self._has_strong_campaign_context(blob):
            return "CRITICAL", "Malicious Service", f"Service references RenLoader/HijackLoader artifacts: {service_name} -> {path_name}"
        if not executable or self._is_safe_process_context(service_name.lower(), executable, path_name) or self._has_trusted_file_metadata(executable):
            return None
        if self._looks_like_suspicious_netsupport_path(executable, allow_metadata=True):
            return "HIGH", "Malicious Service", f"Service points at a NetSupport-style remote-control payload in a suspicious location: {service_name} -> {path_name}"
        if any(marker in normalized_executable for marker in COMMON_USERLAND_EXEC_MARKERS) and (
            self._looks_random(base) or self._contains_marker(normalized_executable, PROCESS_IOC_MARKERS)
        ):
            return "HIGH", "Malicious Service", f"Service points at suspicious user-writable executable: {service_name} -> {path_name}"
        return None

    def _collect_scheduled_task_rows(self):
        if self._scheduled_task_rows is not None:
            return self._scheduled_task_rows

        rows = self._run_powershell_json(
            "$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object { "
            "$task = $_; "
            "foreach ($action in $task.Actions) { "
            "[pscustomobject]@{ "
            "TaskName=$task.TaskName; "
            "TaskPath=$task.TaskPath; "
            "Execute=$action.Execute; "
            "Arguments=$action.Arguments; "
            "WorkingDirectory=$action.WorkingDirectory; "
            "UserId=$task.Principal.UserId; "
            "State=[string]$task.State "
            "} "
            "} "
            "}; "
            "$tasks | ConvertTo-Json -Compress",
            timeout=60,
        )
        if not rows:
            rows = []
            try:
                result = subprocess.run(
                    [self._schtasks_path(), "/query", "/fo", "CSV", "/v"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=0x08000000,
                )
                reader = csv.DictReader(result.stdout.splitlines())
                for item in reader:
                    task_name = str(item.get("TaskName") or item.get("Task Name") or "").strip()
                    command_text = str(item.get("Task To Run") or item.get("Actions") or "").strip()
                    execute, arguments = self._split_command_text(command_text)
                    rows.append(
                        {
                            "TaskName": task_name,
                            "TaskPath": "",
                            "Execute": execute,
                            "Arguments": arguments,
                            "WorkingDirectory": str(item.get("Start In") or item.get("Start In (Optional)") or "").strip(),
                            "UserId": str(item.get("Run As User") or "").strip(),
                            "State": str(item.get("Status") or item.get("Scheduled Task State") or "").strip(),
                        }
                    )
            except Exception:
                rows = []
        self._scheduled_task_rows = rows or []
        return self._scheduled_task_rows

    def _collect_run_autorun_rows(self):
        if self._autorun_rows is not None:
            return self._autorun_rows

        rows = []
        if not WINREG_OK:
            self._autorun_rows = rows
            return rows

        locations = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
        ]

        for hive, subkey, hive_name in locations:
            try:
                key = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            index = 0
            while True:
                try:
                    value_name, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                rows.append(
                    {
                        "HiveName": hive_name,
                        "Subkey": subkey,
                        "ValueName": str(value_name or ""),
                        "Value": str(value or ""),
                    }
                )

            try:
                winreg.CloseKey(key)
            except Exception:
                pass

        self._autorun_rows = rows
        return rows

    def _collect_policy_persistence_rows(self):
        if self._policy_rows is not None:
            return self._policy_rows

        rows = []
        if not WINREG_OK:
            self._policy_rows = rows
            return rows

        explorer_run_locations = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run", "HKLM"),
        ]
        for hive, subkey, hive_name in explorer_run_locations:
            try:
                key = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            index = 0
            while True:
                try:
                    value_name, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                rows.append(
                    {
                        "Kind": "ExplorerRun",
                        "Hive": hive,
                        "HiveName": hive_name,
                        "Subkey": subkey,
                        "ValueName": str(value_name or ""),
                        "Value": str(value or ""),
                    }
                )

            try:
                winreg.CloseKey(key)
            except Exception:
                pass

        single_value_locations = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Command Processor", "Autorun", "CmdAutorun", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Command Processor", "Autorun", "CmdAutorun", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Command Processor", "Autorun", "CmdAutorun", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "Shell", "PolicyShell", "HKLM"),
        ]
        for hive, subkey, value_name, kind, hive_name in single_value_locations:
            try:
                key = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            try:
                value = str(winreg.QueryValueEx(key, value_name)[0] or "")
            except OSError:
                value = ""
            finally:
                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass

            rows.append(
                {
                    "Kind": kind,
                    "Hive": hive,
                    "HiveName": hive_name,
                    "Subkey": subkey,
                    "ValueName": value_name,
                    "Value": value,
                }
            )

        self._policy_rows = rows
        return rows

    def _collect_runonceex_rows(self):
        if self._runonceex_rows is not None:
            return self._runonceex_rows

        rows = []
        if not WINREG_OK:
            self._runonceex_rows = rows
            return rows

        locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnceEx", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnceEx", "HKLM"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnceEx", "HKCU"),
        ]

        for hive, subkey, hive_name in locations:
            try:
                root = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            try:
                index = 0
                while True:
                    try:
                        child_name = winreg.EnumKey(root, index)
                    except OSError:
                        break
                    index += 1
                    child_path = subkey + "\\" + child_name
                    try:
                        child = winreg.OpenKey(hive, child_path)
                    except (FileNotFoundError, PermissionError):
                        continue

                    try:
                        value_index = 0
                        while True:
                            try:
                                value_name, value, _ = winreg.EnumValue(child, value_index)
                            except OSError:
                                break
                            value_index += 1
                            rows.append(
                                {
                                    "Hive": hive,
                                    "HiveName": hive_name,
                                    "Subkey": child_path,
                                    "ValueName": str(value_name or ""),
                                    "Value": str(value or ""),
                                }
                            )
                    finally:
                        try:
                            winreg.CloseKey(child)
                        except Exception:
                            pass
            finally:
                try:
                    winreg.CloseKey(root)
                except Exception:
                    pass

        self._runonceex_rows = rows
        return rows

    def _collect_active_setup_rows(self):
        if self._active_setup_rows is not None:
            return self._active_setup_rows

        rows = []
        if not WINREG_OK:
            self._active_setup_rows = rows
            return rows

        locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Active Setup\Installed Components", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Active Setup\Installed Components", "HKLM"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Active Setup\Installed Components", "HKCU"),
        ]

        for hive, subkey, hive_name in locations:
            try:
                root = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            index = 0
            while True:
                try:
                    component_name = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                component_path = subkey + "\\" + component_name
                try:
                    child = winreg.OpenKey(hive, component_path)
                except (FileNotFoundError, PermissionError):
                    continue

                try:
                    try:
                        stub_path = str(winreg.QueryValueEx(child, "StubPath")[0] or "")
                    except OSError:
                        stub_path = ""
                    try:
                        component_label = str(winreg.QueryValueEx(child, "")[0] or "")
                    except OSError:
                        component_label = ""
                finally:
                    try:
                        winreg.CloseKey(child)
                    except Exception:
                        pass

                if stub_path:
                    rows.append(
                        {
                            "Hive": hive,
                            "HiveName": hive_name,
                            "Subkey": component_path,
                            "ComponentName": component_name,
                            "ComponentLabel": component_label,
                            "StubPath": stub_path,
                        }
                    )

            try:
                winreg.CloseKey(root)
            except Exception:
                pass

        self._active_setup_rows = rows
        return rows

    def _collect_disabled_startup_rows(self):
        if self._disabled_startup_rows is not None:
            return self._disabled_startup_rows

        rows = []
        if not WINREG_OK:
            self._disabled_startup_rows = rows
            return rows

        shortcut_rows = {}
        for row in self._collect_shortcut_rows():
            shortcut_path = self._normalized_path(row.get("Path"))
            if shortcut_path:
                shortcut_rows[shortcut_path] = row

        actual_run_keys = {
            "Run": [
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
            ],
            "Run32": [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
            ],
        }

        startupapproved_roots = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved", "HKLM"),
        ]

        for hive, root, hive_name in startupapproved_roots:
            for child_name in ("Run", "Run32", "StartupFolder"):
                subkey = root + "\\" + child_name
                try:
                    key = winreg.OpenKey(hive, subkey)
                except (FileNotFoundError, PermissionError):
                    continue

                index = 0
                while True:
                    try:
                        item_name, binary_value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    index += 1

                    if not self._is_disabled_startupapproved_value(binary_value):
                        continue

                    if child_name in actual_run_keys:
                        for run_hive, run_key, run_hive_name in actual_run_keys[child_name]:
                            try:
                                run_handle = winreg.OpenKey(run_hive, run_key)
                                run_value = str(winreg.QueryValueEx(run_handle, item_name)[0] or "")
                                winreg.CloseKey(run_handle)
                            except (FileNotFoundError, PermissionError, OSError):
                                continue

                            rows.append(
                                {
                                    "Kind": "autorun",
                                    "Path": f"{run_hive_name}\\{run_key}[{item_name}]",
                                    "Command": run_value,
                                    "SourceLabel": f"disabled-startup:{child_name.lower()}",
                                    "ApprovalKey": f"{hive_name}\\{subkey}[{item_name}]",
                                }
                            )
                            break
                        continue

                    for startup_root in self._startup_shortcut_roots():
                        shortcut_path = self._normalized_path(os.path.join(startup_root, item_name))
                        row = shortcut_rows.get(shortcut_path)
                        if not row:
                            continue
                        rows.append(
                            {
                                "Kind": "shortcut",
                                "Path": str(row.get("Path") or ""),
                                "Command": str(row.get("TargetPath") or ""),
                                "Arguments": str(row.get("Arguments") or ""),
                                "WorkingDirectory": str(row.get("WorkingDirectory") or ""),
                                "SourceLabel": "disabled-startup:startupfolder",
                                "ApprovalKey": f"{hive_name}\\{subkey}[{item_name}]",
                            }
                        )
                        break

                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass

        self._disabled_startup_rows = rows
        return rows

    def _collect_wmi_persistence_rows(self):
        if self._wmi_rows is not None:
            return self._wmi_rows

        rows = []
        queries = (
            ("__EventFilter", "Get-WmiObject -Namespace root\\subscription -Class __EventFilter | Select-Object Name,Query,EventNamespace | ConvertTo-Json -Compress"),
            ("CommandLineEventConsumer", "Get-WmiObject -Namespace root\\subscription -Class CommandLineEventConsumer | Select-Object Name,CommandLineTemplate,ExecutablePath | ConvertTo-Json -Compress"),
            ("ActiveScriptEventConsumer", "Get-WmiObject -Namespace root\\subscription -Class ActiveScriptEventConsumer | Select-Object Name,ScriptingEngine,ScriptText | ConvertTo-Json -Compress"),
        )

        for class_name, script in queries:
            query_rows = self._run_powershell_json(script, timeout=45)
            if query_rows is None:
                self._wmi_rows = []
                return self._wmi_rows
            for row in query_rows:
                item = {"ClassName": class_name}
                item.update(row)
                rows.append(item)

        self._wmi_rows = rows
        return rows

    def _collect_shell_persistence_rows(self):
        if self._shell_rows is not None:
            return self._shell_rows

        rows = []
        if not WINREG_OK:
            self._shell_rows = rows
            return rows

        locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "Shell", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "Userinit", "HKLM"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Windows", "Load", "HKCU"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Windows", "Run", "HKCU"),
        ]

        for hive, subkey, value_name, hive_name in locations:
            try:
                key = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            try:
                value = str(winreg.QueryValueEx(key, value_name)[0] or "")
            except OSError:
                value = ""
            finally:
                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass

            rows.append(
                {
                    "HiveName": hive_name,
                    "Subkey": subkey,
                    "ValueName": value_name,
                    "Value": value,
                }
            )

        self._shell_rows = rows
        return rows

    def _collect_logon_persistence_rows(self):
        if self._logon_rows is not None:
            return self._logon_rows

        rows = []
        if not WINREG_OK:
            self._logon_rows = rows
            return rows

        locations = [
            (winreg.HKEY_CURRENT_USER, r"Environment", "UserInitMprLogonScript", "UserInitMprLogonScript", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "Taskman", "WinlogonTaskman", "HKLM"),
        ]

        for hive, subkey, value_name, kind, hive_name in locations:
            try:
                key = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            try:
                value = str(winreg.QueryValueEx(key, value_name)[0] or "")
            except OSError:
                value = ""
            finally:
                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass

            rows.append(
                {
                    "Kind": kind,
                    "Hive": hive,
                    "HiveName": hive_name,
                    "Subkey": subkey,
                    "ValueName": value_name,
                    "Value": value,
                }
            )

        notify_root = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\Notify"
        try:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, notify_root)
        except (FileNotFoundError, PermissionError):
            root = None

        if root:
            try:
                index = 0
                while True:
                    try:
                        notify_name = winreg.EnumKey(root, index)
                    except OSError:
                        break
                    index += 1
                    notify_path = notify_root + "\\" + notify_name
                    try:
                        child = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, notify_path)
                    except (FileNotFoundError, PermissionError):
                        continue

                    try:
                        try:
                            dll_name = str(winreg.QueryValueEx(child, "DLLName")[0] or "")
                        except OSError:
                            dll_name = ""
                        if not dll_name:
                            continue
                        rows.append(
                            {
                                "Kind": "WinlogonNotify",
                                "Hive": winreg.HKEY_LOCAL_MACHINE,
                                "HiveName": "HKLM",
                                "Subkey": notify_path,
                                "ValueName": "DLLName",
                                "NotifyName": notify_name,
                                "Value": dll_name,
                            }
                        )
                    finally:
                        try:
                            winreg.CloseKey(child)
                        except Exception:
                            pass
            finally:
                try:
                    winreg.CloseKey(root)
                except Exception:
                    pass

        self._logon_rows = rows
        return rows

    def _resolve_clsid_server_path(self, clsid):
        clsid = str(clsid or "").strip()
        if not clsid:
            return ""

        candidate_roots = []
        if hasattr(winreg, "HKEY_CLASSES_ROOT"):
            candidate_roots.append((winreg.HKEY_CLASSES_ROOT, rf"CLSID\{clsid}"))
        candidate_roots.extend([
            (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Classes\CLSID\{clsid}"),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Classes\CLSID\{clsid}"),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Classes\CLSID\{clsid}"),
        ])

        for hive, base_key in candidate_roots:
            for server_key in ("InprocServer32", "LocalServer32"):
                try:
                    key = winreg.OpenKey(hive, base_key + "\\" + server_key)
                except (FileNotFoundError, PermissionError):
                    continue
                try:
                    value = str(winreg.QueryValueEx(key, "")[0] or "").strip()
                except OSError:
                    value = ""
                finally:
                    try:
                        winreg.CloseKey(key)
                    except Exception:
                        pass
                if value:
                    return value
        return ""

    def _collect_explorer_hijack_rows(self):
        if self._explorer_hijack_rows is not None:
            return self._explorer_hijack_rows

        rows = []
        if not WINREG_OK:
            self._explorer_hijack_rows = rows
            return rows

        hook_locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ShellExecuteHooks", "ShellExecuteHook", "HKLM"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\ShellExecuteHooks", "ShellExecuteHook", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\ShellServiceObjectDelayLoad", "ShellServiceObjectDelayLoad", "HKLM"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\ShellServiceObjectDelayLoad", "ShellServiceObjectDelayLoad", "HKCU"),
        ]

        for hive, subkey, kind, hive_name in hook_locations:
            try:
                key = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            index = 0
            while True:
                try:
                    value_name, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                clsid = str(value or "").strip()
                rows.append(
                    {
                        "Kind": kind,
                        "Hive": hive,
                        "HiveName": hive_name,
                        "Subkey": subkey,
                        "ValueName": str(value_name or ""),
                        "Value": clsid,
                        "ResolvedPath": self._resolve_clsid_server_path(clsid),
                    }
                )

            try:
                winreg.CloseKey(key)
            except Exception:
                pass

        self._explorer_hijack_rows = rows
        return rows

    def _looks_suspicious_shell_persistence(self, value_name, value):
        raw = self._normalize_cmdline(value).strip()
        if not raw:
            return None

        name = str(value_name or "")
        lowered_name = name.lower()
        lowered_value = raw.lower()

        if lowered_name == "shell":
            compact = lowered_value.replace(" ", "")
            if compact in {"explorer.exe", "explorer.exe,"}:
                return None
            if self._value_has_malware_signal(raw):
                return "HIGH", "Shell Persistence Review", f"Winlogon Shell points at suspicious startup command: {raw}"
            if "explorer.exe" not in lowered_value:
                return "MEDIUM", "Shell Persistence Review", f"Winlogon Shell was changed from the normal explorer.exe value: {raw}"
            if "," in lowered_value or self._contains_remote_loader_marker(lowered_value):
                return "MEDIUM", "Shell Persistence Review", f"Winlogon Shell contains extra startup payload content: {raw}"
            return None

        if lowered_name == "userinit":
            normalized = lowered_value.replace(" ", "")
            if normalized in {
                r"c:\windows\system32\userinit.exe,",
                r"%systemroot%\system32\userinit.exe,",
            }:
                return None
            if self._value_has_malware_signal(raw):
                return "HIGH", "Shell Persistence Review", f"Winlogon Userinit points at suspicious startup command: {raw}"
            if "," in lowered_value and "userinit.exe" in lowered_value:
                tail = lowered_value.split(",", 1)[1].strip()
                if tail:
                    return "MEDIUM", "Shell Persistence Review", f"Winlogon Userinit contains extra startup payload content: {raw}"
            return "MEDIUM", "Shell Persistence Review", f"Winlogon Userinit differs from the normal default value: {raw}"

        if lowered_name in {"load", "run"} and self._value_has_malware_signal(raw):
            return "HIGH", "Shell Persistence Review", f"Legacy Windows startup value {name} points at suspicious command: {raw}"

        return None

    def _looks_suspicious_policy_persistence(self, row):
        kind = str((row or {}).get("Kind") or "")
        value_name = str((row or {}).get("ValueName") or "")
        raw = self._normalize_cmdline((row or {}).get("Value")).strip()
        if not raw:
            return None

        target = self._extract_command_target(raw)
        normalized_target = self._normalized_path(target)

        if kind == "ExplorerRun":
            if self._value_has_malware_signal(raw):
                return "HIGH", "Policy Persistence", f"Policies Explorer Run launches a suspicious command: {value_name} = {raw}"
            if normalized_target and self._looks_like_temp_stage_launcher(normalized_target):
                return "HIGH", "Policy Persistence", f"Policies Explorer Run launches a temp-stage executable: {value_name} = {raw}"
            return None

        if kind == "CmdAutorun":
            if self._value_has_malware_signal(raw):
                return "HIGH", "Policy Persistence", f"Command Processor Autorun launches a suspicious command: {raw}"
            if self._contains_remote_loader_marker(raw):
                return "HIGH", "Policy Persistence", f"Command Processor Autorun references a remote loader or downloader command: {raw}"
            if normalized_target and any(marker in normalized_target for marker in COMMON_USERLAND_EXEC_MARKERS):
                if not self._is_safe_process_context(os.path.basename(normalized_target).lower(), target, raw):
                    return "HIGH", "Policy Persistence", f"Command Processor Autorun launches a user-writable executable or script: {raw}"
            return None

        if kind == "PolicyShell":
            lowered = raw.lower().replace(" ", "")
            if lowered in {"explorer.exe", "explorer.exe,"}:
                return None
            if self._value_has_malware_signal(raw):
                return "HIGH", "Policy Persistence", f"Policies System Shell points at a suspicious shell command: {raw}"
            if "explorer.exe" not in lowered:
                return "MEDIUM", "Policy Persistence", f"Policies System Shell overrides the normal explorer.exe shell: {raw}"
            if "," in raw or self._contains_remote_loader_marker(raw):
                return "MEDIUM", "Policy Persistence", f"Policies System Shell contains extra startup payload content: {raw}"
            return None

        return None

    def _looks_suspicious_logon_persistence(self, row):
        kind = str((row or {}).get("Kind") or "")
        raw = self._normalize_cmdline((row or {}).get("Value")).strip()
        if not raw:
            return None

        target = self._extract_command_target(raw)
        normalized_target = self._normalized_path(target)

        if kind == "UserInitMprLogonScript":
            if self._value_has_malware_signal(raw):
                return "HIGH", "Logon Script Persistence", f"UserInitMprLogonScript launches a suspicious logon command: {raw}"
            if normalized_target and self._looks_like_temp_stage_launcher(normalized_target):
                return "HIGH", "Logon Script Persistence", f"UserInitMprLogonScript launches a temp-stage executable: {raw}"
            if self._contains_remote_loader_marker(raw):
                return "HIGH", "Logon Script Persistence", f"UserInitMprLogonScript references a remote loader or downloader command: {raw}"
            if normalized_target and self._path_in_user_writable_exec_zone(normalized_target):
                stem = os.path.splitext(os.path.basename(normalized_target))[0]
                if self._looks_random(stem) or self._contains_marker(normalized_target, PROCESS_IOC_MARKERS):
                    return "HIGH", "Logon Script Persistence", f"UserInitMprLogonScript launches a suspicious user-writable payload: {raw}"
            return None

        if kind == "WinlogonTaskman":
            if self._value_has_malware_signal(raw):
                return "HIGH", "Logon Script Persistence", f"Winlogon Taskman points at a suspicious logon command: {raw}"
            if normalized_target and self._path_in_user_writable_exec_zone(normalized_target):
                return "MEDIUM", "Logon Script Persistence", f"Winlogon Taskman points outside the normal system path: {raw}"
            return None

        if kind == "WinlogonNotify":
            notify_name = str((row or {}).get("NotifyName") or "")
            if self._value_has_malware_signal(raw):
                return "HIGH", "Winlogon Notify Review", f"Winlogon Notify DLL looks suspicious: {notify_name} -> {raw}"
            if normalized_target and self._path_in_user_writable_exec_zone(normalized_target):
                return "HIGH", "Winlogon Notify Review", f"Winlogon Notify loads a DLL from a user-writable path: {notify_name} -> {raw}"
            if normalized_target and not self._is_trusted_vendor_path(normalized_target) and not self._is_protected_system_path(normalized_target):
                stem = os.path.splitext(os.path.basename(normalized_target))[0]
                if self._looks_random(stem):
                    return "MEDIUM", "Winlogon Notify Review", f"Winlogon Notify uses an unusual DLL name or path: {notify_name} -> {raw}"
            return None

        return None

    def _looks_suspicious_explorer_hijack(self, row):
        kind = str((row or {}).get("Kind") or "")
        value_name = str((row or {}).get("ValueName") or "")
        clsid = self._normalize_cmdline((row or {}).get("Value")).strip()
        resolved_path = self._normalize_cmdline((row or {}).get("ResolvedPath")).strip()

        if not (clsid or resolved_path):
            return None

        if self._value_has_malware_signal(clsid) or self._value_has_malware_signal(resolved_path):
            return "HIGH", "Explorer Hijack Review", f"{kind} resolves to a suspicious Explorer hook: {value_name} -> {resolved_path or clsid}"

        normalized_target = self._normalized_path(self._extract_command_target(resolved_path) or resolved_path)
        if normalized_target and self._path_in_user_writable_exec_zone(normalized_target):
            return "HIGH", "Explorer Hijack Review", f"{kind} resolves to a user-writable Explorer hook DLL: {value_name} -> {resolved_path}"

        if normalized_target and not self._is_trusted_vendor_path(normalized_target) and not self._is_protected_system_path(normalized_target):
            stem = os.path.splitext(os.path.basename(normalized_target))[0]
            if self._looks_random(stem):
                return "MEDIUM", "Explorer Hijack Review", f"{kind} resolves to an unusual Explorer hook DLL: {value_name} -> {resolved_path}"

        return None

    def _looks_suspicious_active_setup(self, row):
        raw = self._normalize_cmdline((row or {}).get("StubPath")).strip()
        if not raw:
            return None

        target = self._extract_command_target(raw)
        normalized_target = self._normalized_path(target)
        component_name = str((row or {}).get("ComponentName") or "")
        component_label = str((row or {}).get("ComponentLabel") or "")
        display = component_label or component_name or "Active Setup component"
        raw_lower = raw.lower()

        if (
            normalized_target.endswith("\\installer\\chrmstp.exe")
            and self._has_trusted_file_metadata(target)
            and any(token in raw_lower for token in ("--configure-user-settings", "--system-level"))
        ):
            return None

        if self._value_has_malware_signal(raw):
            return "HIGH", "Active Setup Persistence", f"Active Setup component launches a suspicious StubPath: {display} -> {raw}"
        if self._contains_remote_loader_marker(raw):
            return "HIGH", "Active Setup Persistence", f"Active Setup component references a remote loader or downloader command: {display} -> {raw}"
        if normalized_target and self._looks_like_temp_stage_launcher(normalized_target):
            return "HIGH", "Active Setup Persistence", f"Active Setup component launches a temp-stage executable: {display} -> {raw}"
        if normalized_target and self._path_in_user_writable_exec_zone(normalized_target):
            stem = os.path.splitext(os.path.basename(normalized_target))[0]
            if self._looks_random(stem) or self._contains_marker(normalized_target, PROCESS_IOC_MARKERS):
                return "HIGH", "Active Setup Persistence", f"Active Setup component launches a suspicious user-writable payload: {display} -> {raw}"
        return None

    def _looks_suspicious_runonceex(self, row):
        raw = self._normalize_cmdline((row or {}).get("Value")).strip()
        if not raw:
            return None

        target = self._extract_command_target(raw)
        normalized_target = self._normalized_path(target)
        value_name = str((row or {}).get("ValueName") or "")

        if self._value_has_malware_signal(raw):
            return "HIGH", "RunOnceEx Persistence", f"RunOnceEx launches a suspicious command: {value_name} = {raw}"
        if self._contains_remote_loader_marker(raw):
            return "HIGH", "RunOnceEx Persistence", f"RunOnceEx references a remote loader or downloader command: {value_name} = {raw}"
        if normalized_target and self._looks_like_temp_stage_launcher(normalized_target):
            return "HIGH", "RunOnceEx Persistence", f"RunOnceEx launches a temp-stage executable: {value_name} = {raw}"
        if normalized_target and self._path_in_user_writable_exec_zone(normalized_target):
            stem = os.path.splitext(os.path.basename(normalized_target))[0]
            if self._looks_random(stem) or self._contains_marker(normalized_target, PROCESS_IOC_MARKERS):
                return "HIGH", "RunOnceEx Persistence", f"RunOnceEx launches a suspicious user-writable payload: {value_name} = {raw}"
        return None

    def _evaluate_scheduled_task_entry(self, task_name, task_path, execute, arguments="", working_directory=""):
        task_name = str(task_name or "")
        task_path = str(task_path or "")
        execute = str(execute or "")
        arguments = str(arguments or "")
        working_directory = str(working_directory or "")
        blob = " ".join(part for part in (task_name, task_path, execute, arguments, working_directory) if part)
        if not blob:
            return None

        if self._has_strong_campaign_context(blob):
            return (
                "CRITICAL",
                "Malicious Scheduled Task",
                f"Scheduled task references RenEngine/HijackLoader artifacts: {task_path}{task_name}",
            )

        executable = self._extract_command_target(execute)
        normalized_executable = self._normalized_path(executable)
        executable_name = os.path.basename(normalized_executable).lower()
        argument_blob = self._normalize_cmdline(arguments).lower()

        if self._looks_like_godot_asar_task(executable, arguments, working_directory):
            severity = "CRITICAL" if self._file_metadata_matches(executable, PYTHON_COMPANY_TOKENS) else "HIGH"
            return (
                severity,
                "Malicious Scheduled Task",
                f"Scheduled task launches Godot app_userdata payload with .asar arguments: {task_path}{task_name}",
            )

        if self._looks_like_temp_stage_launcher(normalized_executable):
            score = self._score_startup_temp_launcher(executable, arguments, working_directory)
            if score >= 3 and not self._is_safe_process_context(executable_name, executable, arguments, allow_metadata=True):
                return (
                    "HIGH",
                    "Malicious Scheduled Task",
                    f"Scheduled task launches temp-stage executable: {task_path}{task_name} -> {executable}",
                )

        if executable and any(marker in argument_blob for marker in ASAR_ARGUMENT_MARKERS):
            if self._path_in_user_writable_exec_zone(normalized_executable) and not self._is_safe_process_context(
                executable_name, executable, arguments, allow_metadata=True
            ):
                return (
                    "HIGH",
                    "Malicious Scheduled Task",
                    f"Scheduled task passes .asar payload arguments to a user-writable executable: {task_path}{task_name}",
                )

        if executable_name in SHORTCUT_SCRIPT_HOSTS:
            if self._contains_remote_loader_marker(arguments) or any(
                token in argument_blob for token in STARTUP_DOWNLOADER_TOKENS
            ):
                return (
                    "HIGH",
                    "Malicious Scheduled Task",
                    f"Scheduled task launches a script host with remote loader behavior: {task_path}{task_name}",
                )

        return None

    def _startup_signal_for_command(self, command_text, arguments="", working_directory=""):
        raw = self._normalize_cmdline(command_text)
        arguments = self._normalize_cmdline(arguments)
        working_directory = str(working_directory or "")
        blob = " ".join(part for part in (raw, arguments, working_directory) if part)
        target = self._extract_command_target(raw)
        normalized_target = self._normalized_path(target)

        if not blob or self._is_local_tool_context(blob, target):
            return None

        score = 0
        reasons = []
        if self._has_strong_campaign_context(blob):
            score += 4
            reasons.append("campaign markers")
        if self._looks_like_temp_stage_launcher(normalized_target):
            score += 3
            reasons.append("temp-stage launcher")
        if self._looks_like_godot_asar_task(target, arguments, working_directory):
            score += 3
            reasons.append("Godot app_userdata + asar payload")
        if self._contains_remote_loader_marker(blob):
            score += 3
            reasons.append("remote URL/IP loader marker")
        if any(token in blob.lower() for token in STARTUP_DOWNLOADER_TOKENS):
            score += 2
            reasons.append("downloader-style startup command")
        if normalized_target and self._looks_like_suspicious_netsupport_path(normalized_target, allow_metadata=True):
            score += 3
            reasons.append("NetSupport RAT path")

        if normalized_target and self._path_in_user_writable_exec_zone(normalized_target):
            base = os.path.splitext(os.path.basename(normalized_target))[0]
            if self._contains_marker(normalized_target, PROCESS_IOC_MARKERS):
                score += 2
                reasons.append("user-writable IOC path")
            elif self._looks_random(base):
                score += 2
                reasons.append("random launcher in user-writable path")

        if target:
            target_name = os.path.basename(normalized_target).lower()
            if self._is_safe_process_context(target_name, target, arguments, allow_metadata=True):
                if score < 4:
                    return None

        if score <= 0:
            return None

        identity = normalized_target or blob.lower()
        return {
            "identity": identity,
            "target": target or raw,
            "score": score,
            "reasons": reasons,
        }

    def _iter_startup_file_rows(self):
        for root in self._startup_persistence_roots():
            if not os.path.isdir(root):
                continue
            try:
                for entry in os.listdir(root):
                    full = os.path.join(root, entry)
                    if os.path.isfile(full) and not entry.lower().endswith(".lnk"):
                        yield {
                            "Path": full,
                            "Name": entry,
                            "WorkingDirectory": os.path.dirname(full),
                        }
            except Exception:
                continue

    def scan_startup_correlations(self):
        self.log("STARTUP CORRELATION REVIEW", "SECTION")

        correlated = {}

        for row in self._iter_startup_file_rows():
            signal = self._startup_signal_for_command(
                row.get("Path"),
                "",
                row.get("WorkingDirectory"),
            )
            if not signal:
                continue
            location = str(row.get("Path") or "")
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"] + 1)
            bucket["sources"].append(f"startup-file:{location}")
            bucket["reasons"].update(signal["reasons"])
            bucket["reasons"].add("direct startup folder payload")

        for row in self._collect_shortcut_rows():
            signal = self._startup_signal_for_command(
                row.get("TargetPath"),
                row.get("Arguments"),
                row.get("WorkingDirectory"),
            )
            if not signal:
                continue
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"])
            bucket["sources"].append(f"shortcut:{row.get('Path')}")
            bucket["reasons"].update(signal["reasons"])

        for row in self._collect_scheduled_task_rows():
            signal = self._startup_signal_for_command(
                row.get("Execute"),
                row.get("Arguments"),
                row.get("WorkingDirectory"),
            )
            if not signal:
                continue
            task_label = f"{row.get('TaskPath') or ''}{row.get('TaskName') or ''}"
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"])
            bucket["sources"].append(f"task:{task_label}")
            bucket["reasons"].update(signal["reasons"])

        for row in self._collect_run_autorun_rows():
            signal = self._startup_signal_for_command(row.get("Value"))
            if not signal:
                continue
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"])
            bucket["sources"].append(f"autorun:{location}")
            bucket["reasons"].update(signal["reasons"])

        for row in self._collect_policy_persistence_rows():
            signal = self._startup_signal_for_command(row.get("Value"))
            if not signal:
                continue
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"] + 1)
            bucket["sources"].append(f"policy:{location}")
            bucket["reasons"].update(signal["reasons"])
            bucket["reasons"].add("policy-backed autorun")

        for row in self._collect_runonceex_rows():
            signal = self._startup_signal_for_command(row.get("Value"))
            if not signal:
                continue
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"] + 1)
            bucket["sources"].append(f"runonceex:{location}")
            bucket["reasons"].update(signal["reasons"])
            bucket["reasons"].add("runonceex autorun")

        for row in self._collect_active_setup_rows():
            signal = self._startup_signal_for_command(row.get("StubPath"))
            if not signal:
                continue
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[StubPath]"
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"] + 1)
            bucket["sources"].append(f"active-setup:{location}")
            bucket["reasons"].update(signal["reasons"])
            bucket["reasons"].add("active setup stubpath")

        for row in self._collect_logon_persistence_rows():
            target_text = row.get("Value")
            if row.get("Kind") == "WinlogonNotify":
                target_text = row.get("Value")
            signal = self._startup_signal_for_command(target_text)
            if not signal:
                continue
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"] + 1)
            bucket["sources"].append(f"logon:{location}")
            bucket["reasons"].update(signal["reasons"])
            bucket["reasons"].add("legacy logon persistence")

        for row in self._collect_explorer_hijack_rows():
            target_text = row.get("ResolvedPath") or row.get("Value")
            signal = self._startup_signal_for_command(target_text)
            if not signal:
                continue
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"] + 1)
            bucket["sources"].append(f"explorer-hook:{location}")
            bucket["reasons"].update(signal["reasons"])
            bucket["reasons"].add("legacy explorer hook")

        for row in self._collect_disabled_startup_rows():
            signal = self._startup_signal_for_command(
                row.get("Command"),
                row.get("Arguments"),
                row.get("WorkingDirectory"),
            )
            if not signal:
                continue
            location = str(row.get("Path") or row.get("ApprovalKey") or "")
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"] + 1)
            bucket["sources"].append(f"{row.get('SourceLabel') or 'disabled-startup'}:{location}")
            bucket["reasons"].update(signal["reasons"])
            bucket["reasons"].add("disabled startup residue")

        for row in self._collect_shell_persistence_rows():
            signal = self._startup_signal_for_command(row.get("Value"))
            if not signal:
                continue
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"] + 1)
            bucket["sources"].append(f"shell:{location}")
            bucket["reasons"].update(signal["reasons"])
            bucket["reasons"].add("shell/winlogon startup value")

        for row in self._collect_wmi_persistence_rows():
            class_name = str(row.get("ClassName") or "")
            if class_name == "CommandLineEventConsumer":
                command = str(row.get("CommandLineTemplate") or row.get("ExecutablePath") or "")
                signal = self._startup_signal_for_command(command)
                if not signal:
                    continue
                name = str(row.get("Name") or class_name)
                bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
                bucket["score"] = max(bucket["score"], signal["score"] + 2)
                bucket["sources"].append(f"wmi:{name}")
                bucket["reasons"].update(signal["reasons"])
                bucket["reasons"].add("WMI command consumer")
                continue

            if class_name != "ActiveScriptEventConsumer":
                continue
            command = str(row.get("ScriptText") or "")
            signal = self._startup_signal_for_command(command)
            if not signal:
                continue
            name = str(row.get("Name") or class_name)
            bucket = correlated.setdefault(signal["identity"], {"score": 0, "sources": [], "target": signal["target"], "reasons": set()})
            bucket["score"] = max(bucket["score"], signal["score"] + 2)
            bucket["sources"].append(f"wmi-script:{name}")
            bucket["reasons"].update(signal["reasons"])
            bucket["reasons"].add("WMI script consumer")

        for bucket in correlated.values():
            unique_sources = sorted(set(bucket["sources"]))
            if len(unique_sources) < 2:
                continue

            severity = "HIGH" if len(unique_sources) >= 3 or bucket["score"] >= 4 else "MEDIUM"
            if any(source.startswith("wmi:") for source in unique_sources) and len(unique_sources) >= 2:
                severity = "HIGH"
            source_kinds = []
            for source in unique_sources:
                kind = source.split(":", 1)[0]
                if kind not in source_kinds:
                    source_kinds.append(kind)
            source_list = ", ".join(source_kinds[:4])
            reason_text = ", ".join(sorted(bucket["reasons"])) if bucket["reasons"] else "repeated startup persistence"
            self._add(
                severity,
                "Startup Correlation Review",
                f"Suspicious startup target is reused across {len(unique_sources)} surfaces ({source_list}): {bucket['target']} [{reason_text}]",
                bucket["target"],
            )

    def _stream_review_candidate_paths(self):
        candidates = []
        seen = set()
        interesting_categories = {
            "Dropped Executable",
            "Exact IOC Hash",
            "HijackLoader Stage Artifact",
            "Loader Container DLL",
            "Malicious Archive/Script",
            "Malicious File",
            "Payload Key File",
            "Persistence Artifact",
            "Startup Persistence Artifact",
        }
        for threat in self.threats:
            if threat.category not in interesting_categories:
                continue
            path = self._normalized_path(threat.path)
            if not path or path in seen:
                continue
            if not os.path.isfile(path):
                continue
            if self._is_local_tool_path(path):
                continue
            lowered = path.lower()
            if not (
                self._path_in_user_writable_exec_zone(path)
                or self._in_temp(path)
                or "\\start menu\\programs\\startup\\" in lowered
            ):
                continue
            seen.add(path)
            candidates.append(path)
        return candidates

    def scan_alternate_data_streams(self):
        self.log("ALTERNATE DATA STREAM REVIEW", "SECTION")
        candidates = self._stream_review_candidate_paths()
        if not candidates:
            return

        for path in candidates:
            if self._stop:
                return
            streams = self._list_file_streams(path)
            if streams is None:
                self.log("PowerShell unavailable - alternate data stream review skipped", "WARN")
                return
            for stream in streams:
                name = str(stream.get("name") or "")
                lowered = name.lower()
                size = int(stream.get("length") or 0)
                suspicious = (
                    self._has_strong_campaign_context(name, path)
                    or self._contains_remote_loader_marker(name)
                    or any(marker in lowered for marker in SUSPICIOUS_STREAM_NAME_MARKERS)
                )
                severity = "HIGH" if suspicious else "MEDIUM"
                detail = f"{path} -> {name} ({size} byte(s))"
                if suspicious:
                    self._add(
                        severity,
                        "Alternate Data Stream Review",
                        f"Hidden stream on a suspicious file looks loader-like: {detail}",
                        path,
                    )
                else:
                    self._add(
                        severity,
                        "Alternate Data Stream Review",
                        f"Suspicious file carries a non-default alternate data stream: {detail}",
                        path,
                    )

    @staticmethod
    def _chromium_profile_dirs(root):
        if not os.path.isdir(root):
            return []
        base = os.path.basename(root).lower()
        if base != "user data":
            return [root]
        out = []
        try:
            for entry in os.listdir(root):
                full = os.path.join(root, entry)
                if not os.path.isdir(full):
                    continue
                if entry == "Default" or entry.startswith("Profile ") or entry in {"Guest Profile", "System Profile"}:
                    out.append(full)
        except Exception:
            return []
        return out

    def _iter_chromium_extension_manifests(self):
        profile = os.environ.get("USERPROFILE", "")
        for label, rel_root in CHROMIUM_EXTENSION_REVIEW_ROOTS:
            root = os.path.join(profile, rel_root)
            for profile_dir in self._chromium_profile_dirs(root):
                ext_root = os.path.join(profile_dir, "Extensions")
                if not os.path.isdir(ext_root):
                    continue
                try:
                    for ext_id in os.listdir(ext_root):
                        ext_id_dir = os.path.join(ext_root, ext_id)
                        if not os.path.isdir(ext_id_dir):
                            continue
                        for version in os.listdir(ext_id_dir):
                            manifest_path = os.path.join(ext_id_dir, version, "manifest.json")
                            if os.path.isfile(manifest_path):
                                yield label, manifest_path
                except Exception:
                    continue

    @staticmethod
    def _sha256_file(path):
        h = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest().lower()

    def _is_probable_source_lure(self, path, fname):
        if self._is_local_tool_path(path) or self._is_project_like_path(path):
            return False
        name_lower = fname.lower()
        ext = os.path.splitext(name_lower)[1]
        if ext not in SOURCE_LURE_EXTENSIONS:
            return False
        if ext == ".exe":
            if self._is_trusted_vendor_path(path) or self._has_trusted_file_metadata(path):
                return False
            return self._contains_marker(name_lower, SOURCE_LURE_FILENAME_STRONG)
        if self._contains_marker(name_lower, SOURCE_LURE_KEYWORDS) and ext not in {".html", ".htm", ".url"}:
            return True
        if ext in {".url", ".lnk", ".html", ".htm", ".bat", ".cmd", ".ps1", ".vbs", ".js"}:
            return self._script_has_lure_content(path)
        return False

    @staticmethod
    def _has_generic_launcher_stem(stems):
        for stem in stems:
            lowered = str(stem or "").lower()
            if any(keyword in lowered for keyword in GENERIC_LAUNCHER_KEYWORDS):
                return True
        return False

    @staticmethod
    def _has_random_launcher_stem(stems):
        for stem in stems:
            lowered = str(stem or "").lower()
            if lowered in {"python", "pythonw", "renpy"}:
                continue
            if ScanEngine._looks_random(lowered):
                return True
        return False

    def _profile_renpy_bundle(self, dirpath, dir_names_lower, filenames):
        if not RENENGINE_FOLDER_SET.issubset(dir_names_lower):
            return None

        names_lower = [name.lower() for name in filenames]
        file_name_set = set(names_lower)
        exe_stems = {
            os.path.splitext(name)[0]
            for name in names_lower
            if name.endswith(".exe")
        }
        script_stems = {
            os.path.splitext(name)[0]
            for name in names_lower
            if os.path.splitext(name)[1] in RENPY_LAUNCHER_SCRIPT_EXTENSIONS
        }
        paired_stems = sorted(exe_stems & script_stems)
        suspicious_location = (
            self._path_in_user_writable_exec_zone(dirpath.lower())
            or self._in_temp(dirpath)
            or self._is_user_visible_root(dirpath)
        )
        lure_context = self._contains_marker(
            " ".join([dirpath] + names_lower),
            SOURCE_LURE_KEYWORDS,
        )
        generic_launcher = self._has_generic_launcher_stem(exe_stems | script_stems)
        random_launcher = self._has_random_launcher_stem(exe_stems | script_stems)
        has_archive_payload = "archive.rpa" in file_name_set
        has_compiled_payload = "script.rpyc" in file_name_set
        has_key_file = any(name.endswith(".key") for name in names_lower)
        payload_indicator_count = sum(
            1 for name in names_lower
            if os.path.splitext(name)[1] in RENPY_PAYLOAD_INDICATOR_EXTENSIONS
        )
        suspicious_root_mix = (
            len(exe_stems) >= 1
            and len(script_stems) >= 1
            and payload_indicator_count >= 2
        )

        score = 0
        reasons = []
        if paired_stems:
            score += 2
            reasons.append("paired exe/script launcher")
        if has_archive_payload and has_compiled_payload:
            score += 2
            reasons.append("archive.rpa + script.rpyc payload")
        elif has_archive_payload or has_compiled_payload:
            score += 1
            reasons.append("compiled Ren'Py payload file")
        if has_key_file:
            score += 1
            reasons.append("nearby decode-stage key file")
        if suspicious_root_mix:
            score += 1
            reasons.append("launcher and payload files mixed in root")
        if suspicious_location:
            score += 1
            reasons.append("user-writable bundle location")
        if lure_context:
            score += 1
            reasons.append("lure/distribution context")
        if generic_launcher:
            score += 1
            reasons.append("generic launcher naming")
        if random_launcher:
            score += 1
            reasons.append("random launcher naming")

        return {
            "score": score,
            "paired_stems": paired_stems,
            "has_archive_payload": has_archive_payload,
            "has_compiled_payload": has_compiled_payload,
            "has_key_file": has_key_file,
            "payload_indicator_count": payload_indicator_count,
            "suspicious_location": suspicious_location,
            "lure_context": lure_context,
            "generic_launcher": generic_launcher,
            "random_launcher": random_launcher,
            "reasons": reasons,
        }

    def _evaluate_renpy_bundle(self, dirpath, dir_names_lower, filenames):
        profile = self._profile_renpy_bundle(dirpath, dir_names_lower, filenames)
        if not profile:
            return None

        blob = " ".join([dirpath] + list(filenames))
        if self._has_strong_campaign_context(blob):
            return (
                "CRITICAL",
                "RenEngine Bundle",
                f"Ren'Py loader bundle with campaign markers at: {dirpath}",
            )

        if profile["score"] >= 6:
            reason_text = ", ".join(profile["reasons"][:4])
            return (
                "CRITICAL",
                "RenEngine Bundle",
                f"Ren'Py loader bundle matches strong inner-payload signals ({reason_text}): {dirpath}",
            )

        if profile["score"] >= 4:
            reason_text = ", ".join(profile["reasons"][:3])
            return (
                "HIGH",
                "Suspicious RenPy Loader Bundle",
                f"Ren'Py loader bundle matches multiple malware-style signals ({reason_text}): {dirpath}",
            )

        return None

    def _has_renloader_corroboration(self):
        categories = {threat.category for threat in self.threats}
        return bool(categories & (RENLOADER_CORRELATION_CATEGORIES - {"Suspicious RenPy Loader Bundle"}))

    def _looks_like_hijackloader_stage_dir(self, dirpath, file_names_lower):
        dir_lower = dirpath.lower()
        if (self._is_trusted_vendor_path(dirpath) or self._is_protected_system_path(dirpath)) and not self._has_strong_campaign_context(
            dirpath, " ".join(sorted(file_names_lower))
        ):
            return False
        suspicious_context = (
            self._in_temp(dirpath)
            or "\\.temp" in dir_lower
            or self._contains_marker(dir_lower, CAMPAIGN_DIR_MARKERS)
            or self._path_in_user_writable_exec_zone(dir_lower)
        )
        if not suspicious_context:
            return False
        for signature in HIJACKLOADER_STAGE_DIR_SIGNATURES:
            if len(signature & file_names_lower) >= 3:
                return True
        return False

    def _looks_like_generic_loader_stage_dir(self, dirpath, file_names_lower):
        dir_lower = dirpath.lower()
        if (self._is_trusted_vendor_path(dirpath) or self._is_protected_system_path(dirpath)) and not self._has_strong_campaign_context(
            dirpath, " ".join(sorted(file_names_lower))
        ):
            return False
        if not (
            self._in_temp(dirpath)
            or "\\.temp" in dir_lower
            or self._path_in_user_writable_exec_zone(dir_lower)
        ):
            return False

        exe_names = [name for name in file_names_lower if name.endswith(".exe")]
        dll_names = [name for name in file_names_lower if name.endswith(".dll")]
        odd_data_names = [
            name for name in file_names_lower
            if os.path.splitext(name)[1] in {".asp", ".bin", ".dat", ".eml", ".key", ".txt"}
        ]
        if not exe_names or not dll_names or not odd_data_names:
            return False

        suspicious_dll = any(name in LOADER_CONTAINER_DLLS or name in SUSPICIOUS_DLL_NAMES for name in dll_names)
        random_like = sum(
            1 for name in exe_names + dll_names
            if self._looks_random(os.path.splitext(name)[0])
        )
        return suspicious_dll or random_like >= 2

    def _looks_like_netsupport_stage_dir(self, dirpath, file_names_lower):
        normalized = self._normalized_path(dirpath)
        if not normalized or self._is_legit_netsupport_install_path(normalized):
            return False

        suspicious_context = (
            any(marker in normalized for marker in NETSUPPORT_SUSPICIOUS_PATH_MARKERS)
            or self._path_in_user_writable_exec_zone(normalized)
        )
        if not suspicious_context:
            return False

        names = {str(name or "").lower() for name in (file_names_lower or []) if name}
        if not names:
            return False

        has_core_pair = {"client32.ini", "nsm.lic"} <= names
        has_payload = bool(names & ({"client32.exe", "client32u.ini"} | {"htctl32.dll", "pcicl32.dll"}))
        return (has_core_pair and has_payload) or len(names & NETSUPPORT_STAGE_FILENAMES) >= 3

    def _matches_exact_ioc_hash(self, path, fname):
        fl = fname.lower()
        ext = os.path.splitext(fl)[1]
        should_hash = fl in HASH_CANDIDATE_NAMES or ext in {".zip", ".rar", ".7z"}
        if not should_hash:
            return None
        try:
            if os.path.getsize(path) > MAX_IOC_HASH_BYTES:
                return None
        except OSError:
            return None
        try:
            digest = self._sha256_file(path)
        except Exception:
            return None
        return KNOWN_SHA256_IOCS.get(digest)

    def _should_skip_walk_dir(self, dirpath):
        dpl = dirpath.lower()
        if self._is_local_tool_context(dirpath):
            return True
        return any(marker in dpl for marker in BENIGN_HEAVY_SUBTREES)

    def scan_exposure_surface(self):
        if not self.threats:
            return
        summary = self.last_summary or self.summarize_threats()
        if summary["confidence"] not in {"high", "medium"}:
            return

        profile = os.environ.get("USERPROFILE", "")
        for label, rel_path in EXPOSURE_DIRS:
            full_path = os.path.join(profile, rel_path)
            if os.path.exists(full_path):
                self._note_exposure(
                    f"Exposure warning — {label} data may have been accessed. Revoke sessions from a clean device",
                    full_path
                )

    def _looks_suspicious_module_path(self, module_path):
        mpl = (module_path or "").lower()
        if not mpl.endswith(".dll"):
            return False
        if (self._is_trusted_vendor_path(module_path) or self._is_protected_system_path(module_path)) and not self._has_strong_campaign_context(module_path):
            return False
        base = os.path.basename(mpl)
        if base in SUSPICIOUS_DLL_NAMES and (
            self._contains_marker(mpl, CAMPAIGN_DIR_MARKERS)
            or self._path_in_user_writable_exec_zone(mpl)
        ):
            suspicious = True
        elif base in LOADER_CONTAINER_DLLS and (
            "\\.temp" in mpl
            or self._contains_marker(mpl, {"broker_crypt_v4_i386", "dksyvguj", "w8cpbgqi", "gayal", "hap.eml"})
        ):
            suspicious = True
        else:
            suspicious = self._contains_marker(mpl, PROCESS_IOC_MARKERS) and self._path_in_user_writable_exec_zone(mpl)

        if not suspicious:
            return False
        if self._should_consider_metadata_trust(module_path) and self._has_trusted_file_metadata(module_path):
            return False
        return True

    def _should_scan_modules_for_process(self, pid, pname, pexe, cmdline):
        if self.paranoid:
            return True

        normalized_exe = self._normalized_path(pexe)
        if self._has_strong_campaign_context(pname, pexe, cmdline):
            return True
        if self._is_safe_process_context(pname, pexe, cmdline):
            return False
        if pexe and not os.path.exists(pexe) and self._path_in_user_writable_exec_zone(normalized_exe):
            return True
        if pexe and self._path_in_user_writable_exec_zone(normalized_exe):
            return True
        return pid in self._module_scan_pid_targets

    def scan_process_modules(self):
        self.log("── MODULE SCAN ────────────────────────────────────────", "SECTION")
        if not PSUTIL_OK or not hasattr(psutil.Process, "memory_maps"):
            self.log("psutil memory map support unavailable — module scan skipped", "WARN")
            return

        if not self.paranoid and not self._module_scan_pid_targets:
            self.log("No suspicious process targets surfaced in standard mode â€” deep module walk skipped", "INFO")
            return

        seen = set()
        scanned_targets = 0
        if self.paranoid:
            module_targets = psutil.process_iter()
        else:
            module_targets = []
            for pid in sorted(self._module_scan_pid_targets):
                try:
                    module_targets.append(psutil.Process(pid))
                except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                    continue

        for proc in module_targets:
            if self._stop:
                return
            try:
                pid = proc.pid
                pname = self._safe_proc_name(proc)
                pexe = self._safe_proc_exe(proc)
                cmdline = self._safe_proc_cmdline(proc)
                if not self._should_scan_modules_for_process(pid, pname, pexe, cmdline):
                    continue

                scanned_targets += 1
                if scanned_targets % 5 == 0:
                    self.progress(f"Checked modules for {scanned_targets} suspicious processes...")
                pexe_lower = pexe.lower()

                if (
                    pexe
                    and self._path_in_user_writable_exec_zone(pexe_lower)
                    and not os.path.exists(pexe)
                    and not self._is_safe_process_context(pname, pexe, cmdline)
                ):
                    self._add(
                        "CRITICAL",
                        "Execution Trace Anomaly",
                        f"Process image path missing on disk (possible hollowing/doppelganging trace): {pname} (PID {pid})  {pexe}",
                        pexe or cmdline,
                        lambda p=pid: self._kill_process_tree(p)
                    )

                for mmap in proc.memory_maps():
                    mpath = getattr(mmap, "path", "") or ""
                    if not mpath:
                        continue
                    key = (pid, mpath.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    if self._is_safe_process_context(pname, pexe, cmdline) and not self._has_strong_campaign_context(mpath):
                        continue
                    if self._looks_suspicious_module_path(mpath):
                        sev = "CRITICAL" if os.path.basename(mpath).lower() in SUSPICIOUS_DLL_NAMES else "HIGH"
                        self._add(
                            sev,
                            "Injected/Sideloaded DLL",
                            f"Suspicious DLL loaded by {pname} (PID {pid}): {mpath}",
                            mpath,
                            lambda p=pid: self._kill_process_tree(p)
                        )
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass
            except Exception as exc:
                self.log(f"Module scan warning: {exc}", "WARN")

    def scan_startup_persistence(self):
        self.log("── STARTUP ARTIFACT SCAN ─────────────────────────────", "SECTION")
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("PROGRAMDATA", "")
        startup_roots = []
        if appdata:
            startup_roots.append(os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup"))
        if programdata:
            startup_roots.append(os.path.join(programdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup"))

        for root in startup_roots:
            if not os.path.isdir(root):
                continue
            try:
                for fname in os.listdir(root):
                    fpath = os.path.join(root, fname)
                    finding = self._evaluate_startup_file_entry(fpath)
                    if finding:
                        severity, category, description = finding
                        self._add(
                            severity,
                            category,
                            description,
                            fpath,
                            lambda p=fpath: self._delete_file(p),
                        )
                        continue
                    if self._is_probable_source_lure(fpath, fname) or self._file_contains_ascii_or_utf16le(
                        fpath, PROCESS_IOC_MARKERS
                    ):
                        self._add(
                            "HIGH",
                            "Startup Persistence Artifact",
                            f"Suspicious startup entry or shortcut: {fpath}",
                            fpath,
                            lambda p=fpath: self._delete_file(p)
                        )
            except Exception as exc:
                self.log(f"Startup scan warning: {exc}", "WARN")

    def scan_shortcut_targets(self):
        self.log("SHORTCUT REVIEW", "SECTION")
        try:
            for row in self._collect_shortcut_rows():
                if self._stop:
                    return
                finding = self._evaluate_shortcut_entry(
                    row.get("Path"),
                    row.get("Name"),
                    row.get("TargetPath"),
                    row.get("Arguments"),
                    row.get("WorkingDirectory"),
                )
                if not finding:
                    continue
                severity, category, description = finding
                shortcut_path = str(row.get("Path") or "")
                self._add(
                    severity,
                    category,
                    description,
                    shortcut_path,
                    lambda p=shortcut_path: self._delete_file(p),
                )
        except Exception as exc:
            self.log(f"Shortcut review warning: {exc}", "WARN")

    def scan_disabled_startup_items(self):
        self.log("DISABLED STARTUP REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - disabled startup review skipped", "WARN")
            return

        shortcut_rows = self._collect_shortcut_rows()
        startup_shortcuts = {}
        for row in shortcut_rows:
            shortcut_path = self._normalized_path(row.get("Path"))
            if shortcut_path:
                startup_shortcuts[shortcut_path] = row

        actual_run_keys = {
            "Run": [
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
            ],
            "Run32": [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
            ],
        }

        startupapproved_roots = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved", "HKLM"),
        ]

        for hive, root, _hive_name in startupapproved_roots:
            for child_name in ("Run", "Run32", "StartupFolder"):
                subkey = root + "\\" + child_name
                try:
                    key = winreg.OpenKey(hive, subkey)
                except (FileNotFoundError, PermissionError):
                    continue

                index = 0
                while True:
                    try:
                        item_name, binary_value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    index += 1

                    if not self._is_disabled_startupapproved_value(binary_value):
                        continue

                    if child_name in actual_run_keys:
                        for run_hive, run_key, run_hive_name in actual_run_keys[child_name]:
                            try:
                                run_handle = winreg.OpenKey(run_hive, run_key)
                                run_value = str(winreg.QueryValueEx(run_handle, item_name)[0] or "")
                                winreg.CloseKey(run_handle)
                            except (FileNotFoundError, PermissionError, OSError):
                                continue

                            if not self._value_has_malware_signal(run_value):
                                continue
                            location = f"{run_hive_name}\\{run_key}"
                            self._add(
                                "HIGH",
                                "Disabled Startup Artifact",
                                f"Disabled startup entry still points at malware-linked command: {item_name} -> {run_value}",
                                location,
                                lambda approved_hive=hive, approved_key=subkey, approved_name=item_name,
                                value_hive=run_hive, value_key=run_key, value_name=item_name: self._remediate_disabled_startup_entry(
                                    [(approved_hive, approved_key, approved_name), (value_hive, value_key, value_name)]
                                ),
                            )
                            break
                        continue

                    for startup_root in self._startup_shortcut_roots():
                        shortcut_path = self._normalized_path(os.path.join(startup_root, item_name))
                        row = startup_shortcuts.get(shortcut_path)
                        if not row:
                            continue
                        finding = self._evaluate_shortcut_entry(
                            row.get("Path"),
                            row.get("Name"),
                            row.get("TargetPath"),
                            row.get("Arguments"),
                            row.get("WorkingDirectory"),
                        )
                        if not finding:
                            continue
                        self._add(
                            "HIGH",
                            "Disabled Startup Artifact",
                            f"Disabled startup shortcut still references suspicious target: {row.get('Path')}",
                            row.get("Path"),
                            lambda approved_hive=hive, approved_key=subkey, approved_name=item_name,
                            shortcut=row.get("Path"): self._remediate_disabled_startup_entry(
                                [(approved_hive, approved_key, approved_name)],
                                shortcut,
                            ),
                        )
                        break
                    else:
                        if self._looks_suspicious_startup_item_name(item_name):
                            location = f"{subkey}\\{item_name}"
                            self._add(
                                "MEDIUM",
                                "Disabled Startup Artifact",
                                f"Disabled startup item uses a suspicious random-looking name and should be reviewed: {item_name}",
                                location,
                                lambda approved_hive=hive, approved_key=subkey, approved_name=item_name: self._remediate_disabled_startup_entry(
                                    [(approved_hive, approved_key, approved_name)]
                                ),
                            )

                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass

    def scan_services(self):
        self.log("SERVICE SCAN", "SECTION")
        rows = self._run_powershell_json(
            "Get-CimInstance Win32_Service | "
            "Select-Object Name,DisplayName,PathName,StartMode,State | ConvertTo-Json -Compress",
            timeout=60,
        )
        if rows is None:
            self.log("PowerShell unavailable — service scan skipped", "WARN")
            return

        for row in rows:
            if self._stop:
                return
            try:
                name = str(row.get("Name") or "")
                display_name = str(row.get("DisplayName") or "")
                path_name = str(row.get("PathName") or "")
                finding = self._looks_suspicious_service(name, display_name, path_name)
                if not finding:
                    continue
                severity, category, description = finding
                self._add(
                    severity,
                    category,
                    description,
                    path_name or name,
                    lambda service_name=name: self._delete_service(service_name),
                )
            except Exception as exc:
                self.log(f"Service scan warning: {exc}", "WARN")

    def scan_wmi_persistence(self):
        self.log("WMI PERSISTENCE SCAN", "SECTION")
        queries = (
            ("__EventFilter", "Get-WmiObject -Namespace root\\subscription -Class __EventFilter | Select-Object Name,Query,EventNamespace | ConvertTo-Json -Compress"),
            ("CommandLineEventConsumer", "Get-WmiObject -Namespace root\\subscription -Class CommandLineEventConsumer | Select-Object Name,CommandLineTemplate,ExecutablePath | ConvertTo-Json -Compress"),
            ("ActiveScriptEventConsumer", "Get-WmiObject -Namespace root\\subscription -Class ActiveScriptEventConsumer | Select-Object Name,ScriptingEngine,ScriptText | ConvertTo-Json -Compress"),
        )

        for class_name, script in queries:
            rows = self._run_powershell_json(script, timeout=45)
            if rows is None:
                self.log("PowerShell unavailable — WMI scan skipped", "WARN")
                return

            for row in rows:
                if self._stop:
                    return
                try:
                    name = str(row.get("Name") or "")
                    blob = " ".join(str(value or "") for value in row.values())
                    suspicious = self._has_strong_campaign_context(blob)

                    if not suspicious and class_name == "CommandLineEventConsumer":
                        candidate = self._extract_command_target(str(row.get("CommandLineTemplate") or row.get("ExecutablePath") or ""))
                        normalized = self._normalized_path(candidate)
                        base = os.path.splitext(os.path.basename(normalized))[0]
                        suspicious = bool(
                            candidate
                            and self._path_in_user_writable_exec_zone(normalized)
                            and self._looks_random(base)
                        )

                    if not suspicious:
                        continue

                    self._add(
                        "CRITICAL",
                        "WMI Persistence",
                        f"Suspicious WMI subscription object ({class_name}): {name or '[unnamed]'}",
                        name or class_name,
                        lambda filter_name=name if class_name == "__EventFilter" else "",
                               consumer_name=name if class_name != "__EventFilter" else "",
                               consumer_class=class_name if class_name != "__EventFilter" else "":
                            self._delete_wmi_subscription(filter_name, consumer_name, consumer_class),
                    )
                except Exception as exc:
                    self.log(f"WMI scan warning: {exc}", "WARN")

    def scan_browser_extensions(self):
        self.log("BROWSER EXTENSION REVIEW", "SECTION")
        for finding in self._browser_review_entries():
            if self._stop:
                return
            self._add(
                "MEDIUM",
                "Browser Extension Review",
                finding["description"],
                finding["path"],
            )

    def scan_system_tampering(self):
        self.log("SYSTEM TAMPERING REVIEW", "SECTION")

        hosts_path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "drivers", "etc", "hosts")
        try:
            if os.path.isfile(hosts_path):
                with open(hosts_path, "r", encoding="utf-8", errors="ignore") as handle:
                    for raw_line in handle:
                        line = raw_line.strip()
                        if not line or line.startswith("#"):
                            continue
                        tokens = line.split()
                        if len(tokens) < 2:
                            continue
                        address = tokens[0]
                        hostnames = tokens[1:]
                        if address in {"127.0.0.1", "0.0.0.0", "::1"}:
                            continue
                        if any(marker in host.lower() for host in hostnames for marker in SENSITIVE_HOST_MARKERS):
                            self._add(
                                "MEDIUM",
                                "Hosts Tampering Review",
                                f"Hosts file overrides sensitive domain(s): {address} -> {' '.join(hostnames)}",
                                hosts_path,
                            )
                            break
        except Exception as exc:
            self.log(f"Hosts review warning: {exc}", "WARN")

        if WINREG_OK:
            proxy_locations = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", "HKCU"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", "HKLM"),
            ]
            for hive, subkey, hive_name in proxy_locations:
                proxy_enable = 0
                proxy_server = ""
                auto_config = ""
                try:
                    key = winreg.OpenKey(hive, subkey)
                    try:
                        proxy_enable = int(winreg.QueryValueEx(key, "ProxyEnable")[0])
                    except OSError:
                        proxy_enable = 0
                    try:
                        proxy_server = str(winreg.QueryValueEx(key, "ProxyServer")[0] or "")
                    except OSError:
                        proxy_server = ""
                    try:
                        auto_config = str(winreg.QueryValueEx(key, "AutoConfigURL")[0] or "")
                    except OSError:
                        auto_config = ""
                    winreg.CloseKey(key)
                except (FileNotFoundError, PermissionError):
                    continue

                proxy_blob = " ".join(str(part) for part in (proxy_server, auto_config) if part)
                proxy_lower = proxy_blob.lower()
                suspicious_proxy = self._has_strong_campaign_context(proxy_blob) or any(token in proxy_lower for token in ("127.0.0.1", "localhost"))
                if proxy_enable and proxy_blob and suspicious_proxy:
                    severity = "HIGH" if self._has_strong_campaign_context(proxy_blob) else "MEDIUM"
                    self._add(
                        severity,
                        "Proxy Configuration Review",
                        f"Internet proxy setting requires review: {hive_name}\\{subkey} -> {proxy_blob}",
                        f"{hive_name}\\{subkey}",
                        self._reset_user_proxy_settings,
                    )

        try:
            result = subprocess.run(
                ["netsh", "winhttp", "show", "proxy"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=0x08000000,
            )
            output = (result.stdout or "").strip().lower()
            if output and "direct access (no proxy server)" not in output and (
                self._has_strong_campaign_context(output) or any(token in output for token in ("127.0.0.1", "localhost"))
            ):
                self._add(
                    "MEDIUM",
                    "WinHTTP Proxy Review",
                    "WinHTTP proxy is configured and should be reviewed after cleanup.",
                    "netsh winhttp show proxy",
                    self._reset_winhttp_proxy_settings,
                )
        except Exception as exc:
            self.log(f"WinHTTP proxy review warning: {exc}", "WARN")

    def scan_defender_posture(self):
        self.log("DEFENDER POSTURE REVIEW", "SECTION")
        rows = self._run_powershell_json(
            "try { "
            "$pref = Get-MpPreference -ErrorAction Stop; "
            "[pscustomobject]@{ "
            "DisableRealtimeMonitoring=$pref.DisableRealtimeMonitoring; "
            "DisableIOAVProtection=$pref.DisableIOAVProtection; "
            "DisableScriptScanning=$pref.DisableScriptScanning; "
            "ExclusionPath=@($pref.ExclusionPath); "
            "ExclusionProcess=@($pref.ExclusionProcess); "
            "ExclusionExtension=@($pref.ExclusionExtension) "
            "} | ConvertTo-Json -Compress "
            "} catch { }",
            timeout=30,
        )
        if rows is None:
            self.log("PowerShell unavailable - Defender review skipped", "WARN")
            return
        if not rows:
            return

        row = rows[0]
        for kind in ("Path", "Process", "Extension"):
            values = row.get(f"Exclusion{kind}") or []
            if not isinstance(values, list):
                values = [values]
            for value in values:
                value_text = str(value or "").strip()
                if not self._is_risky_defender_exclusion(kind, value_text):
                    continue
                severity = "CRITICAL" if self._has_strong_campaign_context(value_text) else "HIGH"
                self._add(
                    severity,
                    "Defender Exclusion",
                    f"Suspicious Microsoft Defender exclusion ({kind.lower()}): {value_text}",
                    value_text,
                    lambda exclusion_kind=kind, exclusion_value=value_text: self._remove_defender_exclusion(
                        exclusion_kind,
                        exclusion_value,
                    ),
                )

        disabled_controls = []
        if bool(row.get("DisableRealtimeMonitoring")):
            disabled_controls.append("real-time monitoring")
        if bool(row.get("DisableIOAVProtection")):
            disabled_controls.append("IOAV protection")
        if bool(row.get("DisableScriptScanning")):
            disabled_controls.append("script scanning")
        if disabled_controls:
            self._add(
                "MEDIUM",
                "Defender Protection Review",
                "Microsoft Defender protections are disabled and should be reviewed: "
                + ", ".join(disabled_controls),
                "Get-MpPreference",
                self._repair_defender_protection_defaults,
            )

    def scan_security_posture(self):
        self.log("SECURITY CENTER REVIEW", "SECTION")

        rows = self._run_powershell_json(
            "try { "
            "Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction Stop | "
            "Select-Object displayName,pathToSignedProductExe,productState | ConvertTo-Json -Compress "
            "} catch { }",
            timeout=30,
        )
        if rows is not None:
            trusted_products = []
            if not rows:
                self._add(
                    "MEDIUM",
                    "Security Center Review",
                    "Security Center did not report any antivirus product. Review protection state after cleanup.",
                    "root/SecurityCenter2:AntiVirusProduct",
                )
            else:
                for row in rows:
                    try:
                        display_name = str(row.get("displayName") or "").strip()
                        exe_path = str(row.get("pathToSignedProductExe") or "").strip()
                        product_state = str(row.get("productState") or "").strip()
                        if self._is_benign_security_center_product(display_name, exe_path):
                            label = display_name or os.path.basename(exe_path) or "unknown"
                            trusted_products.append(label)
                            continue
                        if exe_path and not (
                            self._is_trusted_vendor_path(exe_path)
                            or self._is_protected_system_path(exe_path)
                            or self._has_trusted_file_metadata(exe_path)
                        ):
                            self._add(
                                "MEDIUM",
                                "Security Center Review",
                                f"Security Center lists an antivirus product from an unusual path: {display_name or exe_path}",
                                exe_path,
                            )
                        if not display_name and not exe_path and product_state:
                            self._add(
                                "MEDIUM",
                                "Security Center Review",
                                f"Security Center returned an incomplete antivirus product entry (state {product_state}).",
                                "root/SecurityCenter2:AntiVirusProduct",
                            )
                    except Exception as exc:
                        self.log(f"Security Center review warning: {exc}", "WARN")

            non_defender_products = []
            for product in trusted_products:
                lowered = str(product or "").strip().lower()
                if lowered in {"windows defender", "microsoft defender", "microsoft defender antivirus"}:
                    continue
                if lowered and lowered not in non_defender_products:
                    non_defender_products.append(lowered)
            if len(non_defender_products) >= 2:
                self._add(
                    "MEDIUM",
                    "Security Center Review",
                    "Multiple antivirus products are registered. Review overlapping real-time protection so cleanup tools do not fight each other.",
                    "root/SecurityCenter2:AntiVirusProduct",
                )

        if not WINREG_OK:
            return

        policy_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows Defender", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows Defender\Spynet", "HKLM"),
        ]
        for hive, subkey, hive_name in policy_roots:
            try:
                key = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            index = 0
            while True:
                try:
                    value_name, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1

                lowered_name = str(value_name or "").strip().lower()
                if lowered_name not in DEFENDER_POLICY_VALUE_NAMES:
                    continue

                suspicious = False
                try:
                    suspicious = int(value) not in {0}
                except Exception:
                    suspicious = str(value).strip().lower() not in {"", "0", "false"}

                if not suspicious:
                    continue

                self._add(
                    "MEDIUM",
                    "Defender Policy Review",
                    f"Windows Defender policy override requires review: {hive_name}\\{subkey} [{value_name}] = {value}",
                    f"{hive_name}\\{subkey}",
                    lambda action_hive=hive, action_subkey=subkey, action_name=value_name: self._delete_reg_val(
                        action_hive,
                        action_subkey,
                        action_name,
                    ),
                )

            try:
                winreg.CloseKey(key)
            except Exception:
                pass

    def scan_installed_programs(self):
        self.log("INSTALLED PROGRAM REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - installed program review skipped", "WARN")
            return

        uninstall_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "HKCU"),
        ]
        seen = set()

        for hive, subkey, hive_name in uninstall_roots:
            try:
                root = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            index = 0
            while True:
                try:
                    child_name = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1

                try:
                    child = winreg.OpenKey(hive, subkey + "\\" + child_name)
                except (FileNotFoundError, PermissionError):
                    continue

                try:
                    display_name = str(winreg.QueryValueEx(child, "DisplayName")[0] or "").strip()
                except OSError:
                    display_name = ""
                try:
                    install_location = str(winreg.QueryValueEx(child, "InstallLocation")[0] or "").strip()
                except OSError:
                    install_location = ""
                try:
                    publisher = str(winreg.QueryValueEx(child, "Publisher")[0] or "").strip()
                except OSError:
                    publisher = ""
                try:
                    uninstall_string = str(winreg.QueryValueEx(child, "UninstallString")[0] or "").strip()
                except OSError:
                    uninstall_string = ""

                try:
                    winreg.CloseKey(child)
                except Exception:
                    pass

                lowered_name = display_name.lower()
                if not lowered_name or lowered_name in seen:
                    continue
                if lowered_name not in FRST_REVIEW_PROGRAM_NAMES and not any(token in lowered_name for token in FRST_REVIEW_PROGRAM_NAMES):
                    continue

                seen.add(lowered_name)
                location_blob = self._normalized_path(install_location or uninstall_string)
                if "netsupport" in lowered_name and (
                    self._is_legit_netsupport_install_path(location_blob)
                    or "\\program files\\" in location_blob
                ):
                    continue
                details = " | ".join(part for part in (display_name, publisher, install_location or uninstall_string) if part)
                self._add(
                    "MEDIUM",
                    "Installed Program Review",
                    f"Installed program seen in current cleanup cases needs review: {details}",
                    f"{hive_name}\\{subkey}\\{child_name}",
                )

            try:
                winreg.CloseKey(root)
            except Exception:
                pass

    def _event_message_has_browser_policy_signal(self, policy_name, value_text):
        policy_name = str(policy_name or "").strip().lower()
        value_text = str(value_text or "").strip()
        value_lower = value_text.lower()

        if self._has_strong_campaign_context(policy_name, value_text):
            return True
        if self._is_local_tool_context(value_text):
            return False
        if any(token in policy_name for token in BROWSER_POLICY_SUSPICIOUS_VALUE_TOKENS):
            if any(marker in value_lower for marker in SCRIPT_LURE_REMOTE_MARKERS):
                return True
            if any(token in value_lower for token in ("127.0.0.1", "localhost")):
                return True
            if self._path_in_user_writable_exec_zone(self._normalized_path(value_text)):
                return True
        return False

    def scan_browser_policies(self):
        self.log("BROWSER POLICY REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - browser policy review skipped", "WARN")
            return

        policy_hives = (
            (winreg.HKEY_LOCAL_MACHINE, "HKLM"),
            (winreg.HKEY_CURRENT_USER, "HKCU"),
        )

        for browser_label, subkey in BROWSER_POLICY_ROOTS:
            for hive, hive_name in policy_hives:
                try:
                    key = winreg.OpenKey(hive, subkey)
                except (FileNotFoundError, PermissionError):
                    continue

                index = 0
                while True:
                    try:
                        value_name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    index += 1

                    value_text = value if isinstance(value, str) else json.dumps(value, default=str)
                    if not self._event_message_has_browser_policy_signal(value_name, value_text):
                        continue

                    severity = "HIGH" if self._has_strong_campaign_context(value_name, value_text) else "MEDIUM"
                    self._add(
                        severity,
                        "Browser Policy Review",
                        f"{browser_label} policy requires review: {value_name} = {value_text}",
                        f"{hive_name}\\{subkey}",
                    )

                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass

    def _is_suspicious_security_event(self, source_label, message):
        message = str(message or "").strip()
        message_lower = message.lower()
        if not message or self._is_local_tool_context(message):
            return False
        if self._has_strong_campaign_context(message):
            return True
        if TEMP_STAGE_DIR_REGEX.search(message_lower):
            return True
        if GODOT_APP_USERDATA_MARKER in message_lower and any(marker in message_lower for marker in ASAR_ARGUMENT_MARKERS):
            return True
        extracted_paths = [self._normalized_path(match.group(0).rstrip(" .,)")) for match in DRIVE_PATH_REGEX.finditer(message)]
        userland_path_hit = any(
            path
            and self._path_in_user_writable_exec_zone(path)
            and not self._is_local_tool_path(path)
            and not self._is_trusted_vendor_path(path)
            and not self._is_protected_system_path(path)
            for path in extracted_paths
        )
        if source_label == "Firewall" and self._is_benign_firewall_event(message_lower, extracted_paths):
            return False
        if source_label == "Defender" and self._is_benign_defender_event(message_lower):
            return False
        if source_label == "CodeIntegrity" and self._is_benign_code_integrity_event(message_lower):
            return False

        if any(token in message_lower for token in ("127.0.0.1", "localhost")) and source_label in {"Defender", "Firewall", "SecurityCenter"}:
            return True
        if source_label == "CodeIntegrity" and userland_path_hit:
            return True
        if source_label == "Defender" and userland_path_hit:
            return True
        if source_label == "Firewall" and (
            userland_path_hit
            or any(token in message_lower for token in ("allow", "allowed", "authorized")) and any(marker in message_lower for marker in USER_WRITABLE_DIR_MARKERS)
        ):
            return True
        if source_label == "SecurityCenter" and (
            userland_path_hit
            or any(token in message_lower for token in ("disabled", "off", "not monitored", "snooze", "expired"))
        ):
            return True
        if source_label == "ServiceControlManager" and userland_path_hit and any(
            token in message_lower for token in ("service", "failed", "terminated", "error", "could not")
        ):
            return True
        return False

    def _is_benign_security_center_product(self, display_name, exe_path):
        display_lower = str(display_name or "").strip().lower()
        exe_lower = str(exe_path or "").strip().lower()
        if display_lower in {"windows defender", "microsoft defender", "microsoft defender antivirus"}:
            return True
        if exe_lower and (
            self._is_trusted_vendor_path(exe_path)
            or self._is_protected_system_path(exe_path)
            or self._has_trusted_file_metadata(exe_path)
        ):
            return True
        if exe_lower and "windows defender" in exe_lower:
            return True
        return False

    def _is_benign_firewall_event(self, message_lower, extracted_paths):
        if not message_lower:
            return False
        if self._has_strong_campaign_context(message_lower):
            return False
        if extracted_paths and all(
            path and (
                self._is_trusted_vendor_path(path)
                or self._is_protected_system_path(path)
                or self._has_trusted_file_metadata(path)
            )
            for path in extracted_paths
        ):
            return True
        if any(
            path
            and self._path_in_user_writable_exec_zone(path)
            and not self._is_trusted_vendor_path(path)
            and not self._is_protected_system_path(path)
            and not self._is_local_tool_path(path)
            for path in extracted_paths
        ):
            return False

        benign_rule_tokens = (
            "windefend",
            "windows defender firewall",
            "service restriction rule for windefend",
            "mpssvc",
        )
        benign_actor_tokens = (
            "origin: local",
            "origin: 0",
            "modifying user: s-1-5-18",
            "modifying user: nt authority\\system",
            "modifying user: system",
        )
        has_benign_rule = any(token in message_lower for token in benign_rule_tokens)
        if has_benign_rule and any(token in message_lower for token in benign_actor_tokens):
            return True
        if "\\appdata\\local\\programs\\opera gx\\opera.exe" in message_lower:
            return True
        return False

    @staticmethod
    def _is_benign_defender_event(message_lower):
        if "[2050]" in message_lower and "has uploaded a file for further analysis" in message_lower:
            return True
        if "microsoft defender antivirus configuration has changed" not in message_lower:
            return False
        if "default\\productappdatapath" in message_lower and "\\programdata\\microsoft" in message_lower:
            return True
        if "windows defender" in message_lower and "\\programdata\\microsoft\\windows defender" in message_lower:
            return True
        return False

    @staticmethod
    def _is_benign_code_integrity_event(message_lower):
        if not message_lower:
            return False
        if "\\programdata\\obs-studio-hook\\" in message_lower and "we-graphics-hook64.dll" in message_lower:
            return True
        if "\\appdata\\local\\programs\\opera gx\\" in message_lower:
            return True
        return False

    def scan_security_events(self):
        self.log("SECURITY EVENT REVIEW", "SECTION")
        seen = set()
        for log_name, days_back, source_label, provider_names in SECURITY_EVENT_LOG_SPECS:
            provider_filter = ""
            if provider_names:
                quoted = ", ".join("'" + str(name).replace("'", "''") + "'" for name in provider_names)
                provider_filter = f"; ProviderName=@({quoted})"
            script = (
                "try { "
                f"$since = (Get-Date).AddDays(-{days_back}); "
                f"Get-WinEvent -FilterHashtable @{{LogName='{log_name}'; StartTime=$since{provider_filter}}} -ErrorAction Stop | "
                "Select-Object -First 40 TimeCreated, Id, ProviderName, Message | ConvertTo-Json -Compress "
                "} catch { }"
            )
            rows = self._run_powershell_json(script, timeout=35)
            if rows is None:
                self.log(f"PowerShell unavailable - {source_label} event review skipped", "WARN")
                return

            for row in rows:
                try:
                    message = str(row.get("Message") or "").strip()
                    if not self._is_suspicious_security_event(source_label, message):
                        continue

                    event_id = str(row.get("Id") or "")
                    provider = str(row.get("ProviderName") or source_label)
                    compact = " ".join(message.split())
                    compact = compact[:220] + ("..." if len(compact) > 220 else "")
                    fingerprint = (source_label, event_id, compact)
                    if fingerprint in seen:
                        continue
                    seen.add(fingerprint)

                    severity = "HIGH" if self._has_strong_campaign_context(message) else "MEDIUM"
                    self._add(
                        severity,
                        "Security Event Review",
                        f"{source_label} event requires review: {provider} [{event_id}] {compact}",
                        log_name,
                    )
                except Exception as exc:
                    self.log(f"{source_label} event review warning: {exc}", "WARN")

    def _evaluate_firewall_rule(self, rule_name, display_name, direction, program):
        normalized_program = self._normalized_path(program)
        if not normalized_program:
            return None

        program_name = os.path.basename(normalized_program)
        base_name = os.path.splitext(program_name)[0]
        strong = self._has_strong_campaign_context(rule_name, display_name, program)
        if strong:
            return {
                "severity": "HIGH",
                "actionable": True,
            }

        if self._is_safe_process_context(program_name, program, display_name, allow_metadata=True):
            return None
        if not self._path_in_user_writable_exec_zone(normalized_program):
            return None

        suspicious_score = 0
        if self._contains_marker(normalized_program, PROCESS_IOC_MARKERS):
            suspicious_score += 2
        if self._contains_marker(normalized_program, CAMPAIGN_DIR_MARKERS):
            suspicious_score += 2
        if self._looks_random(base_name):
            suspicious_score += 2
        if self._in_temp(normalized_program):
            suspicious_score += 2
        if self.paranoid and any(marker in normalized_program for marker in COMMON_USERLAND_EXEC_MARKERS):
            suspicious_score += 1

        threshold = 1 if self.paranoid else 2
        if suspicious_score < threshold:
            return None

        return {
            "severity": "HIGH" if suspicious_score >= 3 else "MEDIUM",
            "actionable": suspicious_score >= 3 and "inbound" in direction.lower(),
        }

    def scan_firewall_rules(self):
        self.log("FIREWALL RULE REVIEW", "SECTION")
        rows = self._run_powershell_json(
            "try { "
            "Get-NetFirewallRule -Enabled True -Action Allow -ErrorAction Stop | "
            "ForEach-Object { "
            "$rule = $_; "
            "$app = $rule | Get-NetFirewallApplicationFilter -ErrorAction SilentlyContinue | Select-Object -First 1; "
            "[pscustomobject]@{ "
            "Name=$rule.Name; "
            "DisplayName=$rule.DisplayName; "
            "Direction=[string]$rule.Direction; "
            "Program=($app.Program) "
            "} "
            "} | ConvertTo-Json -Compress "
            "} catch { }",
            timeout=45,
        )
        if rows is None:
            self.log("PowerShell unavailable - firewall review skipped", "WARN")
            return

        for row in rows:
            if self._stop:
                return
            try:
                rule_name = str(row.get("Name") or "")
                display_name = str(row.get("DisplayName") or "")
                direction = str(row.get("Direction") or "")
                program = str(row.get("Program") or "")
                if not program:
                    continue

                finding = self._evaluate_firewall_rule(rule_name, display_name, direction, program)
                if not finding:
                    continue

                action = None
                if finding["actionable"]:
                    action = lambda name=rule_name: self._delete_firewall_rule(name)

                self._add(
                    finding["severity"],
                    "Firewall Rule Review",
                    f"Allow firewall rule points at suspicious program: {display_name or rule_name} -> {program}",
                    rule_name or display_name,
                    action,
                )
            except Exception as exc:
                self.log(f"Firewall review warning: {exc}", "WARN")

    @staticmethod
    def _path_in_user_writable_exec_zone(path):
        pl = (path or "").lower()
        return any(marker in pl for marker in USER_WRITABLE_DIR_MARKERS)

    @staticmethod
    def _looks_script_host(pname, cmdline_lower):
        return pname in {"python.exe", "pythonw.exe", "wscript.exe", "cscript.exe", "mshta.exe", "rundll32.exe"} or any(
            host in cmdline_lower for host in ("python.exe", "pythonw.exe", "wscript", "cscript", "mshta", "rundll32")
        )

    def _has_actionable_script_host_context(self, pexe, cmdline):
        cmdline_lower = self._normalize_cmdline(cmdline).lower()
        target = self._extract_command_target(cmdline)
        normalized_target = self._normalized_path(target) if self._is_pathlike_command_target(target) else ""
        normalized_exe = self._normalized_path(pexe)

        strong_cmdline_markers = STRONG_CAMPAIGN_MARKERS - {"renpy"}
        if self._contains_marker(cmdline_lower, strong_cmdline_markers):
            return True
        if self._looks_like_temp_stage_launcher(normalized_target):
            return True
        if GODOT_APP_USERDATA_MARKER in normalized_target and any(marker in cmdline_lower for marker in ASAR_ARGUMENT_MARKERS):
            return True
        if normalized_target and self._path_in_user_writable_exec_zone(normalized_target):
            base = os.path.splitext(os.path.basename(normalized_target))[0]
            if self._looks_random(base) or self._contains_marker(normalized_target, PROCESS_IOC_MARKERS):
                return True
        if normalized_exe and self._path_in_user_writable_exec_zone(normalized_exe):
            return True
        return False

    def _is_protected_core_process(self, pname, pexe):
        return pname in PROTECTED_CORE_PROCESS_NAMES and self._is_protected_system_path(pexe)

    def _is_protected_security_process(self, pname, pexe):
        return pname in PROTECTED_SECURITY_PROCESS_NAMES and (
            self._is_trusted_vendor_path(pexe)
            or self._is_protected_system_path(pexe)
            or self._has_trusted_file_metadata(pexe)
        )

    def _is_protected_shell_host(self, pname, pexe):
        return pname in {"cmd.exe", "powershell.exe", "pwsh.exe", "wscript.exe", "cscript.exe", "mshta.exe", "rundll32.exe"} and self._is_protected_core_process(pname, pexe)

    def _shell_host_has_explicit_malware_target(self, cmdline):
        cmdline_lower = self._normalize_cmdline(cmdline).lower()
        target = self._extract_command_target(cmdline)
        if not self._is_pathlike_command_target(target):
            return False

        normalized_target = self._normalized_path(target)
        base = os.path.splitext(os.path.basename(normalized_target))[0]
        ext = os.path.splitext(normalized_target)[1]

        if self._looks_like_temp_stage_launcher(normalized_target):
            return True
        if GODOT_APP_USERDATA_MARKER in normalized_target and any(marker in cmdline_lower for marker in ASAR_ARGUMENT_MARKERS):
            return True
        if self._path_in_user_writable_exec_zone(normalized_target):
            if self._contains_marker(normalized_target, PROCESS_IOC_MARKERS):
                return True
            if ext in {".exe", ".dll", ".bat", ".cmd", ".hta", ".js", ".ps1", ".py", ".pyc", ".pyo", ".vbs"} and self._looks_random(base):
                return True
        return False

    @staticmethod
    def _has_external_raddr(conn):
        try:
            if not conn.raddr:
                return False
            ip = getattr(conn.raddr, "ip", "") or ""
            return ip not in {"127.0.0.1", "::1", "0.0.0.0"}
        except Exception:
            return False

    # ── Filesystem scan ─────────────────────────────────────────────────────

    def scan_filesystem(self):
        self.log("── FILESYSTEM SCAN ────────────────────────────────────", "SECTION")
        visited = 0

        for root in SCAN_ROOTS:
            if not root or not os.path.isdir(root):
                continue
            self.log(f"Entering: {root}", "INFO")

            try:
                for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                    if self._stop:
                        return
                    dirpath_lower = dirpath.lower()
                    if self._should_skip_walk_dir(dirpath) and not self._contains_marker(dirpath_lower, CAMPAIGN_DIR_MARKERS):
                        dirnames.clear()
                        continue

                    dirnames[:] = [
                        d for d in dirnames
                        if not self._should_skip_walk_dir(os.path.join(dirpath, d))
                        or self._contains_marker(os.path.join(dirpath, d).lower(), CAMPAIGN_DIR_MARKERS)
                    ]

                    depth = dirpath.replace(root, "").count(os.sep)
                    if depth > 7:
                        dirnames.clear()
                        continue

                    visited += 1
                    if visited % 40 == 0:
                        self.progress(f"Walked {visited} dirs…  {dirpath[:65]}")

                    dir_names_lower = {d.lower() for d in dirnames}
                    file_names_lower = {f.lower() for f in filenames}
                    bundle_hit = self._evaluate_renpy_bundle(dirpath, dir_names_lower, filenames)
                    if bundle_hit:
                        sev, category, description = bundle_hit
                        dp = dirpath
                        self._add(
                            sev,
                            category,
                            description,
                            dp,
                            lambda p=dp: self._nuke_directory(p),
                        )

                    if self._contains_marker(dirpath, CAMPAIGN_DIR_MARKERS):
                        dp = dirpath
                        self._add("CRITICAL", "Persistence Staging Directory",
                                  f"HijackLoader persistence directory at: {dp}", dp,
                                  lambda p=dp: self._nuke_directory(p))

                    if self._looks_like_hijackloader_stage_dir(dirpath, file_names_lower):
                        dp = dirpath
                        self._add("CRITICAL", "HijackLoader Stage Directory",
                                  f"HijackLoader stage directory at: {dp}", dp,
                                  lambda p=dp: self._nuke_directory(p))
                    elif self._looks_like_netsupport_stage_dir(dirpath, file_names_lower):
                        dp = dirpath
                        self._add("HIGH", "Suspicious Loader Stage Directory",
                                  f"NetSupport-style RAT staging directory detected in a suspicious location: {dp}", dp,
                                  lambda p=dp: self._nuke_directory(p))
                    elif self._looks_like_suspicious_temp_stage_dir(dirpath, file_names_lower):
                        dp = dirpath
                        self._add("HIGH", "Suspicious Temp Stage Directory",
                                  f"Temp staging directory shows downloader or sideload layout: {dp}", dp,
                                  lambda p=dp: self._nuke_directory(p))
                    elif self._looks_like_generic_loader_stage_dir(dirpath, file_names_lower):
                        dp = dirpath
                        self._add("HIGH", "Suspicious Loader Stage Directory",
                                  f"Loader staging directory pattern detected: {dp}", dp,
                                  lambda p=dp: self._nuke_directory(p))

                    for fname in filenames:
                        fl = fname.lower()
                        fpath = os.path.join(dirpath, fname)
                        fpath_lower = fpath.lower()

                        exact_ioc = self._matches_exact_ioc_hash(fpath, fname)
                        if exact_ioc:
                            self._add("CRITICAL", "Exact IOC Hash",
                                      f"Exact IOC hash match ({exact_ioc}): {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))
                            continue

                        if fl in ("instaler.exe", "instaler.py", "instaler.pyo",
                                  "instaler.pyc", "lnstaier.exe", "iviewers.dll"):
                            self._add("CRITICAL", "Malicious File",
                                      f"Known RenKill IOC: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

                        elif fl in ("archive.rpa", "script.rpyc") and self._in_temp(dirpath):
                            self._add("HIGH", "Malicious Archive/Script",
                                      f"RenEngine payload in temp: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

                        elif fl in NETSUPPORT_STAGE_FILENAMES and self._looks_like_suspicious_netsupport_path(fpath, allow_metadata=True):
                            category = "Dropped Executable" if fl.endswith((".exe", ".dll")) else "Persistence Artifact"
                            description = (
                                f"NetSupport-style RAT component found in a suspicious location: {fpath}"
                                if category == "Dropped Executable"
                                else f"NetSupport-style RAT configuration or license artifact found in a suspicious location: {fpath}"
                            )
                            self._add("HIGH", category, description, fpath,
                                      lambda p=fpath: self._delete_file(p))

                        elif fl == "__init__.py" and "renpy" in dirpath.lower() and self._in_temp(dirpath):
                            self._add("HIGH", "Hijacked Module Init",
                                      f"Malicious __init__.py in renpy temp dir: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

                        elif fl.endswith(".key") and self._in_temp(dirpath):
                            self._add("MEDIUM", "Payload Key File",
                                      f"Encrypted payload .key in temp: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

                        elif fl in HIJACKLOADER_STAGE_FILES and self._looks_like_hijackloader_stage_dir(dirpath, file_names_lower):
                            sev = "CRITICAL" if fl in {"w8cpbgqi.exe", "cc32290mt.dll"} else "HIGH"
                            self._add(sev, "HijackLoader Stage Artifact",
                                      f"HijackLoader stage artifact: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

                        elif fl in LOADER_CONTAINER_DLLS and self._looks_like_hijackloader_stage_dir(dirpath, file_names_lower):
                            self._add("HIGH", "Loader Container DLL",
                                      f"Suspicious loader container DLL in stage directory: {fpath}",
                                      fpath, lambda p=fpath: self._delete_file(p))

                        elif fl in CAMPAIGN_FILENAMES and (
                            self._contains_marker(fpath, CAMPAIGN_DIR_MARKERS)
                            or "\\programdata\\" in fpath_lower
                            or "\\appdata\\roaming\\" in fpath_lower
                            or "\\appdata\\local\\" in fpath_lower
                        ):
                            sev = "CRITICAL" if fl in {"froodjurain.wkk", "chime.exe", "zoneind.exe"} else "HIGH"
                            self._add(sev, "Persistence Artifact",
                                      f"HijackLoader/ACR persistence artifact: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

                        elif fl.endswith(".lnk") and (
                            "\\desktop\\" in fpath_lower
                            or fpath_lower.endswith("\\desktop")
                        ) and self._file_contains_ascii_or_utf16le(
                            fpath,
                            ("broker_crypt_v4_i386", "chime.exe", "zoneind.exe", "froodjurain.wkk")
                        ):
                            self._add("HIGH", "Malicious Shortcut",
                                      f"Desktop shortcut referencing RenEngine persistence: {fpath}",
                                      fpath, lambda p=fpath: self._delete_file(p))

                        elif (fl.endswith(".exe") and self._in_temp(dirpath)
                              and self._looks_random(fname[:-4])):
                            self._add("HIGH", "Dropped Executable",
                                      f"Random-named EXE in temp (likely HijackLoader drop): {fpath}",
                                      fpath, lambda p=fpath: self._delete_file(p))

                        elif self._is_user_visible_root(root) and self._is_probable_source_lure(fpath, fname):
                            self._add("MEDIUM", "Source Lure Artifact",
                                      f"Possible infection source or lure file: {fpath}",
                                      fpath, lambda p=fpath: self._delete_file(p))

            except PermissionError:
                pass
            except Exception as exc:
                self.log(f"Walk error: {exc}", "WARN")

    @staticmethod
    def _looks_random(name: str) -> bool:
        if not name or len(name) < 6 or len(name) > 20:
            return False
        if not name.isalnum():
            return False
        has_upper = any(c.isupper() for c in name)
        has_lower = any(c.islower() for c in name)
        has_digit = any(c.isdigit() for c in name)
        return has_upper and has_lower and has_digit

    @staticmethod
    def _add_process_seed(seeds, pid, severity, category, description, path):
        existing = seeds.get(pid)
        rank = Threat.SEVERITY_ORDER
        if existing and rank.get(existing["severity"], 99) <= rank.get(severity, 99):
            return
        seeds[pid] = {
            "severity": severity,
            "category": category,
            "description": description,
            "path": path,
        }

    def _collect_connected_pids(self):
        connected_pids = set()
        if not self.paranoid:
            return connected_pids
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.pid and self._has_external_raddr(conn):
                    connected_pids.add(conn.pid)
        except Exception as exc:
            self.log(f"Paranoid network correlation skipped: {exc}", "WARN")
        return connected_pids

    def _collect_process_rows(self):
        proc_rows = []
        parent_to_children = {}
        proc_by_pid = {}
        scanned = 0

        for proc in psutil.process_iter():
            if self._stop:
                return None, None, None
            try:
                pid = proc.pid
                ppid = self._safe_proc_ppid(proc)
                pname = self._safe_proc_name(proc)
                pexe = self._safe_proc_exe(proc)
                cmdline = self._safe_proc_cmdline(proc)
                row = {
                    "pid": pid,
                    "ppid": ppid,
                    "name": pname,
                    "exe": pexe,
                    "exe_lower": pexe.lower(),
                    "cmdline": cmdline,
                    "cmdline_lower": cmdline.lower(),
                }
                proc_rows.append(row)
                proc_by_pid[pid] = row
                parent_to_children.setdefault(ppid, []).append(pid)
                scanned += 1
                if scanned % 40 == 0:
                    self.progress(f"Indexed {scanned} processes...")
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue

        return proc_rows, parent_to_children, proc_by_pid

    def _seed_process_hit(self, row, connected_pids, seeds):
        pid = row["pid"]
        pname = row["name"]
        pexe = row["exe"]
        pexe_lower = row["exe_lower"]
        cmdline = row["cmdline"]
        cmdline_lower = row["cmdline_lower"]

        if pname in {"cmd.exe", "powershell.exe", "pwsh.exe", "python.exe", "pythonw.exe"} and (
            self._is_local_tool_context(pexe, cmdline) or self._is_project_like_path(self._extract_command_target(cmdline) or cmdline)
        ):
            return
        if self._is_protected_security_process(pname, pexe):
            return
        if self._is_protected_core_process(pname, pexe):
            if self._is_protected_shell_host(pname, pexe) and self._shell_host_has_explicit_malware_target(cmdline):
                pass
            else:
                return
        if self._is_protected_shell_host(pname, pexe) and not self._shell_host_has_explicit_malware_target(cmdline):
            return

        if pexe and self._in_startup_persistence_root(pexe):
            self._add_process_seed(
                seeds,
                pid,
                "CRITICAL",
                "Startup-Launched Process",
                f"Process is running directly from a Windows Startup folder: {pname} (PID {pid})  {pexe}",
                pexe,
            )
            return

        if pexe and any(temp_root and temp_root in pexe_lower for temp_root in self._temp_paths()):
            self._add_process_seed(
                seeds,
                pid,
                "CRITICAL",
                "Process in Temp",
                f"Process running from temp: {pname} (PID {pid})  {pexe}",
                pexe,
            )
            return

        if pname in CAMPAIGN_PROCESS_NAMES:
            self._add_process_seed(
                seeds,
                pid,
                "CRITICAL",
                "Malicious Process",
                f"Known RenEngine process: {pname} (PID {pid})  {pexe or cmdline}",
                pexe or cmdline,
            )
            return

        if pexe and self._looks_like_suspicious_netsupport_path(pexe, allow_metadata=True):
            self._add_process_seed(
                seeds,
                pid,
                "CRITICAL" if pid in connected_pids else "HIGH",
                "Malicious Process",
                f"NetSupport-style remote-control payload is running from a suspicious path: {pname} (PID {pid})  {pexe}",
                pexe,
            )
            return

        if self._contains_marker(pexe_lower, PROCESS_IOC_MARKERS) or (
            self._contains_marker(cmdline_lower, PROCESS_IOC_MARKERS)
            and (pname not in {"powershell.exe", "pwsh.exe", "cmd.exe"} or self._has_actionable_script_host_context(pexe, cmdline))
        ):
            self._add_process_seed(
                seeds,
                pid,
                "CRITICAL",
                "Campaign IOC Process",
                f"Process references RenEngine/HijackLoader artifacts: {pname} (PID {pid})  {pexe or cmdline}",
                pexe or cmdline,
            )
            return

        if self._looks_script_host(pname, cmdline_lower) and self._contains_marker(cmdline_lower, PROCESS_IOC_MARKERS) and self._has_actionable_script_host_context(pexe, cmdline):
            self._add_process_seed(
                seeds,
                pid,
                "CRITICAL",
                "Stealer Script Host",
                f"Script host launched with malware-linked command line: {pname} (PID {pid})  {cmdline}",
                pexe or cmdline,
            )
            return

        if self._is_safe_process_context(pname, pexe, cmdline):
            return

        if pexe and self._path_in_user_writable_exec_zone(pexe_lower):
            if pname in {"python.exe", "pythonw.exe"} and self._contains_marker(cmdline_lower, PROCESS_IOC_MARKERS):
                self._add_process_seed(
                    seeds,
                    pid,
                    "CRITICAL",
                    "Stealer Script Host",
                    f"Python launched from user-writable path with malware-linked args: {pname} (PID {pid})  {cmdline}",
                    pexe or cmdline,
                )
                return

            if pname.endswith(".exe") and pname not in SAFE_PROCESS_NAMES:
                if self._looks_random(pname[:-4]):
                    self._add_process_seed(
                        seeds,
                        pid,
                        "CRITICAL",
                        "Suspicious Userland Process",
                        f"Random-named EXE running from user-writable path: {pname} (PID {pid})  {pexe}",
                        pexe,
                    )
                    return
                if any(marker in pexe_lower for marker in COMMON_USERLAND_EXEC_MARKERS):
                    self._add_process_seed(
                        seeds,
                        pid,
                        "HIGH",
                        "Suspicious Userland Process",
                        f"EXE running from user-writable path: {pname} (PID {pid})  {pexe}",
                        pexe,
                    )

        if pname in {"cmd.exe", "explorer.exe"} and self.paranoid and (
            self._contains_marker(cmdline_lower, PROCESS_IOC_MARKERS)
            or (pexe and not os.path.exists(pexe) and self._path_in_user_writable_exec_zone(pexe_lower))
        ):
            self._add_process_seed(
                seeds,
                pid,
                "CRITICAL",
                "Execution Trace Anomaly",
                f"Windows process showing malware-linked execution trace: {pname} (PID {pid})  {pexe or cmdline}",
                pexe or cmdline,
            )
            return

        if not self.paranoid:
            return

        if self._looks_script_host(pname, cmdline_lower) and (
            self._path_in_user_writable_exec_zone(pexe_lower)
            or self._contains_marker(cmdline_lower, {"appdata", "programdata", "temp", "downloads"})
        ):
            self._add_process_seed(
                seeds,
                pid,
                "HIGH",
                "Paranoid Script Host",
                f"Script-capable host in user-writable execution zone: {pname} (PID {pid})  {pexe or cmdline}",
                pexe or cmdline,
            )
            return

        if pid in connected_pids and pexe and self._path_in_user_writable_exec_zone(pexe_lower) and pname not in SAFE_PROCESS_NAMES:
            severity = "CRITICAL" if (self._looks_random(pname[:-4]) or self._contains_marker(pexe_lower, PROCESS_IOC_MARKERS)) else "HIGH"
            self._add_process_seed(
                seeds,
                pid,
                severity,
                "Paranoid Networked Process",
                f"Network-active executable running from user-writable path: {pname} (PID {pid})  {pexe}",
                pexe,
            )
            return

        if (
            pname.endswith(".exe")
            and pname not in SAFE_PROCESS_NAMES
            and any(token in pname for token in PARANOID_NAME_TOKENS)
            and self._path_in_user_writable_exec_zone(pexe_lower)
        ):
            self._add_process_seed(
                seeds,
                pid,
                "HIGH",
                "Paranoid Masquerade Process",
                f"Masquerading helper/service-style EXE in user-writable path: {pname} (PID {pid})  {pexe}",
                pexe,
            )

    def _expand_process_hits(self, seeds, parent_to_children, proc_by_pid):
        expanded = set()
        queue = list(seeds)
        expanded_count = 0

        while queue:
            current = queue.pop(0)
            if current in expanded:
                continue
            expanded.add(current)
            expanded_count += 1
            if expanded_count % 25 == 0:
                self.progress(f"Tracing {expanded_count} flagged process links...")
            for child_pid in parent_to_children.get(current, []):
                if child_pid not in expanded:
                    queue.append(child_pid)

        for pid in list(seeds):
            for child_pid in parent_to_children.get(pid, []):
                child = proc_by_pid.get(child_pid)
                if not child or child_pid in seeds:
                    continue
                if self._is_safe_process_context(child["name"], child["exe"], child["cmdline"]):
                    continue
                self._add_process_seed(
                    seeds,
                    child_pid,
                    "HIGH",
                    "Malicious Child Process",
                    f"Child of flagged malware-linked process: {child['name']} (PID {child_pid}) parent PID {pid}",
                    child["exe"] or child["cmdline"],
                )

        for pid in expanded:
            row = proc_by_pid.get(pid)
            if not row or pid in seeds:
                continue
            if self._is_safe_process_context(row["name"], row["exe"], row["cmdline"]):
                continue
            self._add_process_seed(
                seeds,
                pid,
                "HIGH",
                "Malicious Child Process",
                f"Descendant of flagged malware-linked process: {row['name']} (PID {pid}) parent PID {row['ppid']}",
                row["exe"] or row["cmdline"],
            )

    def _flush_process_hits(self, seeds):
        sort_key = lambda item: (Threat.SEVERITY_ORDER.get(item[1]["severity"], 99), item[0])
        for pid, info in sorted(seeds.items(), key=sort_key):
            self._add(
                info["severity"],
                info["category"],
                info["description"],
                info["path"],
                lambda p=pid: self._kill_process_tree(p),
            )

    # ── Process scan ────────────────────────────────────────────────────────

    def scan_processes(self):
        self.log("── PROCESS SCAN ───────────────────────────────────────", "SECTION")
        if not PSUTIL_OK:
            self.log("psutil unavailable — process scan skipped", "WARN")
            return

        connected_pids = self._collect_connected_pids()
        proc_rows, parent_to_children, proc_by_pid = self._collect_process_rows()
        if proc_rows is None:
            return

        seeds = {}
        for index, row in enumerate(proc_rows, 1):
            self._seed_process_hit(row, connected_pids, seeds)
            if index % 40 == 0:
                self.progress(f"Analyzed {index} processes...")

        self._expand_process_hits(seeds, parent_to_children, proc_by_pid)
        self._module_scan_pid_targets = set(seeds)
        self._flush_process_hits(seeds)

    # ── Network scan ────────────────────────────────────────────────────────

    def scan_network(self):
        self.log("── NETWORK SCAN ───────────────────────────────────────", "SECTION")
        if not PSUTIL_OK:
            self.log("psutil unavailable — network scan skipped", "WARN")
            return

        try:
            for conn in psutil.net_connections(kind="inet"):
                if self._stop:
                    return
                if not conn.raddr:
                    continue
                if conn.raddr.ip in C2_IPS:
                    try:
                        pname = psutil.Process(conn.pid).name() if conn.pid else "unknown"
                    except Exception:
                        pname = "unknown"
                    self._add("CRITICAL", "Active C2 Connection",
                              f"Live C2 connection to {conn.raddr.ip}:{conn.raddr.port}  process: {pname} (PID {conn.pid})",
                              conn.raddr.ip,
                              lambda p=conn.pid: self._kill_pid(p) if p else None)
        except Exception as exc:
            self.log(f"Network scan error: {exc}", "WARN")

    # ── Scheduled task scan ─────────────────────────────────────────────────

    def scan_scheduled_tasks(self):
        self.log("── SCHEDULED TASK SCAN ────────────────────────────────", "SECTION")
        try:
            for row in self._collect_scheduled_task_rows():
                if self._stop:
                    return
                finding = self._evaluate_scheduled_task_entry(
                    row.get("TaskName"),
                    row.get("TaskPath"),
                    row.get("Execute"),
                    row.get("Arguments"),
                    row.get("WorkingDirectory"),
                )
                if not finding:
                    continue
                severity, category, description = finding
                task_name = f"{row.get('TaskPath') or ''}{row.get('TaskName') or ''}"
                self._add(
                    severity,
                    category,
                    description,
                    task_name,
                    lambda t=task_name: self._delete_task(t),
                )
        except Exception as exc:
            self.log(f"Task scan error: {exc}", "WARN")

    # ── Registry scan ───────────────────────────────────────────────────────

    def scan_registry(self):
        self.log("── REGISTRY SCAN ──────────────────────────────────────", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable — registry scan skipped", "WARN")
            return

        hives = [
            (winreg.HKEY_CURRENT_USER,  "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE, "HKLM"),
        ]
        subkeys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
        ]

        for hive, hive_name in hives:
            for subkey in subkeys:
                try:
                    key = winreg.OpenKey(hive, subkey)
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            if self._value_has_malware_signal(value):
                                full_key = f"{hive_name}\\{subkey}"
                                self._add("HIGH", "Registry Persistence",
                                          f"Autorun: {full_key}  [{name}] = {value[:100]}",
                                          full_key,
                                          lambda h=hive, sk=subkey, n=name: self._delete_reg_val(h, sk, n))
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except (FileNotFoundError, PermissionError):
                    pass

        ifeo_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\Image File Execution Options", "HKLM"),
        ]
        for hive, subkey, hive_name in ifeo_roots:
            try:
                root = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            idx = 0
            while True:
                try:
                    image_name = winreg.EnumKey(root, idx)
                except OSError:
                    break
                idx += 1

                image_path = f"{hive_name}\\{subkey}\\{image_name}"
                try:
                    child = winreg.OpenKey(hive, subkey + "\\" + image_name)
                except (FileNotFoundError, PermissionError):
                    continue

                for value_name in ("Debugger", "VerifierDlls", "GlobalFlag"):
                    try:
                        value = winreg.QueryValueEx(child, value_name)[0]
                    except OSError:
                        continue
                    if self._value_has_malware_signal(value):
                        self._add(
                            "CRITICAL" if value_name == "Debugger" else "HIGH",
                            "IFEO Persistence",
                            f"IFEO hijack on {image_name}: {value_name} = {value}",
                            image_path,
                            lambda h=hive, sk=subkey + "\\" + image_name, n=value_name: self._delete_reg_val(h, sk, n),
                        )
                try:
                    winreg.CloseKey(child)
                except Exception:
                    pass
            try:
                winreg.CloseKey(root)
            except Exception:
                pass

        appinit_locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows", "HKLM"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\Windows", "HKLM"),
        ]
        for hive, subkey, hive_name in appinit_locations:
            try:
                key = winreg.OpenKey(hive, subkey)
            except (FileNotFoundError, PermissionError):
                continue

            try:
                appinit_value = str(winreg.QueryValueEx(key, "AppInit_DLLs")[0] or "")
            except OSError:
                appinit_value = ""
            if appinit_value and self._value_has_malware_signal(appinit_value):
                self._add(
                    "CRITICAL",
                    "AppInit Persistence",
                    f"AppInit_DLLs contains suspicious DLL path(s): {appinit_value}",
                    f"{hive_name}\\{subkey}",
                    lambda h=hive, sk=subkey, n="AppInit_DLLs": self._delete_reg_val(h, sk, n),
                )
            try:
                winreg.CloseKey(key)
            except Exception:
                pass

    def scan_policy_persistence(self):
        self.log("POLICY PERSISTENCE REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - policy persistence review skipped", "WARN")
            return

        for row in self._collect_policy_persistence_rows():
            if self._stop:
                return
            finding = self._looks_suspicious_policy_persistence(row)
            if not finding:
                continue
            severity, category, description = finding
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            action = None
            if severity == "HIGH":
                action = lambda h=row.get("Hive"), sk=row.get("Subkey"), n=row.get("ValueName"): self._delete_reg_val(h, sk, n)
            self._add(
                severity,
                category,
                description,
                location,
                action,
            )

    def scan_runonceex_persistence(self):
        self.log("RUNONCEEX REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - RunOnceEx review skipped", "WARN")
            return

        for row in self._collect_runonceex_rows():
            if self._stop:
                return
            finding = self._looks_suspicious_runonceex(row)
            if not finding:
                continue
            severity, category, description = finding
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            self._add(
                severity,
                category,
                description,
                location,
                lambda h=row.get("Hive"), sk=row.get("Subkey"), n=row.get("ValueName"): self._delete_reg_val(h, sk, n),
            )

    def scan_active_setup_persistence(self):
        self.log("ACTIVE SETUP REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - Active Setup review skipped", "WARN")
            return

        for row in self._collect_active_setup_rows():
            if self._stop:
                return
            finding = self._looks_suspicious_active_setup(row)
            if not finding:
                continue
            severity, category, description = finding
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[StubPath]"
            self._add(
                severity,
                category,
                description,
                location,
                lambda h=row.get("Hive"), sk=row.get("Subkey"), n="StubPath": self._delete_reg_val(h, sk, n),
            )

    def scan_session_manager_review(self):
        self.log("SESSION MANAGER REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - session manager review skipped", "WARN")
            return

        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager")
        except (FileNotFoundError, PermissionError):
            key = None

        if key:
            try:
                try:
                    boot_execute = winreg.QueryValueEx(key, "BootExecute")[0]
                except OSError:
                    boot_execute = []
                boot_values = boot_execute if isinstance(boot_execute, (list, tuple)) else [boot_execute]
                normalized_boot = [self._normalize_cmdline(item).strip() for item in boot_values if str(item or "").strip()]
                if normalized_boot and [item.lower() for item in normalized_boot] != ["autocheck autochk *"]:
                    joined = " | ".join(normalized_boot)
                    severity = "HIGH" if self._value_has_malware_signal(joined) else "MEDIUM"
                    self._add(
                        severity,
                        "Session Manager Review",
                        f"BootExecute differs from the normal autocheck value: {joined}",
                        r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager[BootExecute]",
                    )

                try:
                    excluded_known_dlls = str(winreg.QueryValueEx(key, "ExcludeFromKnownDlls")[0] or "")
                except OSError:
                    excluded_known_dlls = ""
                if excluded_known_dlls and self._value_has_malware_signal(excluded_known_dlls):
                    self._add(
                        "HIGH",
                        "Session Manager Review",
                        f"ExcludeFromKnownDlls contains suspicious DLL names: {excluded_known_dlls}",
                        r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager[ExcludeFromKnownDlls]",
                    )
            finally:
                try:
                    winreg.CloseKey(key)
                except Exception:
                    pass

        try:
            known_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\KnownDLLs")
        except (FileNotFoundError, PermissionError):
            known_key = None

        if known_key:
            try:
                try:
                    dll_directory = str(winreg.QueryValueEx(known_key, "DllDirectory")[0] or "")
                except OSError:
                    dll_directory = ""
                if dll_directory:
                    normalized_dir = self._normalized_path(dll_directory)
                    if self._value_has_malware_signal(dll_directory) or (
                        normalized_dir
                        and "\\system32" not in normalized_dir
                        and "\\syswow64" not in normalized_dir
                        and "%systemroot%" not in dll_directory.lower()
                    ):
                        self._add(
                            "HIGH",
                            "KnownDLLs Review",
                            f"KnownDLLs DllDirectory points outside normal system DLL paths: {dll_directory}",
                            r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\KnownDLLs[DllDirectory]",
                        )

                index = 0
                while True:
                    try:
                        value_name, value, _ = winreg.EnumValue(known_key, index)
                    except OSError:
                        break
                    index += 1
                    if str(value_name or "").lower() in {"dlldirectory"}:
                        continue
                    raw = self._normalize_cmdline(value).strip()
                    if not raw:
                        continue
                    lowered = raw.lower()
                    if self._value_has_malware_signal(raw) or any(token in lowered for token in ("\\", "/", ":")):
                        self._add(
                            "HIGH",
                            "KnownDLLs Review",
                            f"KnownDLLs entry {value_name} points at an unusual DLL target: {raw}",
                            rf"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\KnownDLLs[{value_name}]",
                        )
            finally:
                try:
                    winreg.CloseKey(known_key)
                except Exception:
                    pass

        try:
            appcert_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\AppCertDlls")
        except (FileNotFoundError, PermissionError):
            appcert_key = None

        if appcert_key:
            try:
                index = 0
                while True:
                    try:
                        value_name, value, _ = winreg.EnumValue(appcert_key, index)
                    except OSError:
                        break
                    index += 1
                    raw = self._normalize_cmdline(value).strip()
                    if not raw:
                        continue
                    target = self._extract_command_target(raw) or raw
                    normalized_target = self._normalized_path(target)
                    if self._value_has_malware_signal(raw) or (
                        normalized_target
                        and any(marker in normalized_target for marker in COMMON_USERLAND_EXEC_MARKERS)
                        and not self._is_trusted_vendor_path(normalized_target)
                    ):
                        self._add(
                            "HIGH",
                            "AppCert Persistence",
                            f"AppCertDlls entry injects a suspicious DLL: {value_name} = {raw}",
                            rf"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\AppCertDlls[{value_name}]",
                            lambda n=value_name: self._delete_reg_val(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\AppCertDlls", n),
                        )
            finally:
                try:
                    winreg.CloseKey(appcert_key)
                except Exception:
                    pass

    def scan_safeboot_review(self):
        self.log("SAFEBOOT REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - SafeBoot review skipped", "WARN")
            return

        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\SafeBoot")
        except (FileNotFoundError, PermissionError):
            return

        try:
            try:
                alternate_shell = str(winreg.QueryValueEx(key, "AlternateShell")[0] or "")
            except OSError:
                alternate_shell = ""
        finally:
            try:
                winreg.CloseKey(key)
            except Exception:
                pass

        if not alternate_shell:
            return

        normalized = self._normalize_cmdline(alternate_shell).strip()
        lowered = normalized.lower().replace(" ", "")
        if lowered in {"cmd.exe", r"%systemroot%\system32\cmd.exe", r"c:\windows\system32\cmd.exe"}:
            return

        severity = "HIGH" if self._value_has_malware_signal(normalized) else "MEDIUM"
        self._add(
            severity,
            "SafeBoot Review",
            f"SafeBoot AlternateShell differs from the normal cmd.exe value: {normalized}",
            r"HKLM\SYSTEM\CurrentControlSet\Control\SafeBoot[AlternateShell]",
        )

    def scan_logon_persistence(self):
        self.log("LOGON PERSISTENCE REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - logon persistence review skipped", "WARN")
            return

        for row in self._collect_logon_persistence_rows():
            if self._stop:
                return
            finding = self._looks_suspicious_logon_persistence(row)
            if not finding:
                continue
            severity, category, description = finding
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            action = None
            if category == "Logon Script Persistence" and severity == "HIGH":
                action = lambda h=row.get("Hive"), sk=row.get("Subkey"), n=row.get("ValueName"): self._delete_reg_val(h, sk, n)
            self._add(
                severity,
                category,
                description,
                location,
                action,
            )

    def scan_explorer_hijacks(self):
        self.log("EXPLORER HIJACK REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - Explorer hijack review skipped", "WARN")
            return

        for row in self._collect_explorer_hijack_rows():
            if self._stop:
                return
            finding = self._looks_suspicious_explorer_hijack(row)
            if not finding:
                continue
            severity, category, description = finding
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            self._add(
                severity,
                category,
                description,
                location,
            )

    def scan_shell_persistence(self):
        self.log("SHELL PERSISTENCE REVIEW", "SECTION")
        if not WINREG_OK:
            self.log("winreg unavailable - shell persistence review skipped", "WARN")
            return

        for row in self._collect_shell_persistence_rows():
            if self._stop:
                return
            finding = self._looks_suspicious_shell_persistence(row.get("ValueName"), row.get("Value"))
            if not finding:
                continue
            severity, category, description = finding
            location = f"{row.get('HiveName')}\\{row.get('Subkey')}[{row.get('ValueName')}]"
            self._add(
                severity,
                category,
                description,
                location,
            )

    # Remediation helpers

    def _kill_pid(self, pid):
        if pid is None:
            return False
        try:
            if not PSUTIL_OK:
                self._log_safety_block("kill PID without process context", f"PID {pid}")
                return False

            blocked, target = self._should_block_process_remediation(pid)
            if blocked:
                self._log_safety_block("kill protected or trusted process", target)
                return False

            p = psutil.Process(pid)
            p.terminate()
            time.sleep(0.4)
            if p.is_running():
                p.kill()
            self.killed += 1
            if self._recovery_session:
                self._record_recovery_note(f"killed process PID {pid} ({target})")
            self.log(f"Killed PID {pid}", "SUCCESS")
            return True
        except Exception as exc:
            self.log(f"Could not kill PID {pid}: {exc}", "WARN")
            return False

    def _kill_process_tree(self, pid):
        if pid is None:
            return False
        try:
            if not PSUTIL_OK:
                self._log_safety_block("kill process tree without process context", f"PID {pid}")
                return False

            blocked, target = self._should_block_process_remediation(pid)
            if blocked:
                self._log_safety_block("kill protected or trusted process tree", target)
                return False

            root = psutil.Process(pid)
            victims = []
            for proc in root.children(recursive=True):
                try:
                    child_name = (proc.name() or "").lower()
                    child_exe = proc.exe() or ""
                    child_cmd = self._normalize_cmdline(proc.cmdline())
                    if self._is_safe_process_context(child_name, child_exe, child_cmd, allow_metadata=True):
                        self._log_safety_block("kill protected child process", child_exe or child_cmd or child_name)
                        continue
                    victims.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            victims.sort(key=lambda proc: len(proc.children(recursive=True)), reverse=True)

            killed_any = False
            for proc in victims:
                try:
                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            gone, alive = psutil.wait_procs(victims, timeout=0.8)
            for proc in alive:
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            try:
                root.terminate()
                time.sleep(0.4)
                if root.is_running():
                    root.kill()
                killed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            self.killed += len(gone) + len(alive) + (1 if killed_any else 0)
            if self._recovery_session:
                self._record_recovery_note(f"killed process tree rooted at PID {pid} ({target})")
            self.log(f"Killed process tree rooted at PID {pid}", "SUCCESS")
            return True
        except Exception as exc:
            self.log(f"Could not kill process tree for PID {pid}: {exc}", "WARN")
            return self._kill_pid(pid)

    def _delete_file(self, path):
        if not os.path.isfile(path):
            return True
        if self._should_block_path_remediation(path):
            self._log_safety_block("delete protected or trusted file", path)
            return False
        backup_path, quarantine_reason = self._try_move_path_to_recovery(path)
        if backup_path:
            self.removed += 1
            self.log(f"Quarantined and neutralized: {path}", "SUCCESS")
            return True
        if self._is_user_visible_root(path):
            self.log(self._format_removal_failure("quarantine user-visible file safely", path, "the file sits in a user-visible root and recovery snapshot quarantine failed"), "WARN")
            return False
        try:
            os.remove(path)
            self.removed += 1
            self.log(f"Deleted (no recovery snapshot): {path}", "WARN")
            return True
        except PermissionError:
            try:
                subprocess.run(["attrib", "-r", "-s", "-h", path],
                               capture_output=True, creationflags=0x08000000)
                os.remove(path)
                self.removed += 1
                self.log(f"Deleted (forced, no recovery snapshot): {path}", "WARN")
                return True
            except Exception as exc:
                reason = quarantine_reason or "access denied or file is locked by another process"
                self.log(self._format_removal_failure("remove file", path, f"{reason}; forced delete also failed: {exc}"), "WARN")
        except Exception as exc:
            reason = quarantine_reason or "quarantine failed"
            self.log(self._format_removal_failure("remove file", path, f"{reason}; delete failed: {exc}"), "WARN")
        return False

    def _nuke_directory(self, path):
        if not os.path.isdir(path):
            return True
        if self._should_block_path_remediation(path, is_dir=True):
            self._log_safety_block("remove protected or broad directory", path)
            return False
        backup_path, quarantine_reason = self._try_move_path_to_recovery(path)
        if backup_path:
            self.removed += 1
            self.log(f"Quarantined directory: {path}", "SUCCESS")
            return True
        if self._is_user_visible_root(path):
            self.log(self._format_removal_failure("quarantine user-visible directory safely", path, "the directory sits in a user-visible root and recovery snapshot quarantine failed"), "WARN")
            return False
        try:
            shutil.rmtree(path, ignore_errors=True)
            self.removed += 1
            self.log(f"Removed directory (no recovery snapshot): {path}", "WARN")
            return True
        except Exception as exc:
            reason = quarantine_reason or "quarantine failed"
            self.log(self._format_removal_failure("remove directory", path, f"{reason}; directory delete failed: {exc}"), "WARN")
        return False

    def _delete_task(self, task_name):
        backup = self._capture_task_xml(task_name)
        try:
            r = subprocess.run(
                [self._schtasks_path(), "/delete", "/tn", task_name, "/f"],
                capture_output=True, text=True, creationflags=0x08000000
            )
            if r.returncode == 0:
                if backup:
                    self._record_recovery_entry(backup)
                self.removed += 1
                self.log(f"Deleted scheduled task: {task_name}", "SUCCESS")
                return True
            self.log(self._format_removal_failure("delete scheduled task", task_name, self._result_failure_reason(r, "task delete failed")), "WARN")
        except Exception as exc:
            self.log(self._format_removal_failure("delete scheduled task", task_name, exc), "WARN")
        return False

    def _delete_service(self, service_name):
        if not service_name:
            return False
        rows = self._run_powershell_json(
            f"Get-CimInstance Win32_Service -Filter \"Name='{service_name}'\" | "
            "Select-Object Name,PathName | ConvertTo-Json -Compress",
            timeout=20,
        )
        if rows:
            path_name = str(rows[0].get("PathName") or "")
            finding = self._looks_suspicious_service(service_name, "", path_name)
            if not finding:
                self._log_safety_block("delete trusted service", service_name)
                return False
        try:
            subprocess.run(["sc", "stop", service_name], capture_output=True, text=True, timeout=15, creationflags=0x08000000)
            result = subprocess.run(["sc", "delete", service_name], capture_output=True, text=True, timeout=15, creationflags=0x08000000)
            if result.returncode == 0:
                if self._recovery_session:
                    self._record_recovery_note(f"deleted service {service_name}")
                self.removed += 1
                self.log(f"Deleted service: {service_name}", "SUCCESS")
                return True
            self.log(self._format_removal_failure("delete service", service_name, self._result_failure_reason(result, "service delete failed")), "WARN")
        except Exception as exc:
            self.log(self._format_removal_failure("delete service", service_name, exc), "WARN")
        return False

    def _delete_firewall_rule(self, rule_name):
        if not rule_name:
            return False
        backup = self._capture_firewall_rule(rule_name)
        escaped = rule_name.replace("'", "''")
        result = self._run_powershell(
            "try { Remove-NetFirewallRule -Name '" + escaped + "' -ErrorAction Stop } catch { exit 1 }",
            timeout=20,
        )
        if result is not None and result.returncode == 0:
            if backup:
                self._record_recovery_entry(backup)
            self.removed += 1
            self.log(f"Removed firewall rule: {rule_name}", "SUCCESS")
            return True
        self.log(self._format_removal_failure("remove firewall rule", rule_name, self._result_failure_reason(result, "firewall rule removal failed")), "WARN")
        return False

    def _remove_defender_exclusion(self, kind, value):
        if not kind or not value:
            return False
        escaped = str(value).replace("'", "''")
        if kind == "Path":
            script = "try { Remove-MpPreference -ExclusionPath '" + escaped + "' -ErrorAction Stop } catch { exit 1 }"
        elif kind == "Process":
            script = "try { Remove-MpPreference -ExclusionProcess '" + escaped + "' -ErrorAction Stop } catch { exit 1 }"
        elif kind == "Extension":
            script = "try { Remove-MpPreference -ExclusionExtension '" + escaped + "' -ErrorAction Stop } catch { exit 1 }"
        else:
            return False

        result = self._run_powershell(script, timeout=20)
        if result is not None and result.returncode == 0:
            self._record_recovery_entry({
                "kind": "defender_exclusion_remove",
                "exclusion_kind": kind,
                "value": value,
            })
            self.removed += 1
            self.log(f"Removed Defender exclusion: {value}", "SUCCESS")
            return True
        self.log(self._format_removal_failure("remove Defender exclusion", value, self._result_failure_reason(result, "Defender exclusion removal failed")), "WARN")
        return False

    def _capture_defender_pref_state(self):
        rows = self._run_powershell_json(
            "try { "
            "Get-MpPreference -ErrorAction Stop | "
            "Select-Object DisableRealtimeMonitoring,DisableIOAVProtection,DisableScriptScanning | ConvertTo-Json -Compress "
            "} catch { }",
            timeout=25,
        )
        if not rows:
            return None

        row = rows[0]
        return {
            "kind": "defender_pref_restore",
            "settings": {
                "DisableRealtimeMonitoring": bool(row.get("DisableRealtimeMonitoring")),
                "DisableIOAVProtection": bool(row.get("DisableIOAVProtection")),
                "DisableScriptScanning": bool(row.get("DisableScriptScanning")),
            },
        }

    def _repair_defender_protection_defaults(self):
        backup = self._capture_defender_pref_state()
        result = self._run_powershell(
            "try { Set-MpPreference "
            "-DisableRealtimeMonitoring $false "
            "-DisableIOAVProtection $false "
            "-DisableScriptScanning $false "
            "-ErrorAction Stop } catch { exit 1 }",
            timeout=25,
        )
        if result is not None and result.returncode == 0:
            if backup:
                self._record_recovery_entry(backup)
            self.removed += 1
            self.log("Re-enabled Microsoft Defender protection defaults", "SUCCESS")
            return True
        self.log(self._format_removal_failure("re-enable Microsoft Defender protection defaults", "Defender", self._result_failure_reason(result, "Defender protection repair failed")), "WARN")
        return False

    def _remediate_disabled_startup_entry(self, reg_values, shortcut_path=""):
        removed_any = False
        for hive, subkey, name in reg_values:
            removed_any = self._delete_reg_val(hive, subkey, name) or removed_any
        if shortcut_path:
            removed_any = self._delete_file(shortcut_path) or removed_any
        return removed_any

    def _delete_reg_val(self, hive, subkey, name):
        if not WINREG_OK:
            return False
        backup = self._capture_reg_value_entry(hive, subkey, name)
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            if backup:
                self._record_recovery_entry(backup)
            self.removed += 1
            self.log(f"Deleted registry value: {name}", "SUCCESS")
            return True
        except Exception as exc:
            self.log(self._format_removal_failure("delete registry value", f"{subkey}[{name}]", exc), "WARN")
        return False

    def _delete_wmi_subscription(self, filter_name="", consumer_name="", consumer_class=""):
        if not filter_name and not consumer_name:
            return False

        script_lines = []
        if filter_name:
            escaped = filter_name.replace("'", "''")
            script_lines.append(
                "$f = Get-WmiObject -Namespace root\\subscription -Class __EventFilter "
                f"-Filter \"Name='{escaped}'\" -ErrorAction SilentlyContinue; "
                "if ($f) { "
                "$f | ForEach-Object { $_.GetRelated('__FilterToConsumerBinding') | Remove-WmiObject -ErrorAction SilentlyContinue }; "
                "$f | Remove-WmiObject -ErrorAction SilentlyContinue }"
            )
        if consumer_name:
            escaped = consumer_name.replace("'", "''")
            if consumer_class and consumer_class != "__EventFilter":
                script_lines.append(
                    f"$c = Get-WmiObject -Namespace root\\subscription -Class {consumer_class} "
                    f"-Filter \"Name='{escaped}'\" -ErrorAction SilentlyContinue; "
                    "if ($c) { "
                    "$c | ForEach-Object { $_.GetRelated('__FilterToConsumerBinding') | Remove-WmiObject -ErrorAction SilentlyContinue }; "
                    "$c | Remove-WmiObject -ErrorAction SilentlyContinue }"
                )
            else:
                script_lines.append(
                    "$classes = 'CommandLineEventConsumer','ActiveScriptEventConsumer'; "
                    f"foreach ($cls in $classes) {{ $c = Get-WmiObject -Namespace root\\subscription -Class $cls -Filter \"Name='{escaped}'\" -ErrorAction SilentlyContinue; "
                    "if ($c) { $c | ForEach-Object { $_.GetRelated('__FilterToConsumerBinding') | Remove-WmiObject -ErrorAction SilentlyContinue }; "
                    "$c | Remove-WmiObject -ErrorAction SilentlyContinue } }"
                )

        result = self._run_powershell("; ".join(script_lines), timeout=30)
        if result is not None and result.returncode == 0:
            if self._recovery_session:
                self._record_recovery_note(f"removed WMI subscription {filter_name or consumer_name}")
            self.removed += 1
            target = filter_name or consumer_name
            self.log(f"Removed WMI persistence: {target}", "SUCCESS")
            return True
        self.log(self._format_removal_failure("remove WMI persistence", filter_name or consumer_name, self._result_failure_reason(result, "WMI removal failed")), "WARN")
        return False

    def _reset_user_proxy_settings(self):
        if not WINREG_OK:
            return False
        changed = False
        snapshots = []
        for hive, subkey in (
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"),
        ):
            for value_name in ("ProxyEnable", "ProxyServer", "AutoConfigURL"):
                snapshot = self._capture_reg_state(hive, subkey, value_name)
                if snapshot:
                    snapshots.append(snapshot)
            try:
                key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE)
            except (FileNotFoundError, PermissionError):
                continue

            try:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                changed = True
            except Exception:
                pass
            for value_name in ("ProxyServer", "AutoConfigURL"):
                try:
                    winreg.DeleteValue(key, value_name)
                    changed = True
                except Exception:
                    pass
            try:
                winreg.CloseKey(key)
            except Exception:
                pass

        if changed:
            if snapshots:
                self._record_recovery_entry({
                    "kind": "proxy_reset",
                    "snapshots": snapshots,
                })
            self.removed += 1
            self.log("Reset Internet proxy settings", "SUCCESS")
            return True
        return False

    def _capture_winhttp_proxy_state(self):
        try:
            result = subprocess.run(
                ["netsh", "winhttp", "show", "proxy"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=0x08000000,
            )
        except Exception:
            return None
        output = (result.stdout or "").strip()
        if result.returncode != 0 or not output:
            return None

        lowered = output.lower()
        if "direct access (no proxy server)" in lowered:
            return {"kind": "winhttp_proxy_reset", "mode": "direct"}

        proxy = ""
        bypass = ""
        for raw_line in output.splitlines():
            line = raw_line.strip()
            lowered_line = line.lower()
            if lowered_line.startswith("proxy server"):
                proxy = line.split(":", 1)[1].strip() if ":" in line else ""
            elif lowered_line.startswith("bypass list"):
                bypass = line.split(":", 1)[1].strip() if ":" in line else ""

        if not proxy:
            return None
        return {
            "kind": "winhttp_proxy_reset",
            "mode": "custom",
            "proxy": proxy,
            "bypass": bypass,
        }

    def _reset_winhttp_proxy_settings(self):
        backup = self._capture_winhttp_proxy_state()
        if not backup or str(backup.get("mode") or "").lower() == "direct":
            return False

        try:
            result = subprocess.run(
                ["netsh", "winhttp", "reset", "proxy"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=0x08000000,
            )
        except Exception:
            self.log("Could not reset WinHTTP proxy", "WARN")
            return False

        if result.returncode == 0:
            self._record_recovery_entry(backup)
            self.removed += 1
            self.log("Reset WinHTTP proxy settings", "SUCCESS")
            return True
        self.log("Could not reset WinHTTP proxy", "WARN")
        return False

    # ── Orchestration ───────────────────────────────────────────────────────

    def run_full_scan(self):
        self.threats.clear()
        self.killed = 0
        self.removed = 0
        self._stop = False
        self.last_summary = None
        self.cleanup_assessment = None
        self.exposure_notes.clear()
        self.post_cleanup_browser_summary = None
        self._module_scan_pid_targets.clear()
        self._shortcut_scan_rows = None
        self._scheduled_task_rows = None
        self._autorun_rows = None
        self._policy_rows = None
        self._active_setup_rows = None
        self._disabled_startup_rows = None
        self._wmi_rows = None
        self._shell_rows = None
        self._logon_rows = None
        self._explorer_hijack_rows = None
        self.scan_network()
        self.scan_processes()
        self.scan_process_modules()
        self.scan_filesystem()
        self.scan_startup_persistence()
        self.scan_shortcut_targets()
        self.scan_disabled_startup_items()
        self.scan_services()
        self.scan_wmi_persistence()
        self.scan_scheduled_tasks()
        self.scan_registry()
        self.scan_runonceex_persistence()
        self.scan_policy_persistence()
        self.scan_active_setup_persistence()
        self.scan_session_manager_review()
        self.scan_safeboot_review()
        self.scan_logon_persistence()
        self.scan_explorer_hijacks()
        self.scan_shell_persistence()
        self.scan_startup_correlations()
        self.scan_alternate_data_streams()
        self.scan_system_tampering()
        self.scan_defender_posture()
        self.scan_security_posture()
        self.scan_browser_policies()
        self.scan_security_events()
        self.scan_firewall_rules()
        self.scan_installed_programs()
        self.scan_browser_extensions()
        self.threats.sort()
        crit = sum(1 for t in self.threats if t.severity == "CRITICAL")
        high = sum(1 for t in self.threats if t.severity == "HIGH")
        summary = self.summarize_threats()
        cleanup = self.assess_cleanup_state()
        self.scan_exposure_surface()
        exposure = self.assess_account_exposure()
        breakdown = self.finding_breakdown()
        browser_compare = self.post_cleanup_browser_summary or self.compare_post_cleanup_browser_state()
        self.log(
            f"-- SCAN COMPLETE  |  {len(self.threats)} threat(s) found  -  {crit} CRITICAL  {high} HIGH --",
            "SECTION"
        )
        self.log(f"Summary verdict   : {summary['label']}", "CRITICAL" if summary["confidence"] == "high" else "WARN" if summary["confidence"] == "medium" else "INFO")
        self.log(f"Assessment        : {summary['detail']}", "INFO")
        self.log(f"Confirmed items   : {breakdown['confirmed']}  |  Review-first: {breakdown['review']}  |  Other: {breakdown['other']}", "INFO")
        self.log(f"Local confidence  : {cleanup['score']}%  -  {cleanup['label']}", "WARN" if cleanup["score"] < 90 else "INFO")
        self.log(f"Confidence note   : {cleanup['detail']}", "INFO")
        if browser_compare:
            self.log(
                f"Browser compare   : {browser_compare['cleared_count']} suspicious browser item(s) cleared, {browser_compare['reappeared_count']} reappeared",
                "INFO" if not browser_compare["reappeared_count"] else "WARN",
            )
        self.log(f"Account risk      : {exposure['score']}%  -  {exposure['label']}", "CRITICAL" if exposure["score"] >= 70 else "WARN")
        self.log(f"Account note      : {exposure['detail']}", "INFO")

    def run_remediation(self):
        self._recovery_session = None
        self._recovery_manifest_path = ""
        self._recovery_warning_emitted = False
        self._begin_recovery_session()
        self._try_create_restore_point("cleanup")
        self._capture_pre_cleanup_snapshot()

        file_cleanup_categories = self._active_file_remediation_categories()
        self.log("── EXECUTING REMEDIATION ──────────────────────────────", "SECTION")

        self._run_remediation_bucket(PROCESS_REMEDIATION_CATEGORIES)

        time.sleep(0.8)

        self._run_remediation_bucket(file_cleanup_categories)

        for threat in sorted(self.threats):
            if threat.category in MANUAL_REVIEW_CATEGORIES and not threat.remediated:
                self.log(f"Review manually before deleting user file: {threat.path or threat.description}", "WARN")

        self._run_remediation_bucket({"Malicious Scheduled Task", "Registry Persistence"})

        self.log(
            f"── REMEDIATION DONE  |  {self.killed} process(es) killed  "
            f"{self.removed} file(s)/entry(ies) removed ──",
            "SECTION"
        )

        self._log_recovery_snapshot_summary()
        return {
            "killed": self.killed,
            "removed": self.removed,
        }

    def run_protection_repair(self):
        self._recovery_session = None
        self._recovery_manifest_path = ""
        self._recovery_warning_emitted = False
        self._begin_recovery_session()
        self._try_create_restore_point("repair")
        starting_removed = self.removed

        self.log("── REPAIRING PROTECTION DEFAULTS ─────────────────────", "SECTION")
        ordered_categories = (
            "Defender Exclusion",
            "Defender Policy Review",
            "Defender Protection Review",
            "Proxy Configuration Review",
            "WinHTTP Proxy Review",
            "Firewall Rule Review",
        )
        for category in ordered_categories:
            self._run_remediation_bucket({category})

        self.log(
            f"── PROTECTION REPAIR DONE  |  {self.removed - starting_removed} setting(s)/rule(s) repaired ──",
            "SECTION",
        )
        self._log_recovery_snapshot_summary()
        return {
            "removed": self.removed - starting_removed,
        }

    def generate_report(self) -> str:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        crit = sum(1 for t in self.threats if t.severity == "CRITICAL")
        high = sum(1 for t in self.threats if t.severity == "HIGH")
        recovery = self.get_latest_recovery_summary()
        summary = self.last_summary or self.summarize_threats()
        cleanup = self.cleanup_assessment or self.assess_cleanup_state()
        exposure = self.assess_account_exposure()
        breakdown = self.finding_breakdown()
        persistence_compare = self.post_cleanup_persistence_summary or self.compare_post_cleanup_persistence()
        browser_compare = self.post_cleanup_browser_summary or self.compare_post_cleanup_browser_state()
        recovery_plan = self.build_account_recovery_plan(exposure).splitlines()
        latest_manifest = self._load_latest_recovery_manifest() or {}
        quarantine = self._quarantine_summary(self._recovery_session or latest_manifest)
        restore_point = recovery.get("restore_point") or {}

        grouped = {}
        for threat in self.threats:
            group_name = self._report_group_name(threat.category)
            grouped.setdefault(group_name, []).append(threat)

        lines = [
            "=" * 64,
            "RENKILL THREAT REPORT",
            "=" * 64,
            f"Generated : {now}",
            f"Machine   : {os.environ.get('COMPUTERNAME', 'Unknown')}",
            f"User      : {os.environ.get('USERNAME', 'Unknown')}",
            f"Tool ver  : {VERSION}",
            "",
            f"Threats found   : {len(self.threats)}  ({crit} CRITICAL, {high} HIGH)",
            f"Confirmed items : {breakdown['confirmed']}",
            f"Review-first    : {breakdown['review']}",
            f"Other findings  : {breakdown['other']}",
            f"Processes killed: {self.killed}",
            f"Files removed   : {self.removed}",
            f"Recovery undo   : {'Available' if recovery['available'] else 'Not available'}",
            "",
            f"Summary verdict : {summary['label']}",
            f"Assessment      : {summary['detail']}",
            f"Local confidence: {cleanup['score']}% - {cleanup['label']}",
            f"Confidence note : {cleanup['detail']}",
            f"Account risk    : {exposure['score']}% - {exposure['label']}",
            f"Account note    : {exposure['detail']}",
        ]

        if persistence_compare:
            lines += [
                f"Startup snapshot: {persistence_compare['before_count']} before cleanup, {persistence_compare['current_count']} on this scan",
                f"Snapshot change : {persistence_compare['cleared_count']} cleared, {persistence_compare['reappeared_count']} reappeared",
            ]
        if browser_compare:
            lines += [
                f"Browser snapshot: {browser_compare['before_count']} suspicious item(s) before cleanup, {browser_compare['current_count']} on this scan",
                f"Browser change  : {browser_compare['cleared_count']} cleared, {browser_compare['reappeared_count']} reappeared",
            ]

        if recovery["available"]:
            lines.append(
                f"Recovery items  : {recovery['reversible_count']} reversible change(s), "
                f"{recovery['note_count']} non-reversible note(s)"
            )
        if restore_point:
            status = str(restore_point.get("status") or "")
            if status == "created":
                lines.append("Restore point   : Created before cleanup")
            elif status == "recently_created":
                lines.append("Restore point   : Windows already had a recent restore point")
            elif status == "unavailable":
                detail = str(restore_point.get("detail") or "")
                lines.append("Restore point   : Not available" + (f" ({detail})" if detail else ""))
        if quarantine["items"]:
            lines += [
                "",
                "Quarantine:",
                f"Quarantine items: {quarantine['items']} isolated",
                f"Quarantine files: {quarantine['files']}",
                f"Quarantine dirs : {quarantine['dirs']}",
                f"Neutralized     : {quarantine['neutralized']} inert payload copy/copies",
            ]

        lines += ["", "Exposure notes:"]
        if self.exposure_notes:
            for description, path_text in self.exposure_notes:
                lines.append(f"- {description}" + (f" | {path_text}" if path_text else ""))
        else:
            lines.append("- No high-confidence account exposure paths were flagged.")

        lines += ["", "=" * 64, "FINDINGS BY SURFACE", "=" * 64]
        group_order = (
            "Startup / Persistence",
            "Process / Memory / Network",
            "Files / Staging",
            "System Posture / Policy",
            "Other Findings",
        )
        item_index = 1
        for group_name in group_order:
            items = grouped.get(group_name) or []
            if not items:
                continue
            lines += ["", group_name]
            for threat in items:
                lines += [
                    f"[{item_index:03d}] [{threat.severity:<8}] {threat.category}",
                    f"       {threat.description}",
                    f"       Path      : {threat.path}",
                    f"       Detected  : {threat.timestamp}",
                    f"       Remediated: {'Yes' if threat.remediated else 'No - MANUAL ACTION REQUIRED'}",
                ]
                item_index += 1

        lines += [
            "",
            "=" * 64,
            "RECOVERY CENTER",
            "=" * 64,
        ]
        lines.extend(recovery_plan)

        lines += [
            "",
            "=" * 64,
            "POST-INFECTION CHECKLIST (do from a CLEAN device)",
            "=" * 64,
            " 1. Change ALL saved browser passwords",
            " 2. Revoke all active sessions (Google, banking, Discord, Steam)",
            " 3. Move crypto assets to a fresh wallet / new seed phrase",
            " 4. Review Google devices and sign out anything unfamiliar",
            " 5. Turn off Chrome sync and clear synced data before turning sync back on",
            " 6. Review Discord Authorized Apps and submit a hacked-account ticket if needed",
            " 7. Run Microsoft Defender Full Scan, then Microsoft Defender Offline",
            " 8. Re-enable MFA on critical accounts",
            " 9. Run RenKill again after reboot to confirm clean",
            "10. Reinstall Windows if CRITICAL threats persist",
            "",
            "=" * 64,
            "IOC REFERENCE",
            "=" * 64,
            " Loader   : RenEngine (Trojan.Python.Agent.nb)",
            " Stage 2  : HijackLoader (Trojan.Win32.Penguish)",
            " Payload  : ACR Stealer | Lumma | Rhadamanthys | Vidar",
            " C2 IP    : 78.40.193.126",
            " Distrib  : dodi-repacks[.]site -> MediaFire ZIP",
        ]
        return sanitize_for_display("\\n".join(lines))


# GUI

BG      = "#0b0b0b"
BG2     = "#111111"
BG3     = "#181818"
BG4     = "#1e1e1e"
FG      = "#dcdcdc"
FG2     = "#777777"
FG3     = "#444444"
RED     = "#E24B4A"
AMBER   = "#EF9F27"
YELLOW  = "#E6C458"
GREEN   = "#5EC269"
BLUE    = "#378ADD"
MONO    = "Consolas"

SEV_COLORS = {
    "CRITICAL": RED,
    "HIGH":     AMBER,
    "MEDIUM":   YELLOW,
    "INFO":     FG2,
    "WARN":     AMBER,
    "SUCCESS":  GREEN,
    "SECTION":  BLUE,
    "DEFAULT":  FG,
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"RenKill  v{VERSION}")
        self.geometry("940x660")
        self.minsize(740, 480)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._scanner = None
        self._thread = None
        self._paranoid_var = tk.BooleanVar(value=False)
        self._action_hint_var = tk.StringVar(
            value="Scan first to map the infection. ACCOUNT LOCKDOWN is ready any time for a one-click local cookie/session wipe on this PC."
        )
        self._repair_defaults_available = False
        self._revert_available = False
        self._session_reset_available = False
        self._last_remediation_ts = 0.0
        self._update_info = None
        self._update_check_in_progress = False
        self._startup_update_prompted = set()

        self._build()
        self.bind("<Configure>", self._refresh_status_layout)
        self.after(0, self._refresh_status_layout)
        self._check_admin()
        self._startup_msg()
        self._report_update_state()
        self.after(1200, self._check_for_updates_silent)
        summary = self._update_revert_button()
        if summary["available"]:
            self._log(
                f"Recovery snapshot available: {summary['reversible_count']} reversible change(s) ready to restore.",
                "INFO",
            )

    def _build(self):
        # Title bar
        bar = tk.Frame(self, bg=BG, padx=18, pady=14)
        bar.pack(fill="x")

        left = tk.Frame(bar, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="RenKill", font=(MONO, 20, "bold"),
                 bg=BG, fg=RED).pack(side="left")
        tk.Label(left, text=f"  v{VERSION}  |  RenEngine / HijackLoader Removal Tool",
                 font=(MONO, 10), bg=BG, fg=FG3).pack(side="left", pady=3)

        right = tk.Frame(bar, bg=BG)
        right.pack(side="right")
        admin_ok = is_admin()
        tk.Label(right,
                 text=" ADMIN " if admin_ok else " LIMITED ",
                 font=(MONO, 9, "bold"),
                 bg=GREEN if admin_ok else AMBER,
                 fg=BG, padx=5, pady=2).pack(side="right")
        # Separator
        tk.Frame(self, bg="#222222", height=1).pack(fill="x")

        # Status bar
        sbar = tk.Frame(self, bg=BG2, padx=18, pady=7)
        sbar.pack(fill="x")
        sbar.grid_columnconfigure(0, weight=1)
        self._status_var = tk.StringVar(value="Ready")
        self._status_lbl = tk.Label(sbar, textvariable=self._status_var,
                                    font=(MONO, 10), bg=BG2, fg=GREEN, anchor="w", justify="left")
        self._status_lbl.grid(row=0, column=0, sticky="ew")
        self._count_var = tk.StringVar(value="—")
        self._count_lbl = tk.Label(sbar, textvariable=self._count_var,
                                   font=(MONO, 10, "bold"), bg=BG2, fg=RED, anchor="e", justify="right")
        self._count_lbl.grid(row=1, column=0, sticky="ew", pady=(3, 0))

        # Buttons
        brow = tk.Frame(self, bg=BG, padx=18, pady=10)
        brow.pack(fill="x")

        primary_actions = tk.Frame(brow, bg=BG)
        primary_actions.pack(fill="x")
        secondary_actions = tk.Frame(brow, bg=BG, pady=6)
        secondary_actions.pack(fill="x")

        self._btn_scan = self._btn(primary_actions, "⟳  SCAN SYSTEM", BLUE, self._do_scan)
        self._btn_kill = self._btn(primary_actions, "✕  KILL & CLEAN", RED, self._do_kill)
        self._btn_revert = self._btn(primary_actions, "REVERT LAST CLEAN", BLUE, self._do_revert)
        self._btn_sessions = self._btn(primary_actions, "⌁  ACCOUNT LOCKDOWN", AMBER, self._do_reset_sessions)
        self._btn_repair = self._btn(secondary_actions, "🛡  REPAIR DEFAULTS", GREEN, self._do_repair_defaults)
        self._btn_report = self._btn(secondary_actions, "↓  EXPORT REPORT", GREEN, self._do_report)
        self._btn_clear = self._btn(secondary_actions, "⌫  CLEAR LOG", FG3, self._do_clear)

        self._btn_update = self._btn(secondary_actions, "CHECK UPDATES", BLUE, self._do_update)
        self._btn_recovery = self._btn(secondary_actions, "ACCOUNT RECOVERY", AMBER, self._do_recovery_plan)

        self._paranoid_chk = tk.Checkbutton(
            secondary_actions,
            text="PARANOID MODE",
            variable=self._paranoid_var,
            onvalue=True,
            offvalue=False,
            selectcolor=BG3,
            activebackground=BG,
            activeforeground=RED,
            bg=BG,
            fg=RED,
            font=(MONO, 9, "bold"),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self._paranoid_chk.pack(side="right", padx=(12, 0), pady=2)

        self._btn_kill.configure(state="disabled")
        self._btn_revert.configure(state="disabled")
        self._btn_sessions.configure(state="normal")
        self._btn_repair.configure(state="normal")
        self._btn_report.configure(state="disabled")
        self._btn_update.configure(state="normal")

        self._action_hint_lbl = tk.Label(
            self,
            textvariable=self._action_hint_var,
            font=(MONO, 9),
            bg=BG,
            fg=FG3,
            anchor="w",
            justify="left",
            padx=18,
            pady=2,
        )
        self._action_hint_lbl.pack(fill="x")

        # Progress
        self._prog_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self._prog_var,
                 font=(MONO, 9), bg=BG, fg=FG3, anchor="w", padx=18).pack(fill="x")

        # Log
        log_frame = tk.Frame(self, bg=BG, padx=18, pady=6)
        log_frame.pack(fill="both", expand=True)

        self._log_txt = scrolledtext.ScrolledText(
            log_frame, font=(MONO, 10), bg="#080808", fg=FG,
            relief="flat", bd=0, wrap="word",
            insertbackground=FG, selectbackground="#2a2a2a",
            padx=10, pady=8,
        )
        self._log_txt.pack(fill="both", expand=True)

        for tag, color in SEV_COLORS.items():
            bold = tag in ("SECTION", "CRITICAL")
            self._log_txt.tag_configure(
                tag, foreground=color,
                font=(MONO, 10, "bold") if bold else (MONO, 10)
            )
        self._log_txt.configure(state="disabled")

        # Footer
        foot = tk.Frame(self, bg=BG, padx=18, pady=4)
        foot.pack(fill="x")
        tk.Label(foot,
                 text="Fuck viruses",
                 font=(MONO, 9, "bold"), bg=BG, fg=FG2).pack(side="left")
        tk.Label(foot,
                 text="made with \u2665 - Cloud",
                 font=(MONO, 9, "bold"), bg=BG, fg=FG2).pack(side="right")

    @staticmethod
    def _btn(parent, text, color, cmd):
        b = tk.Button(parent, text=text, font=(MONO, 10, "bold"),
                      bg=BG4, fg=color, activebackground=color, activeforeground=BG,
                      relief="flat", padx=14, pady=6, cursor="hand2",
                      bd=0, command=cmd)
        b.pack(side="left", padx=(0, 8))
        return b

    @staticmethod
    def _is_frozen_release():
        return bool(getattr(sys, "frozen", False))

    @staticmethod
    def _app_install_dir():
        anchor = sys.executable if getattr(sys, "frozen", False) else __file__
        return os.path.dirname(os.path.abspath(anchor))

    @classmethod
    def _update_state_path(cls):
        return os.path.join(cls._app_install_dir(), UPDATE_STATE_FILE)

    def _set_update_button(self, text, color=BLUE, state="normal"):
        def _apply():
            if hasattr(self, "_btn_update"):
                self._btn_update.configure(text=text, fg=color, activebackground=color, state=state)
        self.after(0, _apply)

    def _read_update_state(self):
        path = self._update_state_path()
        if not os.path.isfile(path):
            return {}
        state = {}
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    state[key.strip().lower()] = value.strip()
        except Exception:
            return {}
        return state

    def _clear_update_state(self):
        path = self._update_state_path()
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass

    def _report_update_state(self):
        state = self._read_update_state()
        if not state:
            return

        status = str(state.get("status") or "").strip().lower()
        expected_version = str(state.get("version") or "").strip()
        detail = str(state.get("detail") or "").strip()
        expected_tuple = ScanEngine._version_tuple(expected_version)
        current_tuple = ScanEngine._version_tuple(VERSION)
        version_mismatch = bool(expected_tuple and current_tuple and current_tuple < expected_tuple)

        if status == "applied" and not version_mismatch:
            message = f"Updater verified RenKill {expected_version or VERSION} successfully."
            self._log(message, "SUCCESS")
            self._set_status(message, GREEN)
        else:
            failure_detail = detail or "the installed files did not match the expected release"
            message = (
                f"Updater warning    : expected RenKill {expected_version or 'newer release'}, "
                f"but this copy is still v{VERSION}. {failure_detail}"
            )
            self._log(message, "WARN")
            self._set_status("Last update attempt did not finish cleanly.", AMBER)
            self._set_action_hint(
                "Updater could not confirm the new version. If this keeps happening, redownload the latest GitHub release package manually.",
                AMBER,
            )
            messagebox.showwarning(
                "Update Verification Warning",
                sanitize_for_display(
                    f"RenKill expected to update to {expected_version or 'a newer release'}, but this copy is still v{VERSION}.\n\n"
                    f"Detail: {failure_detail}\n\n"
                    "If the updater keeps looping, download the latest release package manually."
                ),
            )

        self._clear_update_state()

    def _fetch_latest_release_info(self):
        request = urllib.request.Request(
            UPDATE_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"{TOOL_NAME}/{VERSION}",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8", "ignore"))

        if not isinstance(payload, dict):
            raise RuntimeError("GitHub release response was not a JSON object.")
        if payload.get("draft"):
            raise RuntimeError("Latest GitHub release is still marked as a draft.")

        tag_name = str(payload.get("tag_name") or "").strip()
        assets = payload.get("assets") or []
        asset = None
        for candidate in assets:
            name = str(candidate.get("name") or "")
            if name.lower().endswith(UPDATE_ASSET_SUFFIX):
                asset = candidate
                break
        if not asset:
            raise RuntimeError("Latest release does not include a Windows package asset.")

        return {
            "tag_name": tag_name,
            "version": tag_name.lstrip("v"),
            "html_url": str(payload.get("html_url") or UPDATE_RELEASES_URL),
            "published_at": str(payload.get("published_at") or ""),
            "asset_name": str(asset.get("name") or ""),
            "download_url": str(asset.get("browser_download_url") or ""),
        }

    def _has_newer_release(self, release_info):
        remote_version = ScanEngine._version_tuple(release_info.get("version"))
        current_version = ScanEngine._version_tuple(VERSION)
        return bool(remote_version and current_version and remote_version > current_version)

    def _check_for_updates(self, *, silent):
        if self._update_check_in_progress:
            return

        self._update_check_in_progress = True
        if not silent:
            self._set_update_button("CHECKING…", AMBER, "disabled")
            self._set_status("Checking GitHub releases for updates…", AMBER)

        def _run():
            release_info = None
            error = None
            try:
                release_info = self._fetch_latest_release_info()
            except Exception as exc:
                error = exc

            def _done():
                self._update_check_in_progress = False
                if error:
                    self._set_update_button("CHECK UPDATES", BLUE, "normal")
                    if not silent:
                        self._set_status("Update check failed.", RED)
                        messagebox.showerror(
                            "Update Check Failed",
                            sanitize_for_display(
                                f"RenKill could not check GitHub releases right now.\n\nError: {error}"
                            ),
                        )
                    return

                if release_info and self._has_newer_release(release_info):
                    self._update_info = release_info
                    self._set_update_button(f"UPDATE TO {release_info['version']}", GREEN, "normal")
                    self._log(
                        f"Update ready       : GitHub release {release_info['tag_name']} is available.",
                        "INFO",
                    )
                    if silent:
                        self._set_action_hint(
                            f"Update available: {release_info['tag_name']} is live on GitHub releases. CHECK UPDATES can pull it down and restart RenKill safely.",
                            GREEN,
                        )
                        self._prompt_startup_update(release_info)
                    else:
                        self._set_status(
                            f"Update available: {release_info['tag_name']} is ready to install.",
                            GREEN,
                        )
                        if messagebox.askyesno(
                            "Update Available",
                            sanitize_for_display(
                                f"RenKill {release_info['tag_name']} is available.\n\n"
                                "Download and apply the update now?"
                            ),
                        ):
                            self._start_update_download(release_info)
                    return

                self._update_info = None
                self._set_update_button("CHECK UPDATES", BLUE, "normal")
                if not silent:
                    self._set_status("RenKill is already on the latest release.", GREEN)
                    messagebox.showinfo(
                        "RenKill Up To Date",
                        f"RenKill v{VERSION} already matches the latest GitHub release.",
                    )

            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _check_for_updates_silent(self):
        self._check_for_updates(silent=True)

    def _prompt_startup_update(self, release_info):
        if not release_info:
            return
        tag_name = str(release_info.get("tag_name") or "").strip()
        if not tag_name or tag_name in self._startup_update_prompted:
            return
        self._startup_update_prompted.add(tag_name)
        if not self._is_frozen_release():
            return
        if messagebox.askyesno(
            "Update Available",
            sanitize_for_display(
                f"RenKill {tag_name} is available.\n\n"
                "Download and apply the update now?"
            ),
        ):
            self._start_update_download(release_info)

    def _download_release_package(self, release_info, progress_cb=None):
        temp_root = tempfile.mkdtemp(prefix="renkill-update-")
        zip_path = os.path.join(temp_root, release_info["asset_name"])
        extract_dir = os.path.join(temp_root, "payload")
        request = urllib.request.Request(
            release_info["download_url"],
            headers={"User-Agent": f"{TOOL_NAME}/{VERSION}"},
        )

        with urllib.request.urlopen(request, timeout=45) as response, open(zip_path, "wb") as handle:
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    if total > 0:
                        percent = max(1, min(100, int(downloaded * 100 / total)))
                        progress_cb(f"Downloading update… {percent}%")
                    else:
                        progress_cb(f"Downloading update… {downloaded // 1024} KB")

        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_dir)

        new_exe = os.path.join(extract_dir, "RenKill.exe")
        if not os.path.isfile(new_exe):
            raise RuntimeError("Downloaded release package did not contain RenKill.exe.")
        return temp_root, extract_dir

    def _write_update_apply_script(self, extract_dir):
        install_dir = self._app_install_dir()
        current_pid = os.getpid()
        temp_root = os.path.dirname(extract_dir)
        expected_version = self._update_info.get("version") if isinstance(self._update_info, dict) else VERSION
        source_exe = os.path.join(extract_dir, "RenKill.exe")
        expected_hash = ""
        try:
            expected_hash = self._sha256_file(source_exe)
        except Exception:
            expected_hash = ""
        if not expected_hash:
            raise RuntimeError("RenKill could not hash the downloaded update package.")
        script_path = os.path.join(tempfile.gettempdir(), f"renkill-apply-update-{current_pid}.cmd")
        script_lines = [
            "@echo off",
            "setlocal EnableExtensions EnableDelayedExpansion",
            f'set "RENKILL_PID={current_pid}"',
            f'set "RENKILL_SRC={extract_dir}"',
            f'set "RENKILL_DST={install_dir}"',
            f'set "RENKILL_ROOT={temp_root}"',
            f'set "RENKILL_EXPECTED_VERSION={expected_version}"',
            f'set "RENKILL_EXPECTED_HASH={expected_hash}"',
            'set "RENKILL_DST_EXE=%RENKILL_DST%\\RenKill.exe"',
            'set "RENKILL_STATE=%RENKILL_DST%\\' + UPDATE_STATE_FILE + '"',
            '> "%RENKILL_STATE%" echo status=starting',
            '>> "%RENKILL_STATE%" echo version=%RENKILL_EXPECTED_VERSION%',
            '>> "%RENKILL_STATE%" echo package_root=%RENKILL_ROOT%',
            ":wait_loop",
            'tasklist /FI "PID eq %RENKILL_PID%" | find "%RENKILL_PID%" >nul',
            "if not errorlevel 1 (",
            "  timeout /t 1 /nobreak >nul",
            "  goto wait_loop",
            ")",
            'robocopy "%RENKILL_SRC%" "%RENKILL_DST%" /E /R:2 /W:1 /NFL /NDL /NJH /NJS /NC /NS >nul',
            'set "RENKILL_RC=!ERRORLEVEL!"',
            "if !RENKILL_RC! GEQ 8 goto copy_failed",
            'if not exist "%RENKILL_DST_EXE%" goto verify_failed',
            'for /f "usebackq delims=" %%H in (`"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -Command "(Get-FileHash -LiteralPath $env:RENKILL_DST_EXE -Algorithm SHA256).Hash.ToLower()"`) do set "RENKILL_DST_HASH=%%H"',
            'if /I not "!RENKILL_DST_HASH!"=="%RENKILL_EXPECTED_HASH%" goto verify_failed',
            '> "%RENKILL_STATE%" echo status=applied',
            '>> "%RENKILL_STATE%" echo version=%RENKILL_EXPECTED_VERSION%',
            '>> "%RENKILL_STATE%" echo detail=verified file copy and hash match',
            'start "" "%RENKILL_DST%\\RenKill.exe"',
            'rmdir /s /q "%RENKILL_ROOT%" >nul 2>nul',
            'del "%~f0" >nul 2>nul',
            "goto :eof",
            ":copy_failed",
            '> "%RENKILL_STATE%" echo status=failed',
            '>> "%RENKILL_STATE%" echo version=%RENKILL_EXPECTED_VERSION%',
            '>> "%RENKILL_STATE%" echo detail=robocopy failed with exit code !RENKILL_RC!',
            '>> "%RENKILL_STATE%" echo package_root=%RENKILL_ROOT%',
            '"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show(\'RenKill could not apply the update automatically. Please download the latest release package manually.\', \'RenKill Update Failed\')" >nul 2>nul',
            'if exist "%RENKILL_DST_EXE%" start "" "%RENKILL_DST_EXE%"',
            'del "%~f0" >nul 2>nul',
            "goto :eof",
            ":verify_failed",
            '> "%RENKILL_STATE%" echo status=failed',
            '>> "%RENKILL_STATE%" echo version=%RENKILL_EXPECTED_VERSION%',
            '>> "%RENKILL_STATE%" echo detail=updated files did not verify against the downloaded package',
            '>> "%RENKILL_STATE%" echo package_root=%RENKILL_ROOT%',
            '"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show(\'RenKill could not verify the updated files. Please download the latest release package manually.\', \'RenKill Update Failed\')" >nul 2>nul',
            'if exist "%RENKILL_DST_EXE%" start "" "%RENKILL_DST_EXE%"',
            'del "%~f0" >nul 2>nul',
        ]
        with open(script_path, "w", encoding="utf-8", newline="\r\n") as handle:
            handle.write("\r\n".join(script_lines) + "\r\n")
        return script_path

    def _launch_update_apply_script(self, script_path):
        creation_flags = 0x08000000
        try:
            creation_flags |= subprocess.DETACHED_PROCESS
        except AttributeError:
            pass
        subprocess.Popen(
            ["cmd.exe", "/c", script_path],
            creationflags=creation_flags,
            close_fds=True,
        )

    def _exit_for_update(self):
        try:
            self.destroy()
        finally:
            os._exit(0)

    def _start_update_download(self, release_info):
        if not release_info:
            return
        if not self._is_frozen_release():
            if messagebox.askyesno(
                "Update Ready",
                sanitize_for_display(
                    "Automatic apply works from the packaged RenKill release build.\n\n"
                    "Open the GitHub releases page instead?"
                ),
            ):
                try:
                    os.startfile(release_info.get("html_url") or UPDATE_RELEASES_URL)
                except Exception:
                    messagebox.showinfo("GitHub Releases", release_info.get("html_url") or UPDATE_RELEASES_URL)
            return

        self._btn_scan.configure(state="disabled")
        self._btn_kill.configure(state="disabled")
        self._btn_repair.configure(state="disabled")
        self._btn_revert.configure(state="disabled")
        self._btn_update.configure(state="disabled")
        self._btn_sessions.configure(state="disabled")
        self._btn_report.configure(state="disabled")
        self._set_status(f"Downloading {release_info['tag_name']}…", AMBER)

        def _run():
            script_path = ""
            error = None
            try:
                _, extract_dir = self._download_release_package(release_info, self._set_progress)
                script_path = self._write_update_apply_script(extract_dir)
            except Exception as exc:
                error = exc

            def _done():
                self._set_progress("")
                if error:
                    self._btn_scan.configure(state="normal")
                    self._btn_kill.configure(state="normal" if self._scanner and self._scanner.threats else "disabled")
                    self._btn_repair.configure(state="normal")
                    self._btn_sessions.configure(state="normal")
                    self._btn_report.configure(state="normal" if self._scanner else "disabled")
                    self._update_revert_button()
                    self._set_update_button("CHECK UPDATES", BLUE, "normal")
                    self._set_status("Update download failed.", RED)
                    messagebox.showerror(
                        "Update Failed",
                        sanitize_for_display(
                            f"RenKill could not download or stage the update.\n\nError: {error}"
                        ),
                    )
                    return

                try:
                    self._launch_update_apply_script(script_path)
                except Exception as exc:
                    self._btn_scan.configure(state="normal")
                    self._btn_kill.configure(state="normal" if self._scanner and self._scanner.threats else "disabled")
                    self._btn_repair.configure(state="normal")
                    self._btn_sessions.configure(state="normal")
                    self._btn_report.configure(state="normal" if self._scanner else "disabled")
                    self._update_revert_button()
                    self._set_update_button("CHECK UPDATES", BLUE, "normal")
                    self._set_status("Update launch failed.", RED)
                    messagebox.showerror(
                        "Update Failed",
                        sanitize_for_display(
                            f"RenKill staged the update but could not launch the apply step.\n\nError: {exc}"
                        ),
                    )
                    return

                self._set_status(f"Applying {release_info['tag_name']} and restarting…", GREEN)
                self._log(
                    f"Updater ready      : applying {release_info['tag_name']} from GitHub releases and restarting RenKill.",
                    "SUCCESS",
                )
                self.after(350, self._exit_for_update)

            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _do_update(self):
        if self._update_check_in_progress:
            return
        if self._update_info and self._has_newer_release(self._update_info):
            if messagebox.askyesno(
                "Apply Update",
                sanitize_for_display(
                    f"RenKill {self._update_info['tag_name']} is ready.\n\n"
                    "Download and apply it now?"
                ),
            ):
                self._start_update_download(self._update_info)
            return
        self._check_for_updates(silent=False)

    def _restore_update_button_state(self):
        if self._update_info and self._has_newer_release(self._update_info):
            self._set_update_button(f"UPDATE TO {self._update_info['version']}", GREEN, "normal")
            return
        self._set_update_button("CHECK UPDATES", BLUE, "normal")

    @staticmethod
    def _chromium_profile_dirs(root):
        if not os.path.isdir(root):
            return []
        base = os.path.basename(root).lower()
        if base != "user data":
            return [root]
        out = []
        try:
            for entry in os.listdir(root):
                full = os.path.join(root, entry)
                if not os.path.isdir(full):
                    continue
                if entry == "Default" or entry.startswith("Profile ") or entry in {"Guest Profile", "System Profile"}:
                    out.append(full)
        except Exception:
            return []
        return out

    def _delete_path_force(self, path):
        if not os.path.exists(path):
            return False
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=False)
            else:
                os.remove(path)
            return True
        except PermissionError:
            try:
                subprocess.run(["attrib", "-r", "-s", "-h", path],
                               capture_output=True, creationflags=0x08000000)
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=False)
                else:
                    os.remove(path)
                return True
            except Exception:
                return False
        except Exception:
            return False

    def _kill_named_processes(self, names):
        killed = 0
        if not PSUTIL_OK:
            for name in sorted(names):
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/IM", name],
                                   capture_output=True, creationflags=0x08000000)
                except Exception:
                    pass
            return 0

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                if pname in names:
                    proc.terminate()
                    time.sleep(0.2)
                    if proc.is_running():
                        proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception:
                pass
        return killed

    def _iter_session_reset_paths(self):
        profile = os.environ.get("USERPROFILE", "")
        for app in SESSION_RESET_APPS:
            for rel_root in app["roots"]:
                root = os.path.join(profile, rel_root)
                kind = app["kind"]
                if kind == "flat":
                    if not os.path.isdir(root):
                        continue
                    for sub in app["subpaths"]:
                        yield app["label"], os.path.join(root, sub)
                elif kind == "chromium":
                    for profile_dir in self._chromium_profile_dirs(root):
                        for sub in CHROMIUM_SESSION_SUBPATHS:
                            yield app["label"], os.path.join(profile_dir, sub)
                elif kind == "firefox":
                    if not os.path.isdir(root):
                        continue
                    try:
                        for entry in os.listdir(root):
                            profile_dir = os.path.join(root, entry)
                            if not os.path.isdir(profile_dir):
                                continue
                            for fname in FIREFOX_SESSION_FILES:
                                yield app["label"], os.path.join(profile_dir, fname)
                            for sub in FIREFOX_SESSION_DIRS:
                                yield app["label"], os.path.join(profile_dir, sub)
                    except Exception:
                        continue

    def _log(self, msg, level="DEFAULT"):
        def _w():
            self._log_txt.configure(state="normal")
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            tag = level if level in SEV_COLORS else "DEFAULT"
            safe_msg = sanitize_for_display(msg)
            if level == "SECTION":
                self._log_txt.insert("end", f"\n[{ts}]  {safe_msg}\n", tag)
            else:
                self._log_txt.insert("end", f"[{ts}]  {safe_msg}\n", tag)
            self._log_txt.see("end")
            self._log_txt.configure(state="disabled")
        self.after(0, _w)

    def _set_status(self, msg, color=GREEN):
        self.after(0, lambda: (
            self._status_var.set(msg),
            self._status_lbl.configure(fg=color)
        ))

    @staticmethod
    def _diagnostic_log_path():
        candidates = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), TOOL_NAME),
            os.path.join(os.getcwd(), TOOL_NAME),
        ]
        for root in candidates:
            if not root:
                continue
            try:
                os.makedirs(root, exist_ok=True)
                return os.path.join(root, "renkill_diagnostics.log")
            except Exception:
                continue
        return ""

    def _write_diagnostic_log(self, context):
        path = self._diagnostic_log_path()
        if not path:
            return ""
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(f"\n[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {context}\n")
                handle.write(traceback.format_exc())
                handle.write("\n")
            return path
        except Exception:
            return ""

    def _refresh_status_layout(self, _event=None):
        if not hasattr(self, "_status_lbl"):
            return
        wrap = max(320, self.winfo_width() - 72)
        self._status_lbl.configure(wraplength=wrap)
        if hasattr(self, "_action_hint_lbl"):
            self._action_hint_lbl.configure(wraplength=wrap)

    def _set_action_hint(self, msg, color=FG3):
        def _apply():
            self._action_hint_var.set(msg)
            if hasattr(self, "_action_hint_lbl"):
                self._action_hint_lbl.configure(fg=color)
        self.after(0, _apply)

    def _threat_count(self, categories):
        if not self._scanner:
            return 0
        category_set = set(categories)
        return sum(1 for threat in self._scanner.threats if threat.category in category_set)

    def _actionable_threat_count(self, categories):
        if not self._scanner:
            return 0
        category_set = set(categories)
        return sum(
            1
            for threat in self._scanner.threats
            if threat.category in category_set and threat.action and not threat.remediated
        )

    def _update_post_scan_hint(self, threat_count, cleanup, exposure):
        startup_categories = {
            "Active Setup Persistence",
            "AppCert Persistence",
            "Explorer Hijack Review",
            "KnownDLLs Review",
            "Disabled Startup Artifact",
            "Logon Script Persistence",
            "Malicious Scheduled Task",
            "Malicious Shortcut",
            "Policy Persistence",
            "Registry Persistence",
            "RunOnceEx Persistence",
            "SafeBoot Review",
            "Session Manager Review",
            "Shell Persistence Review",
            "Startup-Launched Process",
            "Startup Correlation Review",
            "Winlogon Notify Review",
            "WMI Persistence",
        }
        startup_hits = self._threat_count(startup_categories)
        repair_hits = self._actionable_threat_count(PROTECTION_REPAIR_CATEGORIES)
        breakdown = self._scanner.finding_breakdown() if self._scanner else {"confirmed": 0, "review": 0, "other": 0}
        if startup_hits:
            self._set_action_hint(
                f"Startup watch: {startup_hits} suspicious startup item(s) were found. Use KILL & CLEAN, then reboot and rescan so hidden startup leftovers cannot relaunch the infection.",
                RED if startup_hits >= 2 else AMBER,
            )
            return
        if threat_count > 0:
            if breakdown["confirmed"] and breakdown["review"]:
                self._set_action_hint(
                    f"{breakdown['confirmed']} confirmed malware-style item(s) and {breakdown['review']} review-first finding(s) were surfaced. Clean the confirmed traces, then use ACCOUNT RECOVERY and REPAIR DEFAULTS as needed.",
                    AMBER,
                )
                return
            if repair_hits and (self._session_reset_available or exposure["score"] >= 50):
                self._set_action_hint(
                    "Threats were found. Use KILL & CLEAN for malware traces, REPAIR DEFAULTS for security/proxy drift, then ACCOUNT LOCKDOWN to wipe reusable local sessions on this PC.",
                    AMBER,
                )
            elif repair_hits:
                self._set_action_hint(
                    "Threats were found. Use KILL & CLEAN for malware traces, then REPAIR DEFAULTS to restore safe protection and proxy settings.",
                    AMBER,
                )
            elif self._session_reset_available or exposure["score"] >= 50:
                self._set_action_hint(
                    "Threats were found. Use KILL & CLEAN for confirmed traces, then use ACCOUNT LOCKDOWN to wipe local browser/Discord sessions on this PC.",
                    AMBER,
                )
            else:
                self._set_action_hint(
                    "Threats were found. Use KILL & CLEAN for confirmed traces. REVERT LAST CLEAN stays available for reversible changes.",
                    AMBER,
                )
            return
        if exposure["score"] >= 50:
            self._set_action_hint(
                f"This scan looks locally clean, but account risk is still {exposure['score']}%. ACCOUNT LOCKDOWN can wipe local sessions here; password/session recovery still belongs on a clean device.",
                AMBER,
            )
            return
        if cleanup["score"] < 100:
            self._set_action_hint(
                "No active threats were found, but a reboot and one more rescan will raise confidence that local persistence is fully gone.",
                FG3,
            )
            return
        self._set_action_hint(
            "Scan came back clean. ACCOUNT LOCKDOWN still stays ready if you want a one-click local browser/Discord sign-out on this PC.",
            FG3,
        )

    def _set_progress(self, msg):
        self.after(0, lambda: self._prog_var.set(sanitize_for_display(msg)))

    @staticmethod
    def _boot_time():
        if not PSUTIL_OK:
            return 0.0
        try:
            return float(psutil.boot_time())
        except Exception:
            return 0.0

    def _check_admin(self):
        if is_admin():
            self._set_status("Ready — running as Administrator")
        else:
            self._set_status(
                "WARNING: No admin rights — some scan vectors limited. Restart as Admin for full coverage.",
                AMBER
            )

    def _startup_msg(self):
        self._log(f"{TOOL_NAME} v{VERSION}", "SECTION")
        self._log(f"Scan roots queued : {len(SCAN_ROOTS)}", "INFO")
        self._log(f"psutil            : {'OK' if PSUTIL_OK else 'MISSING — pip install psutil'}", "INFO" if PSUTIL_OK else "WARN")
        self._log(f"winreg            : {'OK' if WINREG_OK else 'MISSING'}", "INFO" if WINREG_OK else "WARN")
        self._log(f"Admin             : {'YES — full scan' if is_admin() else 'NO — limited scan'}", "INFO" if is_admin() else "WARN")
        self._log("Scan mode         : Standard", "INFO")
        self._log("Containment tool   : ACCOUNT LOCKDOWN is ready for a one-click local cookie/session wipe.", "WARN")
        self._log("Press SCAN SYSTEM to begin.", "DEFAULT")

    def _load_recovery_summary(self):
        scanner = ScanEngine(lambda *_: None, lambda *_: None)
        return scanner.get_latest_recovery_summary()

    def _update_revert_button(self):
        summary = self._load_recovery_summary()
        self._revert_available = bool(summary["available"])
        if hasattr(self, "_btn_revert"):
            self._btn_revert.configure(state="normal" if self._revert_available else "disabled")
        return summary

    @staticmethod
    def _recovery_snapshot_blurb(summary):
        if not summary["available"]:
            return ""
        return (
            "\nRecovery snapshot:\n"
            f"  - {summary['reversible_count']} reversible change(s) recorded\n"
            "  - Use REVERT LAST CLEAN if a safe rollback is needed\n"
        )

    @staticmethod
    def _kill_confirmation_text(process_count, file_count, breakdown):
        return (
            "RenKill will:\n\n"
            f"  Kill {process_count} process(es) / connection(s)\n"
            f"  Delete {file_count} file(s) / task(s) / registry entry(ies)\n"
            f"  Confirmed malware-style findings: {breakdown['confirmed']}\n"
            f"  Review-first findings left for judgment: {breakdown['review']}\n\n"
            "RenKill will quarantine or back up reversible file, task, registry, firewall, "
            "and proxy changes when possible.\n"
            "Review-first findings are not blindly deleted unless they also map to a confirmed cleanup action.\n"
            "Process kills, service removals, WMI removals, and session resets are not fully reversible.\n\n"
            "Continue?"
        )

    def _do_scan(self):
        if self._thread and self._thread.is_alive():
            return

        self._btn_scan.configure(state="disabled")
        self._btn_kill.configure(state="disabled")
        self._btn_revert.configure(state="disabled")
        self._btn_sessions.configure(state="disabled")
        self._btn_report.configure(state="disabled")
        self._btn_update.configure(state="disabled")
        self._count_var.set("Scanning…")
        scan_mode = "PARANOID" if self._paranoid_var.get() else "STANDARD"
        self._set_status(f"Scanning system ({scan_mode})…", BLUE)
        self._log(f"Scan mode         : {scan_mode}", "WARN" if self._paranoid_var.get() else "INFO")

        self._scanner = ScanEngine(self._log, self._set_progress, paranoid=self._paranoid_var.get())
        self._scanner.post_cleanup_scan = self._last_remediation_ts > 0
        self._scanner.rebooted_after_cleanup = self._scanner.post_cleanup_scan and self._boot_time() > self._last_remediation_ts

        def _run():
            try:
                self._scanner.run_full_scan()
            except Exception as exc:
                self._log(f"Scan error: {exc}", "CRITICAL")

                def _fail():
                    self._set_progress("")
                    self._btn_scan.configure(state="normal")
                    self._update_revert_button()
                    self._btn_report.configure(state="normal")
                    self._restore_update_button_state()
                    self._btn_kill.configure(state="disabled")
                    self._btn_repair.configure(state="normal")
                    self._btn_sessions.configure(state="normal")
                    self._count_var.set("Scan error")
                    self._set_status("Scan failed — see log for the exact error.", RED)
                self.after(0, _fail)
                return

            n = len(self._scanner.threats)
            summary = self._scanner.last_summary or self._scanner.summarize_threats()
            cleanup = self._scanner.cleanup_assessment or self._scanner.assess_cleanup_state()
            exposure = self._scanner.assess_account_exposure()
            persistence_compare = self._scanner.post_cleanup_persistence_summary or self._scanner.compare_post_cleanup_persistence()
            browser_compare = self._scanner.post_cleanup_browser_summary or self._scanner.compare_post_cleanup_browser_state()

            def _done():
                self._set_progress("")
                self._btn_scan.configure(state="normal")
                self._btn_report.configure(state="normal")
                self._restore_update_button_state()
                self._update_revert_button()
                self._session_reset_available = bool(self._scanner.exposure_notes)
                self._repair_defaults_available = self._actionable_threat_count(PROTECTION_REPAIR_CATEGORIES) > 0
                self._btn_sessions.configure(state="normal")
                self._btn_repair.configure(state="normal")
                startup_hits = self._threat_count({
                    "Active Setup Persistence",
                    "AppCert Persistence",
                    "Explorer Hijack Review",
                    "KnownDLLs Review",
                    "Disabled Startup Artifact",
                    "Logon Script Persistence",
                    "Malicious Scheduled Task",
                    "Malicious Shortcut",
                    "Policy Persistence",
                    "Registry Persistence",
                    "RunOnceEx Persistence",
                    "SafeBoot Review",
                    "Session Manager Review",
                    "Shell Persistence Review",
                    "Startup-Launched Process",
                    "Startup Correlation Review",
                    "Winlogon Notify Review",
                    "WMI Persistence",
                })
                if n > 0:
                    self._btn_kill.configure(state="normal")
                    self._count_var.set(f"{n} threats  |  local {cleanup['score']}%  |  account risk {exposure['score']}%")
                    self._set_status(
                        f"Scan complete. {summary['label']}. Local {cleanup['score']}%. Account risk {exposure['score']}%. Use KILL & CLEAN to remediate.",
                        summary["color"]
                    )
                    if startup_hits:
                        self._log(
                            f"Startup watch      : {startup_hits} suspicious startup/persistence item(s) were found. Clear these so the infection cannot relaunch itself.",
                            "CRITICAL" if startup_hits >= 2 else "WARN",
                        )
                    if persistence_compare and persistence_compare["reappeared_count"]:
                        self._log(
                            f"Post-clean drift   : {persistence_compare['reappeared_count']} startup target(s) came back after cleanup.",
                            "CRITICAL" if persistence_compare["suspicious_reappeared_count"] else "WARN",
                        )
                    if browser_compare and browser_compare["reappeared_count"]:
                        self._log(
                            f"Browser aftermath  : {browser_compare['reappeared_count']} suspicious browser-state item(s) came back after cleanup.",
                            "WARN",
                        )
                    if self._session_reset_available:
                        self._log("ACCOUNT LOCKDOWN is available for a one-click local browser/Discord session wipe.", "WARN")
                    if self._repair_defaults_available:
                        self._log("REPAIR DEFAULTS is available for Defender, proxy, and actionable firewall drift.", "INFO")
                    else:
                        self._log("REPAIR DEFAULTS found nothing actionable in this scan. It stays available for scans that surface real Defender/proxy/firewall drift.", "INFO")
                elif self._scanner.post_cleanup_scan and not self._scanner.rebooted_after_cleanup:
                    self._count_var.set(f"Clean  |  local {cleanup['score']}%  |  account risk {exposure['score']}%")
                    self._set_status(
                        f"No threats detected, but reboot and scan once more. Local {cleanup['score']}%. Account risk {exposure['score']}%.",
                        AMBER
                    )
                elif self._scanner.post_cleanup_scan:
                    self._count_var.set(f"Clean  |  local {cleanup['score']}%  |  account risk {exposure['score']}%")
                    self._set_status(
                        f"Post-clean rescan passed. No threats detected. Local {cleanup['score']}%. Account risk {exposure['score']}%.",
                        GREEN
                    )
                    if persistence_compare:
                        self._log(
                            f"Snapshot compare   : {persistence_compare['cleared_count']} startup target(s) stayed gone, {persistence_compare['reappeared_count']} came back after cleanup.",
                            "INFO" if not persistence_compare["reappeared_count"] else "WARN",
                        )
                    if browser_compare:
                        self._log(
                            f"Browser compare    : {browser_compare['cleared_count']} suspicious browser item(s) stayed gone, {browser_compare['reappeared_count']} came back after cleanup.",
                            "INFO" if not browser_compare["reappeared_count"] else "WARN",
                        )
                else:
                    self._count_var.set(f"Clean  |  local {cleanup['score']}%  |  account risk {exposure['score']}%")
                    self._set_status(f"Scan complete. No threats detected. Local {cleanup['score']}%. Account risk {exposure['score']}%.", GREEN)
                self._update_post_scan_hint(n, cleanup, exposure)
            self.after(0, _done)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def _do_kill(self):
        if not self._scanner or not self._scanner.threats:
            return

        live = [t for t in self._scanner.threats if not t.remediated]
        procs = sum(1 for t in live if "Process" in t.category or "Connection" in t.category)
        files = len(live) - procs
        breakdown = self._scanner.finding_breakdown()

        if not messagebox.askyesno(
            "Confirm KILL & CLEAN",
            self._kill_confirmation_text(procs, files, breakdown)
        ):
            return

        self._btn_kill.configure(state="disabled")
        self._btn_repair.configure(state="disabled")
        self._btn_revert.configure(state="disabled")
        self._btn_update.configure(state="disabled")
        self._set_status("Executing remediation…", AMBER)

        self._btn_scan.configure(state="disabled")

        def _run():
            try:
                self._scanner.run_remediation()
            except Exception as exc:
                diag_path = self._write_diagnostic_log("KILL & CLEAN crash")

                def _fail():
                    self._btn_scan.configure(state="normal")
                    self._btn_kill.configure(state="normal" if self._scanner and self._scanner.threats else "disabled")
                    self._restore_update_button_state()
                    self._update_revert_button()
                    self._set_status("Cleanup failed - see log for details.", RED)
                    self._log(f"Cleanup error: {exc}", "CRITICAL")
                    if diag_path:
                        self._log(f"Diagnostic log written to: {diag_path}", "WARN")
                    messagebox.showerror(
                        "RenKill - Cleanup Failed",
                        sanitize_for_display(
                            "KILL & CLEAN hit an internal error and stopped safely.\n\n"
                            f"Error: {exc}\n"
                            + (f"Diagnostic log: {diag_path}\n\n" if diag_path else "\n")
                            + "Please send the last log lines and this diagnostic path to Cloud."
                        ),
                    )

                self.after(0, _fail)
                return
            def _done():
                k = self._scanner.killed
                r = self._scanner.removed
                self._last_remediation_ts = time.time()
                recovery = self._update_revert_button()
                quarantine = self._scanner._quarantine_summary()
                exposure_blurb = ""
                if self._scanner.exposure_notes:
                    exposure_blurb = (
                        "\nExposure warning:\n"
                        "  - Browser and/or Discord data may have been exposed\n"
                        "  - Revoke sessions from a clean device immediately\n"
                    )
                recovery_blurb = self._recovery_snapshot_blurb(recovery)
                exposure = self._scanner.assess_account_exposure()
                self._set_status(
                    f"Cleanup finished - {k} process(es) killed, {r} item(s) removed. Reboot, rescan, and treat account risk as {exposure['score']}%.",
                    GREEN
                )
                messagebox.showinfo(
                    "RenKill - Remediation Complete",
                    f"Processes killed     : {k}\n"
                    f"Files/entries removed: {r}\n\n"
                    f"Quarantined items    : {quarantine['items']} total\n"
                    f"Inert payload copies : {quarantine['neutralized']}\n\n"
                    f"Local cleanup state  : reboot and rescan needed\n"
                    f"Account risk         : {exposure['score']}% - {exposure['label']}\n\n"
                    f"NEXT STEP ON THIS PC:\n"
                    f"  - Reboot Windows\n"
                    f"  - Run SCAN SYSTEM again for post-clean confidence\n\n"
                    f"FROM A CLEAN DEVICE:\n"
                    f"  - Change ALL browser-saved passwords\n"
                    f"  - Revoke all active sessions\n"
                    f"  - Move crypto to fresh wallet addresses\n\n"
                    f"{recovery_blurb}"
                    f"{exposure_blurb}"
                    f"Run SCAN SYSTEM again to verify clean."
                )
                self._btn_scan.configure(state="normal")
                self._restore_update_button_state()
            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _do_repair_defaults(self):
        if not self._scanner:
            return

        repair_count = self._actionable_threat_count(PROTECTION_REPAIR_CATEGORIES)
        if repair_count <= 0:
            messagebox.showinfo(
                "Repair Defaults",
                "No actionable protection or proxy drift is queued right now."
            )
            return

        if not messagebox.askyesno(
            "Confirm Repair Defaults",
            "RenKill will repair the safe, reversible protection drift it already detected.\n\n"
            "This includes items like:\n"
            "  - suspicious Defender exclusions\n"
            "  - Defender policy overrides\n"
            "  - disabled Defender protection flags\n"
            "  - suspicious proxy settings\n"
            "  - actionable suspicious firewall rules\n\n"
            "RenKill will record recovery data for reversible changes when possible.\n\n"
            "Continue?"
        ):
            return

        self._btn_scan.configure(state="disabled")
        self._btn_kill.configure(state="disabled")
        self._btn_repair.configure(state="disabled")
        self._btn_revert.configure(state="disabled")
        self._btn_update.configure(state="disabled")
        self._set_status("Repairing protection defaults…", AMBER)

        def _run():
            try:
                result = self._scanner.run_protection_repair()
            except Exception as exc:
                diag_path = self._write_diagnostic_log("REPAIR DEFAULTS crash")

                def _fail():
                    self._btn_scan.configure(state="normal")
                    self._btn_kill.configure(state="normal" if self._scanner and self._scanner.threats else "disabled")
                    self._btn_repair.configure(state="normal" if self._repair_defaults_available else "disabled")
                    self._restore_update_button_state()
                    self._update_revert_button()
                    self._set_status("Repair Defaults failed — see log for the exact error.", RED)
                    if diag_path:
                        self._log(f"Diagnostic log written to: {diag_path}", "WARN")
                    self._log(f"Repair Defaults crash: {exc}", "CRITICAL")
                self.after(0, _fail)
                return

            def _done():
                repaired = int(result.get("removed", 0))
                self._btn_scan.configure(state="normal")
                self._btn_kill.configure(state="normal" if self._scanner and self._scanner.threats else "disabled")
                self._restore_update_button_state()
                summary = self._update_revert_button()
                self._set_status(
                    f"Repair Defaults finished — {repaired} protection setting(s)/rule(s) repaired. Run SCAN SYSTEM again to confirm.",
                    GREEN if repaired else AMBER,
                )
                self._repair_defaults_available = False
                self._btn_repair.configure(state="disabled")
                self._set_action_hint(
                    "Repair Defaults finished. Run SCAN SYSTEM again to verify the posture drift is gone and only real malware findings remain.",
                    FG3,
                )
                if summary["available"]:
                    self._log(
                        f"Recovery snapshot available: {summary['reversible_count']} reversible change(s) ready to restore.",
                        "INFO",
                    )
                messagebox.showinfo(
                    "RenKill — Repair Defaults Complete",
                    f"Protection items repaired: {repaired}\n\n"
                    "Next step:\n"
                    "  - Run SCAN SYSTEM again\n"
                    "  - Confirm the Defender/proxy/firewall noise is gone\n"
                    "  - Use REVERT LAST CLEAN if you need to undo a reversible settings change"
                )
            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _do_revert(self):
        summary = self._update_revert_button()
        if not summary["available"]:
            messagebox.showinfo(
                "Revert Last Clean",
                "No reversible cleanup snapshot is available yet."
            )
            return

        if not messagebox.askyesno(
            "Confirm Revert",
            f"RenKill will restore up to {summary['reversible_count']} quarantined or backed-up change(s) from the last cleanup.\n\n"
            "This can restore files, tasks, registry values, firewall rules, Defender exclusions, and proxy settings.\n"
            "It will not restart killed processes or fully undo service/WMI removals.\n\n"
            "Continue?"
        ):
            return

        self._btn_revert.configure(state="disabled")
        self._btn_scan.configure(state="disabled")
        self._btn_kill.configure(state="disabled")
        self._btn_update.configure(state="disabled")
        self._set_status("Reverting last cleanup snapshot...", AMBER)

        def _run():
            scanner = ScanEngine(self._log, self._set_progress, paranoid=self._paranoid_var.get())
            result = scanner.revert_last_remediation()

            def _done():
                self._set_progress("")
                self._btn_scan.configure(state="normal")
                self._btn_kill.configure(state="disabled")
                self._restore_update_button_state()
                self._update_revert_button()
                restored = result["restored"]
                failed = result["failed"]
                conflicts = result["conflicts"]
                note_count = len(result["notes"])
                self._set_status(
                    f"Revert complete - {restored} change(s) restored, {failed} failed.",
                    GREEN if failed == 0 else AMBER,
                )
                messagebox.showinfo(
                    "RenKill - Revert Complete",
                    f"Restored changes    : {restored}\n"
                    f"Failed restores     : {failed}\n"
                    f"Conflict restores   : {conflicts}\n"
                    f"Non-reversible notes: {note_count}\n\n"
                    "Run SCAN SYSTEM again to confirm the current state."
                )

            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _do_reset_sessions(self):
        if not messagebox.askyesno(
            "Confirm Account Lockdown",
            "RenKill will close Discord and supported browsers, then wipe local cookies, session tokens, and web-session storage.\n\n"
            "Use this when you want to cut off any currently reusable local sessions on the infected PC.\n"
            "This will sign the user out locally and may remove app/site session state.\n"
            "This does NOT replace password changes or remote session revocation from a clean device.\n\n"
            "Continue?"
        ):
            return

        self._btn_sessions.configure(state="disabled")
        self._btn_update.configure(state="disabled")
        self._set_status("Running account lockdown…", AMBER)

        def _run():
            killed = 0
            removed = 0
            touched_apps = set()
            process_names = set()
            for app in SESSION_RESET_APPS:
                process_names.update(name.lower() for name in app["processes"])

            killed += self._kill_named_processes(process_names)
            time.sleep(0.6)

            for label, path in self._iter_session_reset_paths():
                if self._delete_path_force(path):
                    removed += 1
                    touched_apps.add(label)
                    self._log(f"Cleared local session data: {path}", "SUCCESS")

            def _done():
                app_list = ", ".join(sorted(touched_apps)) if touched_apps else "none found"
                self._set_status(
                    f"Account lockdown complete — {removed} storage item(s) cleared.",
                    GREEN if removed else AMBER
                )
                messagebox.showinfo(
                    "RenKill — Account Lockdown Complete",
                    f"Processes closed : {killed}\n"
                    f"Storage items wiped: {removed}\n"
                    f"Apps affected    : {app_list}\n\n"
                    f"This clears LOCAL cookies, sessions, and token-style storage on this PC.\n"
                    f"You still need to do the following from a CLEAN device:\n"
                    f"  • Change passwords\n"
                    f"  • Revoke remote sessions\n"
                    f"  • Review Discord Authorized Apps\n"
                    f"  • Move crypto to fresh wallet addresses\n"
                )
                self._btn_sessions.configure(state="normal")
                self._restore_update_button_state()
            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _do_recovery_plan(self):
        scanner = self._scanner or ScanEngine(lambda *_: None, lambda *_: None)
        exposure = scanner.assess_account_exposure() if self._scanner else {
            "score": 0,
            "label": "General recovery guidance",
            "detail": "Run a scan first for a tailored recovery plan. This is the generic clean-device checklist.",
            "color": FG3,
        }
        plan_text = scanner.build_account_recovery_plan(exposure)
        messagebox.showinfo("RenKill — Account Recovery", plan_text)

    def _do_report(self):
        if not self._scanner:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text report", "*.txt"), ("All files", "*.*")],
            initialfile=f"RenKill_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._scanner.generate_report())
                messagebox.showinfo("Saved", sanitize_for_display(f"Report saved to:\n{path}"))
            except Exception as exc:
                messagebox.showerror("Error", sanitize_for_display(f"Could not save: {exc}"))

    def _do_clear(self):
        self._log_txt.configure(state="normal")
        self._log_txt.delete("1.0", "end")
        self._log_txt.configure(state="disabled")


# Entry point

if __name__ == "__main__":
    if sys.platform == "win32":
        elevate_if_needed()
    app = App()
    app.mainloop()

