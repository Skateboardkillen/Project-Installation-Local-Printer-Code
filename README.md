# Project-Installation-Local-Printer-Code

## Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate    # on Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the BLE thermal printer (Ale-hop / cat-printer family)

Find its MAC address:

```bash
python3 scan.py
```

Put that address in `PRINTER_MAC` in `print-code.py`.

### 4. Configure the Epson M244A backup printer (USB)

Find its USB vendor/product IDs:

```bash
python3 find_epson_usb.py
```

Update `EPSON_USB_VENDOR_ID` / `EPSON_USB_PRODUCT_ID` in `epson_printer.py` if they differ from the defaults.

On Linux, non-root USB access needs a udev rule (replace the IDs if yours differ from `04b8:0202`):

```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="04b8", ATTR{idProduct}=="0202", MODE="0666"' | sudo tee /etc/udev/rules.d/99-escpos-epson.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then unplug and replug the printer's USB cable.

### 5. Run the print queue poller

```bash
export PRINTER_SECRET=<same value set in Vercel's env vars>
python3 poll.py
```

PRINTER_SECRET=printersecretyeahsuperspecialstring1029


Polls the deployed web app for queued print jobs and prints each one on the BLE printer, falling back to the Epson M244A over USB if the BLE printer fails.
