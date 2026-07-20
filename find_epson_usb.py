import usb.core

EPSON_VENDOR_ID = 0x04b8  # Seiko Epson Corp. - fixed, not model-specific

def main():
    devices = list(usb.core.find(find_all=True, idVendor=EPSON_VENDOR_ID))
    if not devices:
        print("No Epson USB device found. Make sure the M244A is plugged in and powered on.")
        return

    print("Found Epson USB device(s):\n")
    for dev in devices:
        print(f"  idVendor  = 0x{dev.idVendor:04x}")
        print(f"  idProduct = 0x{dev.idProduct:04x}")
        try:
            print(f"  product   = {usb.util.get_string(dev, dev.iProduct)}")
        except Exception:
            pass
        print()
    print("Put the idProduct value above into EPSON_USB_PRODUCT_ID in epson_printer.py")

if __name__ == "__main__":
    main()
