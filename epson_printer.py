from escpos.printer import Usb

# Epson's USB vendor ID is fixed across all their printers.
EPSON_USB_VENDOR_ID = 0x04b8

# Product ID varies by exact interface variant - run find_epson_usb.py with the
# M244A plugged in and update this to match.
EPSON_USB_PRODUCT_ID = 0x0202

def print_epson_ticket(name, score, comment, status):
    """Backup printer path: prints the same ticket as the BLE printer, but using
    the Epson M244A's native ESC/POS text formatting instead of a rendered bitmap.
    `comment` is accepted for interface parity with render_ticket_image but is
    intentionally not printed."""
    failed = status.upper() == "FAILED"
    status_text = "YOU FAILED!" if failed else "ACCEPTED!"

    printer = Usb(EPSON_USB_VENDOR_ID, EPSON_USB_PRODUCT_ID)
    try:
        printer.set(align="center", bold=True, double_height=True, double_width=True)
        printer.textln(status_text)

        printer.set(align="left", bold=False, double_height=False, double_width=False)
        printer.textln("")
        printer.set(bold=True)
        printer.textln(f"Name: {name}")
        printer.set(bold=False)
        printer.textln(f"Score: {score}/100")

        if failed:
            printer.textln("")
            printer.textln(
                "You were judged based on inadequate English "
                "knowledge. A victim of language privilege."
            )

        printer.textln("")
        printer.cut()
    finally:
        printer.close()
