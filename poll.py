import asyncio
import importlib.util
import os
import time
from pathlib import Path

import requests

import epson_printer

# print-code.py has a hyphen in its name, so it can't be `import`ed directly.
_MODULE_PATH = Path(__file__).parent / "print-code.py"
_spec = importlib.util.spec_from_file_location("printer_lib", _MODULE_PATH)
printer_lib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(printer_lib)

# ─── CONFIGURATION ──────────────────────────────────────────────────
VERCEL_URL = "https://project-interaction-installation.vercel.app"
PRINTER_SECRET = os.environ["PRINTER_SECRET"]  # must match PRINTER_SECRET on Vercel
POLL_INTERVAL_SECONDS = 3
# ────────────────────────────────────────────────────────────────────

def poll_for_job():
    resp = requests.get(
        f"{VERCEL_URL}/print/next",
        headers={"x-printer-key": PRINTER_SECRET},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("job")  # None if nothing queued

def print_job(job):
    name = job["name"]
    score = job["score"]
    comment = job["comment"]
    status = job["status"]  # "ACCEPTED" or "FAILED"

    try:
        rows = printer_lib.render_ticket_image(name, score, comment, status)
        asyncio.run(printer_lib.print_rows(rows))
    except Exception as e:
        print(f"Primary (BLE) printer failed ({e}), falling back to Epson M244A...")
        epson_printer.print_epson_ticket(name, score, comment, status)

def main():
    print(f"Polling {VERCEL_URL}/print/next every {POLL_INTERVAL_SECONDS}s...")
    while True:
        try:
            job = poll_for_job()
            if job:
                print(f"Got job: {job}")
                print_job(job)
        except requests.RequestException as e:
            print(f"Poll failed: {e}")
        except Exception as e:
            # A job is popped from the queue the moment it's fetched, so if
            # printing itself fails (printer off, out of range, BLE error),
            # this job is gone for good rather than retried next poll.
            print(f"Print failed for job, it will NOT be retried: {e}")
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
