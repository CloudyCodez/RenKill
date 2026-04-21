#!/usr/bin/env python3
"""RenInspect.

Static-only inspector for suspicious Ren'Py / RenEngine-style bundles.
This tool never executes the sample. It only reads files and reports structure.
"""

import argparse
import base64
import hashlib
import os
import re
import sys
import zipfile


TOOL_NAME = "RenInspect"
VERSION = "0.1.0"

RENPY_FOLDER_SET = {"renpy", "data", "lib"}
RENPY_PAYLOAD_NAMES = {"archive.rpa", "script.rpyc"}
RENPY_PAYLOAD_EXTENSIONS = {".rpa", ".rpyc", ".key"}
SUSPICIOUS_DLLS = {
    "iviewers.dll",
    "vsdebugscriptagent170.dll",
    "d3dx9_43.dll",
    "dbghelp.dll",
    "pla.dll",
    "cc32290mt.dll",
}
CAMPAIGN_MARKERS = {
    "instaler",
    "lnstaier",
    "broker_crypt_v4_i386",
    "froodjurain",
    "zoneind",
    "chime",
    "acr",
    "lumma",
    "vidar",
    "rhadamanthys",
    "godot",
    "app_userdata",
    "node_modules.asar",
}
MAX_HASH_SIZE = 128 * 1024 * 1024
MAX_STRING_READ = 2 * 1024 * 1024
MAX_PREVIEW_STRINGS = 12
RANDOM_NAME_EXTENSIONS = {
    ".exe",
    ".dll",
    ".py",
    ".pyc",
    ".pyo",
    ".bat",
    ".cmd",
    ".ps1",
    ".vbs",
    ".js",
    ".lnk",
}
TEXT_LIKE_EXTENSIONS = {
    ".txt",
    ".json",
    ".py",
    ".bat",
    ".cmd",
    ".ps1",
    ".url",
    ".html",
    ".htm",
    ".js",
    ".vbs",
    ".key",
}
URL_PATTERN = re.compile(r"(?:https?|hxxps?)://[^\s\"'<>]+", re.IGNORECASE)
TEMP_STAGE_PATTERN = re.compile(r"\\tmp-\d{4,}-[a-z0-9]{6,}\\", re.IGNORECASE)
BASE64ISH_PATTERN = re.compile(r"[A-Za-z0-9+/=]{32,}")
SUSPICIOUS_COMMAND_MARKERS = (
    "powershell",
    "cmd /c",
    "cmd.exe /c",
    "mshta",
    "wscript",
    "cscript",
    "rundll32",
    "reg add",
    "schtasks",
)
SUSPICIOUS_URL_MARKERS = (
    "mega",
    "mediafire",
    "discord",
    "telegram",
    "mrbeast",
    "crypto",
    "download",
    "cdn",
)
CONTENT_MARKERS = (
    "archive.rpa",
    "script.rpyc",
    "node_modules.asar",
    "app_userdata",
    "broker_crypt_v4_i386",
    "froodjurain",
    "zoneind",
    "chime",
    "instaler",
    "lnstaier",
)


def normalize_relpath(path):
    return path.replace("/", "\\").strip("\\")


def basename_lower(path):
    return os.path.basename(path).lower()


def extension_lower(path):
    return os.path.splitext(path)[1].lower()


def sha256_path(path):
    size = os.path.getsize(path)
    if size > MAX_HASH_SIZE:
        return None, size
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest(), size


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def looks_random_stem(name):
    stem, _ = os.path.splitext(os.path.basename(name))
    stem = stem.strip().lower()
    if len(stem) < 7:
        return False
    if not re.fullmatch(r"[a-z0-9_-]+", stem):
        return False
    letters = sum(1 for char in stem if char.isalpha())
    digits = sum(1 for char in stem if char.isdigit())
    vowels = sum(1 for char in stem if char in "aeiou")
    return letters >= 6 and digits <= 3 and vowels <= max(1, letters // 6)


def extract_strings(data):
    preview = data[:MAX_STRING_READ]
    strings = []
    seen = set()
    for pattern in (rb"[ -~]{6,}", rb"(?:[\x20-\x7e]\x00){6,}"):
        for match in re.finditer(pattern, preview):
            chunk = match.group(0)
            try:
                if b"\x00" in chunk:
                    value = chunk.decode("utf-16le", errors="ignore")
                else:
                    value = chunk.decode("ascii", errors="ignore")
            except Exception:
                continue
            value = " ".join(value.split())
            if not value or value in seen:
                continue
            seen.add(value)
            strings.append(value)
            if len(strings) >= MAX_PREVIEW_STRINGS:
                return strings
    return strings


def is_zip_path(path):
    return os.path.isfile(path) and path.lower().endswith(".zip")


def classify_entry(relpath):
    lower_path = relpath.lower()
    name = basename_lower(relpath)
    ext = extension_lower(relpath)
    hits = []
    if any(marker in lower_path for marker in CAMPAIGN_MARKERS):
        hits.append("campaign-marker")
    if name in RENPY_PAYLOAD_NAMES:
        hits.append("renpy-payload")
    if ext in RENPY_PAYLOAD_EXTENSIONS:
        hits.append("payload-extension")
    if name in SUSPICIOUS_DLLS:
        hits.append("suspicious-dll")
    if ext in RANDOM_NAME_EXTENSIONS and looks_random_stem(name):
        hits.append("random-looking-name")
    if re.search(r"\\tmp-\d{4,}-[a-z0-9]{6,}\\", lower_path):
        hits.append("temp-stage-pattern")
    return hits


def inspect_content_strings(strings):
    hits = []
    details = []
    for value in strings:
        lower_value = value.lower()
        if URL_PATTERN.search(value):
            if any(marker in lower_value for marker in SUSPICIOUS_URL_MARKERS + tuple(CAMPAIGN_MARKERS)):
                hits.append("suspicious-url")
                details.append(value[:180])
        if any(marker in lower_value for marker in SUSPICIOUS_COMMAND_MARKERS):
            hits.append("loader-command")
            details.append(value[:180])
        if TEMP_STAGE_PATTERN.search(lower_value):
            hits.append("temp-stage-reference")
            details.append(value[:180])
        if any(marker in lower_value for marker in CONTENT_MARKERS):
            hits.append("bundle-handoff-reference")
            details.append(value[:180])
        if BASE64ISH_PATTERN.search(value):
            hits.append("encoded-blob")
            details.append(value[:120])
            for match in BASE64ISH_PATTERN.findall(value):
                try:
                    decoded = base64.b64decode(match, validate=True)
                except Exception:
                    continue
                decoded_strings = extract_strings(decoded)
                if not decoded_strings:
                    continue
                decoded_preview = decoded_strings[0][:180]
                details.append(f"decoded: {decoded_preview}")
                lower_decoded = decoded_preview.lower()
                if URL_PATTERN.search(decoded_preview):
                    hits.append("decoded-url")
                if any(marker in lower_decoded for marker in SUSPICIOUS_COMMAND_MARKERS):
                    hits.append("decoded-command")
                if any(marker in lower_decoded for marker in CONTENT_MARKERS):
                    hits.append("decoded-bundle-reference")

    deduped_hits = []
    seen_hits = set()
    for hit in hits:
        if hit not in seen_hits:
            seen_hits.add(hit)
            deduped_hits.append(hit)

    deduped_details = []
    seen_details = set()
    for detail in details:
        if detail not in seen_details:
            seen_details.add(detail)
            deduped_details.append(detail)
            if len(deduped_details) >= 4:
                break
    return deduped_hits, deduped_details


def has_suspicious_launcher_pair(root_files):
    launchers = []
    scripts = []
    for name in root_files:
        ext = extension_lower(name)
        stem = os.path.splitext(name)[0].lower()
        if ext == ".exe":
            launchers.append((stem, name))
        elif ext in {".py", ".pyc", ".pyo"}:
            scripts.append((stem, name))

    for exe_stem, _ in launchers:
        for script_stem, _ in scripts:
            if exe_stem == script_stem:
                return True
    for stem, _ in launchers + scripts:
        if stem in {"instaler", "lnstaier", "launcher", "installer", "setup"}:
            return True
    return False


def summarize_bundle(paths):
    lower_paths = [path.lower() for path in paths]
    top_dirs = {path.split("\\", 1)[0] for path in lower_paths if "\\" in path}
    summary = {
        "renpy_layout": RENPY_FOLDER_SET.issubset(top_dirs),
        "archive_present": any(path.endswith("\\archive.rpa") or path == "archive.rpa" for path in lower_paths),
        "script_present": any(path.endswith("\\script.rpyc") or path == "script.rpyc" for path in lower_paths),
        "key_present": any(path.endswith(".key") for path in lower_paths),
        "godot_asar": any("godot\\app_userdata" in path and path.endswith(".asar") for path in lower_paths),
        "temp_stage": any(re.search(r"\\tmp-\d{4,}-[a-z0-9]{6,}\\", path) for path in lower_paths),
        "sideload_dlls": sorted({basename_lower(path) for path in lower_paths if basename_lower(path) in SUSPICIOUS_DLLS}),
    }
    root_files = [basename_lower(path) for path in lower_paths if "\\" not in path]
    launcher_root = [name for name in root_files if extension_lower(name) in {".exe", ".py", ".pyc", ".pyo"}]
    summary["launcher_pair"] = has_suspicious_launcher_pair(root_files) and (
        summary["renpy_layout"] or summary["archive_present"] or summary["script_present"] or summary["key_present"]
    )
    summary["random_root_launcher"] = any(looks_random_stem(name) for name in launcher_root)
    return summary


def analyze_directory(target):
    paths = []
    entries = []
    findings = []
    for root, _, files in os.walk(target):
        for name in files:
            full_path = os.path.join(root, name)
            relpath = normalize_relpath(os.path.relpath(full_path, target))
            paths.append(relpath)
            hits = classify_entry(relpath)
            sha256_value = None
            size = os.path.getsize(full_path)
            if hits and size <= MAX_HASH_SIZE:
                try:
                    sha256_value, size = sha256_path(full_path)
                except OSError:
                    sha256_value = None
            strings = []
            content_hits = []
            content_details = []
            if extension_lower(relpath) in TEXT_LIKE_EXTENSIONS or hits:
                try:
                    with open(full_path, "rb") as handle:
                        strings = extract_strings(handle.read(MAX_STRING_READ))
                except OSError:
                    strings = []
            if strings:
                content_hits, content_details = inspect_content_strings(strings)
                hits.extend(content_hits)
                hits = list(dict.fromkeys(hits))
            entry = {
                "path": relpath,
                "size": size,
                "hits": hits,
                "sha256": sha256_value,
                "strings": strings,
                "content_details": content_details,
            }
            entries.append(entry)
            if hits:
                findings.append(entry)
    return {
        "mode": "directory",
        "target": target,
        "paths": paths,
        "entries": entries,
        "findings": findings,
        "bundle": summarize_bundle(paths),
    }


def analyze_zip(target):
    paths = []
    entries = []
    findings = []
    with zipfile.ZipFile(target, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            relpath = normalize_relpath(info.filename)
            paths.append(relpath)
            hits = classify_entry(relpath)
            strings = []
            sha256_value = None
            content_hits = []
            content_details = []
            should_read = extension_lower(relpath) in TEXT_LIKE_EXTENSIONS or bool(hits)
            if info.file_size <= MAX_HASH_SIZE and should_read:
                try:
                    with archive.open(info, "r") as handle:
                        data = handle.read(MAX_STRING_READ + 1)
                    if len(data) <= MAX_HASH_SIZE:
                        sha256_value = sha256_bytes(data)
                    strings = extract_strings(data)
                except OSError:
                    sha256_value = None
            if strings:
                content_hits, content_details = inspect_content_strings(strings)
                hits.extend(content_hits)
                hits = list(dict.fromkeys(hits))
            entry = {
                "path": relpath,
                "size": info.file_size,
                "hits": hits,
                "sha256": sha256_value,
                "strings": strings,
                "content_details": content_details,
            }
            entries.append(entry)
            if hits:
                findings.append(entry)
    return {
        "mode": "zip",
        "target": target,
        "paths": paths,
        "entries": entries,
        "findings": findings,
        "bundle": summarize_bundle(paths),
    }


def render_report(result):
    bundle = result["bundle"]
    score = 0
    score += 40 if bundle["renpy_layout"] else 0
    score += 15 if bundle["archive_present"] else 0
    score += 15 if bundle["script_present"] else 0
    score += 10 if bundle["key_present"] else 0
    score += 10 if bundle["launcher_pair"] else 0
    score += 10 if bundle["godot_asar"] else 0
    score += 10 if bundle["temp_stage"] else 0
    score += min(15, len(bundle["sideload_dlls"]) * 5)
    for entry in result["findings"]:
        if "campaign-marker" in entry["hits"]:
            score += 6
        if "loader-command" in entry["hits"]:
            score += 6
        if "suspicious-url" in entry["hits"]:
            score += 5
        if "encoded-blob" in entry["hits"]:
            score += 4
        if "bundle-handoff-reference" in entry["hits"]:
            score += 5
    score = min(100, score)
    if score >= 70:
        assessment = "High-likelihood RenEngine / Ren'Py loader structure"
    elif score >= 40:
        assessment = "Suspicious loader-like structure worth deeper review"
    elif result["findings"]:
        assessment = "Low-confidence suspicious clues present"
    else:
        assessment = "No strong RenEngine-style static clues found"

    lines = [
        f"{TOOL_NAME} v{VERSION}",
        "",
        f"Target: {result['target']}",
        f"Mode: {result['mode']}",
        f"Files inspected: {len(result['entries'])}",
        f"Assessment: {assessment}",
        f"Static score: {score}%",
        "",
        "Bundle summary:",
        f"- Ren'Py folder layout: {'yes' if bundle['renpy_layout'] else 'no'}",
        f"- archive.rpa present: {'yes' if bundle['archive_present'] else 'no'}",
        f"- script.rpyc present: {'yes' if bundle['script_present'] else 'no'}",
        f"- .key decode clue present: {'yes' if bundle['key_present'] else 'no'}",
        f"- launcher pair at root: {'yes' if bundle['launcher_pair'] else 'no'}",
        f"- random root launcher name: {'yes' if bundle['random_root_launcher'] else 'no'}",
        f"- Godot/app_userdata + .asar clue: {'yes' if bundle['godot_asar'] else 'no'}",
        f"- temp-stage path pattern: {'yes' if bundle['temp_stage'] else 'no'}",
        f"- sideload-style DLLs: {', '.join(bundle['sideload_dlls']) if bundle['sideload_dlls'] else 'none'}",
        "",
    ]

    if result["findings"]:
        lines.append("Interesting entries:")
        for entry in sorted(result["findings"], key=lambda item: item["path"].lower()):
            lines.append(f"- {entry['path']}")
            lines.append(f"  size: {entry['size']} bytes")
            lines.append(f"  signals: {', '.join(entry['hits'])}")
            if entry["sha256"]:
                lines.append(f"  sha256: {entry['sha256']}")
            if entry["content_details"]:
                lines.append(f"  content clues: {' | '.join(entry['content_details'])}")
            elif entry["strings"]:
                lines.append(f"  preview strings: {' | '.join(entry['strings'][:4])}")
        lines.append("")
    else:
        lines.extend([
            "Interesting entries:",
            "- none",
            "",
        ])

    lines.extend([
        "Safety notes:",
        "- This report is static-only. Nothing here was executed.",
        "- If this looks malicious, inspect it in a disposable VM or public malware sandbox, not on your normal desktop.",
    ])
    return "\n".join(lines).strip() + "\n"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Static-only inspector for suspicious Ren'Py / RenEngine-style bundles."
    )
    parser.add_argument("target", help="Path to a folder or .zip archive to inspect")
    parser.add_argument("--report-out", help="Optional path to save the report")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    target = os.path.abspath(args.target)
    if os.path.isdir(target):
        result = analyze_directory(target)
    elif is_zip_path(target):
        result = analyze_zip(target)
    else:
        print("Unsupported target. Use a folder or .zip archive.", file=sys.stderr)
        return 1

    report = render_report(result)
    print(report, end="")
    if args.report_out:
        with open(args.report_out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
