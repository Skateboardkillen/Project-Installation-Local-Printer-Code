import os
import subprocess
import sys
import time
from pathlib import Path

URL = "https://project-interaction-installation.vercel.app/"
CHROME_BIN = "google-chrome"
POLL_SCRIPT = Path(__file__).parent / "poll_epson_only.py"

def main():
    if "PRINTER_SECRET" not in os.environ:
        sys.exit("PRINTER_SECRET is not set. Run: export PRINTER_SECRET=<value> first.")

    print(f"Launching Chrome in kiosk mode: {URL}")
    chrome_proc = subprocess.Popen([
        CHROME_BIN,
        "--kiosk",
        "--noerrdialogs",
        "--disable-infobars",
        "--no-first-run",
        URL,
    ])

    print("Starting Epson-only print poller...")
    poll_proc = subprocess.Popen([sys.executable, str(POLL_SCRIPT)])

    procs = {"chrome": chrome_proc, "poller": poll_proc}

    try:
        while True:
            for name, proc in procs.items():
                code = proc.poll()
                if code is not None:
                    print(f"{name} exited (code {code}), shutting down installation...")
                    return
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted, shutting down...")
    finally:
        for proc in procs.values():
            if proc.poll() is None:
                proc.terminate()
        for proc in procs.values():
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

if __name__ == "__main__":
    main()
