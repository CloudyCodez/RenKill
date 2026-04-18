#!/usr/bin/env python3
"""
RenEngine Hunter v1.2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detects, kills, and removes RenEngine Loader /
HijackLoader infostealer artifacts from Windows systems.

Targets:
  - RenEngine Loader (Trojan.Python.Agent.nb)
  - HijackLoader (Trojan.Win32.Penguish)
  - ACR Stealer, Lumma Stealer, Rhadamanthys, Vidar payloads
  - Associated scheduled task persistence
  - Associated registry autorun entries
  - Active C2 network connections

CJMXO STUDIOS — Defensive Security Tool
"""

import os
import sys
import time
import json
import shutil
import hashlib
import threading
import datetime
import subprocess
import ctypes
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog

# ── Windows-only imports (safe-guarded) ─────────────────────────────────────
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


# ═══════════════════════════════════════════════════════════════════════════════
#  IOC DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

VERSION = "1.3.0"

# Exact filenames (lowercase) that are always malicious in this campaign
MALICIOUS_FILENAMES = {
    "instaler.exe",
    "instaler.py",
    "instaler.pyo",
    "instaler.pyc",
    "lnstaier.exe",       # capital-I variant (l vs I confusion)
    "iviewers.dll",       # HijackLoader sideload DLL
    "script.rpyc",        # compiled RenPy payload script  (only flagged in %TEMP%)
    "__init__.py",        # only flagged if found in %TEMP% renpy subdir
    "archive.rpa",        # only flagged in %TEMP% / suspicious paths
}

# RenEngine folder structure signature
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
}

# Known C2 IPs
C2_IPS = {
    "78.40.193.126",
}

# Registry run-key patterns that indicate RenEngine persistence
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
]

# File extensions used in the .key payload decrypt step
PAYLOAD_KEY_EXTENSIONS = {".key"}

# Kaspersky detection names (informational, not used for scanning)
KASPERSKY_NAMES = [
    "Trojan.Python.Agent.nb",
    "HEUR:Trojan.Python.Agent.gen",
    "Trojan.Win32.Penguish",
    "Trojan.Win32.DllHijacker",
    "Trojan-PSW.Win32.Lumma.gen",
    "Trojan-PSW.Win32.ACRstealer.gen",
]

# Registry keys to check for persistence
REGISTRY_RUN_KEYS = [
    (None, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    (None, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
    (None, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
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
    return list(dict.fromkeys(roots))  # deduplicate, preserve order


SCAN_ROOTS = _build_scan_roots()


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN ELEVATION
# ═══════════════════════════════════════════════════════════════════════════════

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate_if_needed():
    """Re-launch with UAC prompt if not already admin."""
    if sys.platform != "win32":
        return
    if not is_admin():
        args = " ".join(f'"{a}"' for a in sys.argv)
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)
        if ret > 32:
            sys.exit(0)
        # If UAC denied, continue with limited privileges


# ═══════════════════════════════════════════════════════════════════════════════
#  THREAT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
#  SCANNER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ScanEngine:
    def __init__(self, log_cb, progress_cb):
        self.log = log_cb
        self.progress = progress_cb
        self.threats: list[Threat] = []
        self.killed = 0
        self.removed = 0
        self._stop = False

    # ── Internal helpers ────────────────────────────────────────────────────

    def _add(self, severity, category, description, path=None, action=None):
        t = Threat(severity, category, description, path, action)
        self.threats.append(t)
        self.log(f"{description}", severity)
        return t

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
    def _contains_marker(path, markers):
        pl = path.lower()
        return any(marker in pl for marker in markers)

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

    # ── Filesystem scan ─────────────────────────────────────────────────────

    def scan_filesystem(self):
        self.log("── FILESYSTEM SCAN ────────────────────────────────────", "SECTION")
        visited_dirs = 0

        for root in SCAN_ROOTS:
            if not root or not os.path.isdir(root):
                continue
            self.log(f"Entering: {root}", "INFO")

            try:
                for dirpath, dirnames, filenames in os.walk(root, topdown=True):
                    if self._stop:
                        return
                    depth = dirpath.replace(root, "").count(os.sep)
                    if depth > 7:
                        dirnames.clear()
                        continue

                    visited_dirs += 1
                    if visited_dirs % 75 == 0:
                        self.progress(f"Walked {visited_dirs} dirs…  current: {dirpath[:60]}")

                    # ── RenEngine bundle detection ──────────────────────────
                    dir_names_lower = {d.lower() for d in dirnames}
                    if RENENGINE_FOLDER_SET.issubset(dir_names_lower):
                        has_instaler = any(f.lower() in MALICIOUS_FILENAMES for f in filenames)
                        sev = "CRITICAL" if has_instaler else "HIGH"
                        dp = dirpath
                        self._add(sev, "RenEngine Bundle",
                                  f"RenEngine folder structure at: {dp}",
                                  dp,
                                  lambda p=dp: self._nuke_directory(p))

                    if self._contains_marker(dirpath, CAMPAIGN_DIR_MARKERS):
                        dp = dirpath
                        self._add("CRITICAL", "Persistence Staging Directory",
                                  f"HijackLoader persistence directory at: {dp}",
                                  dp,
                                  lambda p=dp: self._nuke_directory(p))

                    # ── Individual file checks ──────────────────────────────
                    for fname in filenames:
                        fl = fname.lower()
                        fpath = os.path.join(dirpath, fname)
                        fpath_lower = fpath.lower()

                        # Always-bad filenames (exe/dll/py)
                        if fl in ("instaler.exe", "instaler.py", "instaler.pyo", "instaler.pyc",
                                  "lnstaier.exe", "iviewers.dll"):
                            self._add("CRITICAL", "Malicious File",
                                      f"Known RenEngine file: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

                        # archive.rpa and script.rpyc only suspicious in temp
                        elif fl in ("archive.rpa", "script.rpyc") and self._in_temp(dirpath):
                            self._add("HIGH", "Malicious Archive/Script",
                                      f"RenEngine payload in temp path: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

                        # __init__.py inside a renpy subdir of temp
                        elif fl == "__init__.py" and "renpy" in dirpath.lower() and self._in_temp(dirpath):
                            self._add("HIGH", "Hijacked Module Init",
                                      f"Malicious __init__.py in renpy temp dir: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

                        # .key files in temp (payload decrypt key)
                        elif fl.endswith(".key") and self._in_temp(dirpath):
                            self._add("MEDIUM", "Payload Key File",
                                      f"Encrypted payload .key in temp: {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

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

                        elif fl.endswith(".lnk") and "\\desktop\\" in fpath_lower and self._file_contains_ascii_or_utf16le(
                            fpath,
                            ("broker_crypt_v4_i386", "chime.exe", "zoneind.exe", "froodjurain.wkk")
                        ):
                            self._add("HIGH", "Malicious Shortcut",
                                      f"Desktop shortcut referencing RenEngine persistence: {fpath}",
                                      fpath, lambda p=fpath: self._delete_file(p))

                        # Any EXE in temp with a random-looking name (8+ alphanum, no spaces)
                        elif (fl.endswith(".exe") and self._in_temp(dirpath)
                              and self._looks_random(fname[:-4]) and fl not in ("setup.exe",)):
                            self._add("HIGH", "Dropped Executable",
                                      f"Randomname EXE in temp (likely HijackLoader drop): {fpath}", fpath,
                                      lambda p=fpath: self._delete_file(p))

            except PermissionError:
                pass
            except Exception as exc:
                self.log(f"Walk error at {root}: {exc}", "WARN")

    @staticmethod
    def _looks_random(name: str) -> bool:
        """Heuristic: 6-20 alphanum chars with mixed case = likely random generated."""
        if not name or len(name) < 6 or len(name) > 20:
            return False
        if not name.isalnum():
            return False
        has_upper = any(c.isupper() for c in name)
        has_lower = any(c.islower() for c in name)
        has_digit = any(c.isdigit() for c in name)
        return has_upper and has_lower and has_digit  # e.g. "UIS4tq7P"

    # ── Process scan ────────────────────────────────────────────────────────

    def scan_processes(self):
        self.log("── PROCESS SCAN ───────────────────────────────────────", "SECTION")
        if not PSUTIL_OK:
            self.log("psutil unavailable — install it for full process scanning", "WARN")
            return

        temp_lower = self._temp_paths()

        for proc in psutil.process_iter(["pid", "name", "exe", "ppid"]):
            if self._stop:
                return
            try:
                pname = (proc.info["name"] or "").lower()
                pexe  = (proc.info["exe"]  or "")
                pexe_lower = pexe.lower()
                pid = proc.info["pid"]

                # Running from temp
                if pexe and any(t and t in pexe_lower for t in temp_lower):
                    self._add("CRITICAL", "Process in Temp",
                              f"Process running from temp path: {pname} (PID {pid}) — {pexe}",
                              pexe,
                              lambda p=pid: self._kill_pid(p))

                # Exact malicious names
                elif pname in ("instaler.exe", "lnstaier.exe", "iviewers.dll"):
                    self._add("CRITICAL", "Malicious Process",
                              f"Known RenEngine process: {pname} (PID {pid})",
                              pexe,
                              lambda p=pid: self._kill_pid(p))

                elif pname in ("chime.exe", "zoneind.exe") and (
                    "\\appdata\\" in pexe_lower or "\\programdata\\" in pexe_lower or "\\temp\\" in pexe_lower
                ):
                    self._add("CRITICAL", "Persistence Process",
                              f"Known persistence payload process: {pname} (PID {pid})",
                              pexe,
                              lambda p=pid: self._kill_pid(p))

                # Random-looking exe name running from non-standard path
                elif (pname.endswith(".exe")
                      and self._looks_random(pname[:-4])
                      and pexe and "\\windows\\" not in pexe_lower
                      and "\\program files" not in pexe_lower):
                    self._add("HIGH", "Suspicious Process",
                              f"Random-named process outside standard paths: {pname} (PID {pid}) — {pexe}",
                              pexe,
                              lambda p=pid: self._kill_pid(p))

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    # ── Network scan ────────────────────────────────────────────────────────

    def scan_network(self):
        self.log("── NETWORK CONNECTION SCAN ────────────────────────────", "SECTION")
        if not PSUTIL_OK:
            self.log("psutil unavailable — network scan skipped", "WARN")
            return

        try:
            for conn in psutil.net_connections(kind="inet"):
                if self._stop:
                    return
                if not conn.raddr:
                    continue
                rip = conn.raddr.ip
                if rip in C2_IPS:
                    try:
                        pname = psutil.Process(conn.pid).name() if conn.pid else "unknown"
                    except Exception:
                        pname = "unknown"
                    self._add("CRITICAL", "Active C2 Connection",
                              f"Live connection to known C2 {rip}:{conn.raddr.port} — {pname} (PID {conn.pid})",
                              rip,
                              lambda p=conn.pid: self._kill_pid(p) if p else None)
        except Exception as exc:
            self.log(f"Network scan error: {exc}", "WARN")

    # ── Scheduled task scan ─────────────────────────────────────────────────

    def scan_scheduled_tasks(self):
        self.log("── SCHEDULED TASK SCAN ────────────────────────────────", "SECTION")
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/fo", "CSV", "/v"],
                capture_output=True, text=True, timeout=45, creationflags=0x08000000
            )
            task_name = None
            for line in result.stdout.splitlines():
                stripped = line.strip().strip('"')
                # Detect task name lines
                if stripped.startswith("\\") or (stripped and stripped[0] not in (",", " ")):
                    parts = line.split('","')
                    if parts:
                        task_name = parts[0].strip('"').strip()

                line_lower = line.lower()
                if task_name and any(kw in line_lower for kw in (
                    "\\temp\\", "\\tmp\\", "instaler", "renpy", "iviewers",
                    "lnstaier", "uis4tq7p", "hijackloader", "broker_crypt_v4_i386",
                    "froodjurain", "vsdebugscriptagent170", "zoneind.exe", "chime.exe"
                )):
                    tn = task_name
                    self._add("HIGH", "Malicious Scheduled Task",
                              f"Persistence via scheduled task: {tn}",
                              tn,
                              lambda t=tn: self._delete_task(t))
                    task_name = None  # reset to avoid duplicate hits per task

        except FileNotFoundError:
            self.log("schtasks.exe not found — skipping task scan", "WARN")
        except subprocess.TimeoutExpired:
            self.log("Scheduled task scan timed out", "WARN")
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
                            val_lower = value.lower()
                            if any(pat in val_lower for pat in SUSPICIOUS_REG_PATTERNS):
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

    # ── Remediation helpers ─────────────────────────────────────────────────

    def _kill_pid(self, pid):
        if pid is None:
            return False
        try:
            if PSUTIL_OK:
                p = psutil.Process(pid)
                p.terminate()
                time.sleep(0.4)
                if p.is_running():
                    p.kill()
            else:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                               capture_output=True, creationflags=0x08000000)
            self.killed += 1
            self.log(f"Killed PID {pid}", "SUCCESS")
            return True
        except Exception as exc:
            self.log(f"Could not kill PID {pid}: {exc}", "WARN")
            return False

    def _delete_file(self, path):
        if not os.path.isfile(path):
            return True
        try:
            os.remove(path)
            self.removed += 1
            self.log(f"Deleted: {path}", "SUCCESS")
            return True
        except PermissionError:
            try:
                subprocess.run(["attrib", "-r", "-s", "-h", path],
                               capture_output=True, creationflags=0x08000000)
                os.remove(path)
                self.removed += 1
                self.log(f"Deleted (forced): {path}", "SUCCESS")
                return True
            except Exception as exc:
                self.log(f"Cannot delete {path}: {exc}", "WARN")
        except Exception as exc:
            self.log(f"Cannot delete {path}: {exc}", "WARN")
        return False

    def _nuke_directory(self, path):
        if not os.path.isdir(path):
            return True
        try:
            shutil.rmtree(path, ignore_errors=True)
            self.removed += 1
            self.log(f"Nuked directory: {path}", "SUCCESS")
            return True
        except Exception as exc:
            self.log(f"Cannot remove dir {path}: {exc}", "WARN")
        return False

    def _delete_task(self, task_name):
        try:
            r = subprocess.run(
                ["schtasks", "/delete", "/tn", task_name, "/f"],
                capture_output=True, text=True, creationflags=0x08000000
            )
            if r.returncode == 0:
                self.removed += 1
                self.log(f"Deleted scheduled task: {task_name}", "SUCCESS")
                return True
            self.log(f"Task delete failed: {r.stderr.strip()}", "WARN")
        except Exception as exc:
            self.log(f"Cannot delete task {task_name}: {exc}", "WARN")
        return False

    def _delete_reg_val(self, hive, subkey, name):
        if not WINREG_OK:
            return False
        try:
            key = winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            self.removed += 1
            self.log(f"Deleted registry value: {name}", "SUCCESS")
            return True
        except Exception as exc:
            self.log(f"Cannot delete reg value {name}: {exc}", "WARN")
        return False

    # ── Orchestration ───────────────────────────────────────────────────────

    def run_full_scan(self):
        self.threats.clear()
        self.killed = 0
        self.removed = 0
        self._stop = False
        self.scan_network()
        self.scan_processes()
        self.scan_filesystem()
        self.scan_scheduled_tasks()
        self.scan_registry()
        self.threats.sort()
        crit = sum(1 for t in self.threats if t.severity == "CRITICAL")
        high = sum(1 for t in self.threats if t.severity == "HIGH")
        self.log(f"── SCAN COMPLETE  |  {len(self.threats)} threat(s) — {crit} CRITICAL  {high} HIGH ──", "SECTION")

    def run_remediation(self):
        self.log("── EXECUTING REMEDIATION ──────────────────────────────", "SECTION")
        # 1. Kill network connections & processes first
        for t in sorted(self.threats):
            if t.category in ("Active C2 Connection", "Malicious Process",
                              "Process in Temp", "Suspicious Process"):
                if t.action and not t.remediated:
                    t.action()
                    t.remediated = True

        time.sleep(0.8)  # Let processes die before deleting their files

        # 2. Delete files & directories
        for t in sorted(self.threats):
            if t.category in ("RenEngine Bundle", "Malicious File",
                              "Malicious Archive/Script", "Hijacked Module Init",
                              "Payload Key File", "Dropped Executable"):
                if t.action and not t.remediated:
                    t.action()
                    t.remediated = True

        # 3. Clean persistence (tasks + registry last)
        for t in sorted(self.threats):
            if t.category in ("Malicious Scheduled Task", "Registry Persistence"):
                if t.action and not t.remediated:
                    t.action()
                    t.remediated = True

        self.log(
            f"── REMEDIATION DONE  |  {self.killed} process(es) killed  "
            f"{self.removed} file(s)/entry(ies) removed ──",
            "SECTION"
        )

    def generate_report(self) -> str:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        crit = sum(1 for t in self.threats if t.severity == "CRITICAL")
        high = sum(1 for t in self.threats if t.severity == "HIGH")
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║          RENENGINE HUNTER — THREAT REPORT                    ║",
            "╚══════════════════════════════════════════════════════════════╝",
            f"Generated : {now}",
            f"Machine   : {os.environ.get('COMPUTERNAME', 'Unknown')}",
            f"User      : {os.environ.get('USERNAME', 'Unknown')}",
            f"Tool ver  : {VERSION}",
            "",
            f"Threats found  : {len(self.threats)}  ({crit} CRITICAL, {high} HIGH)",
            f"Processes killed: {self.killed}",
            f"Files removed  : {self.removed}",
            "",
            "━" * 64,
            "THREAT DETAIL",
            "━" * 64,
        ]
        for i, t in enumerate(self.threats, 1):
            lines += [
                f"\n[{i:03d}] [{t.severity:<8}] {t.category}",
                f"       {t.description}",
                f"       Path      : {t.path}",
                f"       Detected  : {t.timestamp}",
                f"       Remediated: {'Yes' if t.remediated else 'No — MANUAL ACTION REQUIRED'}",
            ]
        lines += [
            "",
            "━" * 64,
            "NEXT STEPS (always do these from a CLEAN device)",
            "━" * 64,
            " 1. Change ALL saved browser passwords immediately.",
            " 2. Revoke all active sessions (Google, banking, Discord, etc.).",
            " 3. Move any crypto wallets to fresh addresses generated on a clean machine.",
            " 4. Enable hardware/app-based MFA on all critical accounts.",
            " 5. Run this tool a second time to confirm all threats cleared.",
            " 6. Consider a full Windows reinstall if any CRITICAL threats remain.",
            "",
            "IOC REFERENCE",
            "━" * 64,
            " Loader   : RenEngine (Trojan.Python.Agent.nb)",
            " Stage 2  : HijackLoader (Trojan.Win32.Penguish)",
            " Payload  : ACR Stealer | Lumma | Rhadamanthys | Vidar",
            " C2 IP    : 78.40.193.126",
            " Distrib  : dodi-repacks[.]site → MediaFire ZIP",
        ]
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
#  GUI
# ═══════════════════════════════════════════════════════════════════════════════

# ── Color palette ──────────────────────────────────────────────────────────────
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
PURPLE  = "#9B8DDD"
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
        self.title(f"RenEngine Hunter  v{VERSION}  —  CJMXO STUDIOS")
        self.geometry("920x640")
        self.minsize(740, 480)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._scanner: ScanEngine | None = None
        self._thread: threading.Thread | None = None

        self._build()
        self._check_admin()
        self._startup_msg()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build(self):
        # ─ Title bar ─────────────────────────────────────────────────────
        bar = tk.Frame(self, bg=BG, padx=18, pady=14)
        bar.pack(fill="x")

        left = tk.Frame(bar, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="RENENGINE HUNTER", font=(MONO, 17, "bold"),
                 bg=BG, fg=RED).pack(side="left")
        tk.Label(left, text=f"  v{VERSION}", font=(MONO, 10),
                 bg=BG, fg=FG3).pack(side="left", pady=3)

        right = tk.Frame(bar, bg=BG)
        right.pack(side="right")
        admin_ok = is_admin()
        tk.Label(right,
                 text=" ADMIN " if admin_ok else " LIMITED ",
                 font=(MONO, 9, "bold"),
                 bg=GREEN if admin_ok else AMBER,
                 fg=BG, padx=5, pady=2).pack(side="right")
        tk.Label(right, text="CJMXO STUDIOS  |  Defensive Security  |  ",
                 font=(MONO, 9), bg=BG, fg=FG3).pack(side="right")

        # ─ Separator ─────────────────────────────────────────────────────
        tk.Frame(self, bg="#222222", height=1).pack(fill="x")

        # ─ Status ────────────────────────────────────────────────────────
        sbar = tk.Frame(self, bg=BG2, padx=18, pady=7)
        sbar.pack(fill="x")
        self._status_var = tk.StringVar(value="Ready")
        self._status_lbl = tk.Label(sbar, textvariable=self._status_var,
                                    font=(MONO, 10), bg=BG2, fg=GREEN, anchor="w")
        self._status_lbl.pack(side="left")
        self._count_var = tk.StringVar(value="—")
        tk.Label(sbar, textvariable=self._count_var,
                 font=(MONO, 10, "bold"), bg=BG2, fg=RED).pack(side="right")

        # ─ Button row ────────────────────────────────────────────────────
        brow = tk.Frame(self, bg=BG, padx=18, pady=10)
        brow.pack(fill="x")

        self._btn_scan   = self._btn(brow, "⟳  SCAN SYSTEM",    BLUE,  self._do_scan)
        self._btn_kill   = self._btn(brow, "✕  KILL & CLEAN",   RED,   self._do_kill)
        self._btn_report = self._btn(brow, "↓  EXPORT REPORT",  GREEN, self._do_report)
        self._btn_clear  = self._btn(brow, "⌫  CLEAR LOG",      FG3,   self._do_clear)

        self._btn_kill.configure(state="disabled")
        self._btn_report.configure(state="disabled")

        # ─ Progress label ─────────────────────────────────────────────
        self._prog_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self._prog_var,
                 font=(MONO, 9), bg=BG, fg=FG3, anchor="w", padx=18
                 ).pack(fill="x")

        # ─ Log pane ──────────────────────────────────────────────────
        log_frame = tk.Frame(self, bg=BG, padx=18, pady=6)
        log_frame.pack(fill="both", expand=True)

        self._log_txt = scrolledtext.ScrolledText(
            log_frame,
            font=(MONO, 10), bg="#080808", fg=FG,
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

        # ─ Footer ────────────────────────────────────────────────────
        foot = tk.Frame(self, bg=BG, padx=18, pady=4)
        foot.pack(fill="x")
        tk.Label(foot,
                 text="Detects: RenEngine Loader | HijackLoader | ACR Stealer | Rhadamanthys | Lumma Stealer | Vidar",
                 font=(MONO, 8), bg=BG, fg="#333").pack(side="left")

    @staticmethod
    def _btn(parent, text, color, cmd) -> tk.Button:
        b = tk.Button(parent, text=text, font=(MONO, 10, "bold"),
                      bg=BG4, fg=color, activebackground=color, activeforeground=BG,
                      relief="flat", padx=14, pady=6, cursor="hand2",
                      bd=0, command=cmd)
        b.pack(side="left", padx=(0, 8))
        return b

    # ── Log write ─────────────────────────────────────────────────────────────

    def _log(self, msg, level="DEFAULT"):
        def _w():
            self._log_txt.configure(state="normal")
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            tag = level if level in SEV_COLORS else "DEFAULT"
            prefix = f"[{ts}]  "
            if level == "SECTION":
                self._log_txt.insert("end", f"\n{prefix}{msg}\n", tag)
            else:
                self._log_txt.insert("end", f"{prefix}{msg}\n", tag)
            self._log_txt.see("end")
            self._log_txt.configure(state="disabled")
        self.after(0, _w)

    def _set_status(self, msg, color=GREEN):
        self.after(0, lambda: (
            self._status_var.set(msg),
            self._status_lbl.configure(fg=color)
        ))

    def _set_progress(self, msg):
        self.after(0, lambda: self._prog_var.set(msg))

    # ── Admin check ───────────────────────────────────────────────────────────

    def _check_admin(self):
        if is_admin():
            self._set_status("Ready — running as Administrator")
        else:
            self._set_status(
                "WARNING: No admin rights — process/registry scans may be limited",
                AMBER
            )

    def _startup_msg(self):
        self._log("RenEngine Hunter ready.", "SECTION")
        self._log(f"Scan roots: {len(SCAN_ROOTS)} directories queued", "INFO")
        self._log(f"psutil  : {'available' if PSUTIL_OK else 'NOT FOUND — install psutil for process/network scans'}", 
                  "INFO" if PSUTIL_OK else "WARN")
        self._log(f"winreg  : {'available' if WINREG_OK else 'NOT FOUND — registry scan skipped'}", 
                  "INFO" if WINREG_OK else "WARN")
        self._log(f"admin   : {'yes — full scan capability' if is_admin() else 'no — some scan vectors limited'}", 
                  "INFO" if is_admin() else "WARN")
        self._log("Press SCAN SYSTEM to begin.", "DEFAULT")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _do_scan(self):
        if self._thread and self._thread.is_alive():
            return

        self._btn_scan.configure(state="disabled")
        self._btn_kill.configure(state="disabled")
        self._btn_report.configure(state="disabled")
        self._count_var.set("Scanning…")
        self._set_status("Scanning system…", BLUE)

        self._scanner = ScanEngine(self._log, self._set_progress)

        def _run():
            self._scanner.run_full_scan()
            n = len(self._scanner.threats)
            crit = sum(1 for t in self._scanner.threats if t.severity == "CRITICAL")

            def _done():
                self._set_progress("")
                self._btn_scan.configure(state="normal")
                self._btn_report.configure(state="normal")
                if n > 0:
                    self._btn_kill.configure(state="normal")
                    self._count_var.set(f"{n} threat(s) — {crit} CRITICAL")
                    self._set_status(
                        f"Scan complete — {n} threats found. Run KILL & CLEAN to remediate.",
                        RED
                    )
                else:
                    self._count_var.set("Clean")
                    self._set_status("Scan complete — no threats detected.", GREEN)
            self.after(0, _done)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def _do_kill(self):
        if not self._scanner or not self._scanner.threats:
            return

        live = [t for t in self._scanner.threats if not t.remediated]
        procs = sum(1 for t in live if "Process" in t.category or "Connection" in t.category)
        files = len(live) - procs

        if not messagebox.askyesno(
            "Confirm KILL & CLEAN",
            f"This will:\n\n"
            f"  • Kill {procs} process(es) / network connection(s)\n"
            f"  • Delete {files} file(s) / directory(ies) / task(s) / registry entry(ies)\n\n"
            f"This cannot be undone.\n\nContinue?"
        ):
            return

        self._btn_kill.configure(state="disabled")
        self._set_status("Executing remediation…", AMBER)

        def _run():
            self._scanner.run_remediation()
            def _done():
                k = self._scanner.killed
                r = self._scanner.removed
                self._set_status(
                    f"Done — {k} process(es) killed, {r} item(s) removed. Run scan again to verify.",
                    GREEN
                )
                messagebox.showinfo(
                    "Remediation Complete",
                    f"Processes killed  : {k}\n"
                    f"Files/entries removed: {r}\n\n"
                    f"Next steps (from a CLEAN device):\n"
                    f" • Change ALL browser-saved passwords\n"
                    f" • Revoke all active sessions (Google, banking, Discord)\n"
                    f" • Move any crypto to fresh wallet addresses\n\n"
                    f"Run SCAN SYSTEM again to verify the system is clean."
                )
            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _do_report(self):
        if not self._scanner:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text report", "*.txt"), ("All files", "*.*")],
            initialfile=f"RenEngine_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._scanner.generate_report())
                messagebox.showinfo("Saved", f"Report saved:\n{path}")
            except Exception as exc:
                messagebox.showerror("Error", f"Could not save: {exc}")

    def _do_clear(self):
        self._log_txt.configure(state="normal")
        self._log_txt.delete("1.0", "end")
        self._log_txt.configure(state="disabled")


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Request elevation on Windows before building the UI
    if sys.platform == "win32":
        elevate_if_needed()

    app = App()
    app.mainloop()
