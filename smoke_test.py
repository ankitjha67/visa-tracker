#!/usr/bin/env python3
r"""
Visa Slot Tracker v4.2.1 — Smoke Test
=====================================

Verifies a fresh install end-to-end across 7 stages. Designed to be invoked
from PowerShell, bash, or directly. All quoting/escaping is handled in Python
so PowerShell can't mangle anything.

Run:
    python smoke_test.py                    # cross-platform
    .\smoke_test.ps1                        # Windows wrapper that sets UTF-8

Exit codes:
    0  = all stages passed
    1+ = number of stages that failed
"""
import sys
import os
import json
import importlib
import traceback
import subprocess
from pathlib import Path

# ANSI colors — work on Windows 10+ console and any modern terminal
GREEN = "\033[92m"
RED   = "\033[91m"
CYAN  = "\033[96m"
GRAY  = "\033[90m"
RESET = "\033[0m"

EXPECTED_VERSION = "4.2.1"

def color(text, c):
    return f"{c}{text}{RESET}"

def stage_header(num, total, name):
    print(f"\n[{num}/{total}] {name} ...", end=" ", flush=True)

def ok(detail=None):
    print(color("OK", GREEN))
    if detail:
        print(color(f"      {detail}", GRAY))

def fail(msg):
    print(color(f"FAIL: {msg}", RED))

def skip(reason):
    print(color(f"SKIP ({reason})", GRAY))

def main():
    failed = []
    total = 7

    print()
    print("=" * 72)
    print(f"  Visa Slot Tracker v{EXPECTED_VERSION} — Smoke Test")
    print("=" * 72)

    # ------------------------------------------------------------------
    # Stage 1: Python version + working directory
    # ------------------------------------------------------------------
    stage_header(1, total, "Python + working dir")
    try:
        cwd = Path.cwd()
        if not (cwd / "visa_tracker_v3.py").exists():
            raise FileNotFoundError(
                "visa_tracker_v3.py not in current directory. "
                f"You're in {cwd}. Did you cd into the right folder?"
            )
        py_ver = sys.version.split()[0]
        if sys.version_info < (3, 10):
            raise RuntimeError(f"Python 3.10+ required; you have {py_ver}")
        ok(f"Python {py_ver}, cwd: {cwd}")
    except Exception as e:
        fail(str(e))
        failed.append(("1/7", str(e)))

    # ------------------------------------------------------------------
    # Stage 2: Required modules import
    # ------------------------------------------------------------------
    stage_header(2, total, "Required modules import")
    try:
        required = [
            "requests", "urllib3", "selenium", "aiohttp",
            "websockets", "fake_useragent", "webdriver_manager",
        ]
        missing = []
        for m in required:
            try:
                importlib.import_module(m)
            except ImportError as e:
                missing.append(f"{m} ({e})")
        if missing:
            raise ImportError(
                f"Missing modules: {', '.join(missing)}. "
                f"Run: pip install -r requirements.txt"
            )
        ok(f"{len(required)} modules imported cleanly")
    except Exception as e:
        fail(str(e))
        failed.append(("2/7", str(e)))

    # ------------------------------------------------------------------
    # Stage 3: centers.json parses, version is correct
    # ------------------------------------------------------------------
    stage_header(3, total, f"centers.json parses (v{EXPECTED_VERSION})")
    try:
        with open("centers.json", encoding="utf-8-sig") as f:
            data = json.load(f)
        actual = data.get("version", "<missing>")
        if actual != EXPECTED_VERSION:
            raise ValueError(
                f"Wrong version: expected {EXPECTED_VERSION}, got {actual}"
            )
        ok(
            f"v{actual}, "
            f"{len(data['centers'])} centers, "
            f"{len(data['processors'])} processors"
        )
    except Exception as e:
        fail(str(e))
        failed.append(("3/7", str(e)))

    # ------------------------------------------------------------------
    # Stage 4: visa_tracker_v3.py compiles
    # ------------------------------------------------------------------
    stage_header(4, total, "visa_tracker_v3.py compiles")
    try:
        import py_compile
        py_compile.compile("visa_tracker_v3.py", doraise=True)
        with open("visa_tracker_v3.py", encoding="utf-8") as f:
            line_count = sum(1 for _ in f)
        ok(f"AST clean, {line_count} lines parsed")
    except Exception as e:
        fail(str(e))
        failed.append(("4/7", str(e)))

    # ------------------------------------------------------------------
    # Stage 5: selftest 10/10
    # ------------------------------------------------------------------
    stage_header(5, total, "selftest (10 offline integration checks)")
    try:
        result = subprocess.run(
            [sys.executable, "visa_tracker_v3.py", "selftest"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
        # Count check marks ✓ but exclude the summary "✓ All checks passed" line
        passed_marks = result.stdout.count("✓")
        if "All checks passed" in result.stdout:
            passed_marks -= 1  # don't double-count summary
        failed_marks = result.stdout.count("✗") + result.stdout.count("FAIL")
        if failed_marks > 0 or passed_marks < 10 or result.returncode != 0:
            raise RuntimeError(
                f"selftest passed {passed_marks}/10, failed {failed_marks}, "
                f"exit code {result.returncode}"
            )
        ok(f"{passed_marks}/10 checks passed")
    except subprocess.TimeoutExpired:
        fail("selftest exceeded 60s timeout")
        failed.append(("5/7", "timeout"))
    except Exception as e:
        fail(str(e))
        failed.append(("5/7", str(e)))

    # ------------------------------------------------------------------
    # Stage 6: windows-toasts importable (Windows only)
    # ------------------------------------------------------------------
    stage_header(6, total, "windows-toasts importable")
    if sys.platform != "win32":
        skip("non-Windows platform")
    else:
        try:
            from windows_toasts import Toast, WindowsToaster  # noqa: F401
            ok("windows-toasts library loaded")
        except ImportError as e:
            fail(f"{e}. Run: pip install windows-toasts")
            failed.append(("6/7", "windows-toasts not installed"))

    # ------------------------------------------------------------------
    # Stage 7: Live desktop notification fires
    # ------------------------------------------------------------------
    stage_header(7, total, "Live desktop notification fires")
    try:
        sys.path.insert(0, ".")
        from visa_tracker_v3 import Notifier, SlotInfo

        n = Notifier({"notification_dry_run": False, "desktop_alerts": True})
        s = SlotInfo(
            country="Smoke Test",
            city="Localhost",
            visa_type="Test",
            date="2026-05-05",
            detection_method="page_change",
            booking_url="https://example.com/",
            confidence="high",
        )
        n._desktop_alert([s])
        ok("notification dispatched — check bottom-right corner of screen")
    except Exception as e:
        traceback.print_exc()
        fail(f"{type(e).__name__}: {e}")
        failed.append(("7/7", str(e)))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    if failed:
        print(color(f"  FAILED: {len(failed)} of {total} stage(s) failed", RED))
        for stage_id, msg in failed:
            print(color(f"    {stage_id}: {msg}", RED))
        print("=" * 72)
        print()
        return 1
    else:
        print(color(f"  ALL {total} STAGES PASSED — v{EXPECTED_VERSION} ready for production", GREEN))
        print("=" * 72)
        print()
        print("Next steps:")
        print("  1. (First-time install) Run calibration:")
        print(f"       {sys.executable} visa_tracker_v3.py calibrate --all")
        print()
        print("  2. Start monitoring (live mode with desktop notifications):")
        print(f"       {sys.executable} visa_tracker_v3.py run")
        print()
        print("See USER_GUIDE.md for the plain-English runbook,")
        print("or ADDING_COUNTRIES.md to expand coverage.")
        print()
        return 0


if __name__ == "__main__":
    # On Windows, ensure stdout can render unicode
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            # Enable ANSI color support on cmd.exe / PowerShell
            os.system("")
        except Exception:
            pass
    sys.exit(main())
