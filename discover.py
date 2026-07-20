import asyncio
from bleak import BleakClient

PRINTER_MAC = "68:08:09:15:31:1B"

async def main():
    print(f"Connecting to {PRINTER_MAC}...")
    async with BleakClient(PRINTER_MAC) as client:
        print(f"Connected: {client.is_connected}\n")

        for service in client.services:
            print(f"[Service] {service.uuid} - {service.description}")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  [Char] {char.uuid}  properties=({props})  handle={char.handle}")

                if "notify" in char.properties or "indicate" in char.properties:
                    def make_handler(uuid):
                        def handler(sender, data):
                            print(f"    >> NOTIFY from {uuid}: {data.hex()}")
                        return handler

                    await client.start_notify(char.uuid, make_handler(char.uuid))
                    print(f"    (subscribed for notifications)")

        print("\nSubscribed to all notify/indicate characteristics.")
        print("Leave this running, then run print-code.py in another terminal")
        print("and watch here for any bytes the printer sends back.")
        print("Press Ctrl+C to stop.\n")

        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
