import asyncio
import textwrap
from bleak import BleakClient
from PIL import Image, ImageDraw, ImageFont

try:
    from bleak.backends.bluezdbus.client import BleakClientBlueZDBus
except ImportError:
    BleakClientBlueZDBus = None

# ─── CONFIGURATION ──────────────────────────────────────────────────
# This is a rebrand of the common "cat printer" GB01/GB02 BLE thermal printer
# chipset. Protocol ported from https://github.com/rbaron/catprinter, which is
# a verified working implementation for that exact chip (confirmed by matching
# ae30 service / ae01 (TX) / ae02 (RX) characteristic UUIDs against our device).
PRINTER_MAC = "68:08:09:15:31:1B"
TX_CHARACTERISTIC_UUID = "0000ae01-0000-1000-8000-00805f9b34fb"
RX_CHARACTERISTIC_UUID = "0000ae02-0000-1000-8000-00805f9b34fb"
IMAGE_PATH = "small-dog-owners-1.jpg"
PRINT_WIDTH = 384
ENERGY = 0xFFFF  # 0x0000 (light) .. 0xFFFF (darker)

PRINTER_READY_NOTIFICATION = b"\x51\x78\xae\x01\x01\x00\x00\x00\xff"
WAIT_FOR_PRINTER_DONE_TIMEOUT_S = 30
# ────────────────────────────────────────────────────────────────────

def to_unsigned_byte(val):
    return val if val >= 0 else val & 0xff

def bs(lst):
    return bytearray(map(to_unsigned_byte, lst))

CMD_GET_DEV_STATE = bs([81, 120, -93, 0, 1, 0, 0, 0, -1])
CMD_SET_QUALITY_200_DPI = bs([81, 120, -92, 0, 1, 0, 50, -98, -1])
CMD_LATTICE_START = bs([81, 120, -90, 0, 11, 0, -86, 85, 23,
                        56, 68, 95, 95, 95, 68, 56, 44, -95, -1])
CMD_LATTICE_END = bs([81, 120, -90, 0, 11, 0, -86, 85,
                     23, 0, 0, 0, 0, 0, 0, 0, 23, 17, -1])
CMD_SET_PAPER = bs([81, 120, -95, 0, 2, 0, 48, 0, -7, -1])

CHECKSUM_TABLE = bs([
    0, 7, 14, 9, 28, 27, 18, 21, 56, 63, 54, 49, 36, 35, 42, 45, 112, 119, 126, 121,
    108, 107, 98, 101, 72, 79, 70, 65, 84, 83, 90, 93, -32, -25, -18, -23, -4, -5,
    -14, -11, -40, -33, -42, -47, -60, -61, -54, -51, -112, -105, -98, -103, -116,
    -117, -126, -123, -88, -81, -90, -95, -76, -77, -70, -67, -57, -64, -55, -50,
    -37, -36, -43, -46, -1, -8, -15, -10, -29, -28, -19, -22, -73, -80, -71, -66,
    -85, -84, -91, -94, -113, -120, -127, -122, -109, -108, -99, -102, 39, 32, 41,
    46, 59, 60, 53, 50, 31, 24, 17, 22, 3, 4, 13, 10, 87, 80, 89, 94, 75, 76, 69, 66,
    111, 104, 97, 102, 115, 116, 125, 122, -119, -114, -121, -128, -107, -110, -101,
    -100, -79, -74, -65, -72, -83, -86, -93, -92, -7, -2, -9, -16, -27, -30, -21, -20,
    -63, -58, -49, -56, -35, -38, -45, -44, 105, 110, 103, 96, 117, 114, 123, 124, 81,
    86, 95, 88, 77, 74, 67, 68, 25, 30, 23, 16, 5, 2, 11, 12, 33, 38, 47, 40, 61, 58,
    51, 52, 78, 73, 64, 71, 82, 85, 92, 91, 118, 113, 120, 127, 106, 109, 100, 99, 62,
    57, 48, 55, 34, 37, 44, 43, 6, 1, 8, 15, 26, 29, 20, 19, -82, -87, -96, -89, -78,
    -75, -68, -69, -106, -111, -104, -97, -118, -115, -124, -125, -34, -39, -48, -41,
    -62, -59, -52, -53, -26, -31, -24, -17, -6, -3, -12, -13,
])

def chk_sum(b_arr, start, length):
    b2 = 0
    for i in range(start, start + length):
        b2 = CHECKSUM_TABLE[(b2 ^ b_arr[i]) & 0xff]
    return b2

def cmd_feed_paper(how_much):
    b_arr = bs([81, 120, -67, 0, 1, 0, how_much & 0xff, 0, 0xff])
    b_arr[7] = chk_sum(b_arr, 6, 1)
    return bytes(b_arr)

def cmd_set_energy(val):
    b_arr = bs([81, 120, -81, 0, 2, 0, (val >> 8) & 0xff, val & 0xff, 0, 0xff])
    b_arr[8] = chk_sum(b_arr, 6, 2)
    return bytes(b_arr)

def cmd_apply_energy():
    b_arr = bs([81, 120, -66, 0, 1, 0, 1, 0, 0xff])
    b_arr[7] = chk_sum(b_arr, 6, 1)
    return bytes(b_arr)

def encode_run_length_repetition(n, val):
    res = []
    while n > 0x7f:
        res.append(0x7f | (val << 7))
        n -= 0x7f
    if n > 0:
        res.append((val << 7) | n)
    return res

def run_length_encode(img_row):
    res = []
    count = 0
    last_val = -1
    for val in img_row:
        if val == last_val:
            count += 1
        else:
            res.extend(encode_run_length_repetition(count, last_val))
            count = 1
        last_val = val
    if count > 0:
        res.extend(encode_run_length_repetition(count, last_val))
    return res

def byte_encode(img_row):
    def bit_encode(chunk_start, bit_index):
        return 1 << bit_index if img_row[chunk_start + bit_index] else 0

    res = []
    for chunk_start in range(0, len(img_row), 8):
        byte = 0
        for bit_index in range(8):
            byte |= bit_encode(chunk_start, bit_index)
        res.append(byte)
    return res

def cmd_print_row(img_row):
    # Try run-length compression first; fall back to fixed-length byte encoding
    # if the row doesn't compress well (matches the real printer firmware's
    # two supported row formats).
    encoded_img = run_length_encode(img_row)
    if len(encoded_img) > PRINT_WIDTH // 8:
        encoded_img = byte_encode(img_row)
        cmd = -94  # 0xA2: byte-encoded row
    else:
        cmd = -65  # 0xBF: run-length-encoded row

    b_arr = bs([81, 120, cmd, 0, len(encoded_img), 0] + list(encoded_img) + [0, 0xff])
    b_arr[-2] = chk_sum(b_arr, 6, len(encoded_img))
    return bytes(b_arr)

def image_to_rows(img):
    """Converts a 1-bit PIL image into rows of booleans, True meaning 'print black'."""
    width, height = img.size
    rows = []
    for y in range(height):
        rows.append([img.getpixel((x, y)) == 0 for x in range(width)])
    return rows

def load_print_image(image_path):
    """Loads a photo and returns it as rows of booleans, True meaning 'print black'."""
    img = Image.open(image_path).convert("L")

    ratio = PRINT_WIDTH / img.width
    height = int(img.height * ratio)
    img = img.resize((PRINT_WIDTH, height), Image.LANCZOS)

    # Convert("1") dithers (Floyd-Steinberg by default) so gradients still read
    # as detail once reduced to 1-bit.
    img = img.convert("1")

    return image_to_rows(img)

def render_ticket_image(name, score, comment, status):
    """Renders a name/score/comment/status ticket into a 384px-wide 1-bit image."""
    margin = 10
    line_gap = 4
    status_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    body_font = ImageFont.truetype("DejaVuSans.ttf", 20)

    failed = status.upper() == "FAILED"
    status_text = "YOU FAILED!" if failed else "ACCEPTED!"

    # `comment` (AI-generated) is accepted but intentionally not rendered.
    section_gap = [("", body_font), ("", body_font)]

    lines = [
        (status_text, status_font),
        *section_gap,
        (f"Name: {name}", header_font),
        *section_gap,
        (f"SCORE: {score}/100", body_font),
    ]

    if failed:
        privilege_note = textwrap.wrap(
            "You were judged based on inadequate English "
            "knowledge. A victim of language privilege.",
            width=32,
        )
        lines += section_gap
        lines += [(line, body_font) for line in privilege_note]

    # Measure first to size the canvas, then draw for real.
    scratch = Image.new("L", (1, 1))
    scratch_draw = ImageDraw.Draw(scratch)
    height = margin
    line_heights = []
    for text, font in lines:
        bbox = scratch_draw.textbbox((0, 0), text or " ", font=font)
        h = bbox[3] - bbox[1]
        line_heights.append(h)
        height += h + line_gap
    height += margin

    img = Image.new("L", (PRINT_WIDTH, height), color=255)
    draw = ImageDraw.Draw(img)
    y = margin
    for (text, font), h in zip(lines, line_heights):
        draw.text((margin, y), text, fill=0, font=font)
        y += h + line_gap

    return image_to_rows(img.convert("1"))

def generate_payload(rows, energy=ENERGY):
    data = bytearray()
    data += CMD_GET_DEV_STATE
    data += CMD_SET_QUALITY_200_DPI
    data += cmd_set_energy(energy)
    data += cmd_apply_energy()
    data += CMD_LATTICE_START

    for row in rows:
        data += cmd_print_row(row)

    data += cmd_feed_paper(25)
    data += CMD_SET_PAPER
    data += CMD_SET_PAPER
    data += CMD_SET_PAPER
    data += CMD_LATTICE_END
    data += CMD_GET_DEV_STATE

    return bytes(data)

async def print_rows(rows, energy=ENERGY):
    """Connects to the printer, sends the given rows, and waits for it to finish."""
    print(f"Connecting to Ale-hop / Fun Print device ({PRINTER_MAC})...")

    payload = generate_payload(rows, energy=energy)

    async with BleakClient(PRINTER_MAC) as client:
        if not client.is_connected:
            print("Connection failed.")
            return

        # BlueZ reports a stale default MTU of 23 unless we force negotiation;
        # write-without-response can't fragment, so an un-negotiated MTU silently
        # truncates/drops any chunk bigger than (mtu - 3) with no error at all.
        if BleakClientBlueZDBus and isinstance(client, BleakClientBlueZDBus):
            await client._acquire_mtu()
        chunk_size = client.mtu_size - 3
        print(f"Connected! MTU: {client.mtu_size} (chunk size {chunk_size})")

        ready_event = asyncio.Event()

        def on_notify(_sender, data: bytearray):
            print(f"    << NOTIFY: {bytes(data).hex()}")
            if bytes(data) == PRINTER_READY_NOTIFICATION:
                ready_event.set()

        await client.start_notify(RX_CHARACTERISTIC_UUID, on_notify)

        print(f"Sending {len(payload)} bytes in {chunk_size}-byte chunks...")
        for i in range(0, len(payload), chunk_size):
            chunk = payload[i:i + chunk_size]
            await client.write_gatt_char(TX_CHARACTERISTIC_UUID, chunk, response=False)
            await asyncio.sleep(0.02)  # Give the printer CPU time to keep up

        print("Data sent. Waiting for printer to report ready...")
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=WAIT_FOR_PRINTER_DONE_TIMEOUT_S)
            print("Printer finished and is ready.")
        except asyncio.TimeoutError:
            print("Timed out waiting for printer ready notification (job may not have completed).")

async def print_image_file(image_path):
    rows = load_print_image(image_path)
    await print_rows(rows)

if __name__ == "__main__":
    asyncio.run(print_image_file(IMAGE_PATH))
