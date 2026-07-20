import asyncio
from bleak import BleakScanner

async def main():
    print("Scanning for Bluetooth devices... (Turn on your printer)")
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name and any(x in d.name.lower() for x in ["print", "mx", "mf"]):
            print(f"\n Found Printer: {d.name}")
            print(f"Linux MAC Address (Copy this): {d.address}\n")

asyncio.run(main())

# 68:08:09:15:31:1B