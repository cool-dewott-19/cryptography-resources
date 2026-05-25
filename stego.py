"""
LSB *kind of* Steganography Project

To use:

  Use the bash commands:

  Encode/decode text:
  
    python3 stego.py encode_text input.png output.png "secret message"
    python3 stego.py decode_text output.png

  Encode/decode an image:
  
    python3 stego.py encode_image carrier.png secret.png output.png [--depth N] [--scale F]
    python3 stego.py decode_image output.png recovered.png

    --depth N  bits per channel to use (1-8, default 1).
               1 = imperceptible, 2 = barely visible, 4 = noticeable.
               The tool will suggest the minimum depth if the carrier is too small.
               
    --scale F  resize the secret image before embedding (e.g. 0.5 = half size).
               Reduces payload so a lower depth can be used.
               Both flags can be combined: --scale 0.5 --depth 2

  For windows, use "python"

Requirements: Pillow, numpy
"""

import sys
import math
import numpy as np
from PIL import Image

END_MARKER = "<<END>>"
IMAGE_MARKER_START = "<<IMG:"   # followed by "WxH:dN>>" then raw pixel bits
IMAGE_MARKER_END   = "<<ENDIMG>>"


def text_to_bits(text: str) -> list:
    """Convert a string to a flat list of bits (MSB first)."""
    bits = []
    for byte in text.encode("utf-8"):
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_text(bits: list) -> str:
    """Convert a flat list of bits back to a UTF-8 string."""
    chars = []
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        chars.append(chr(byte))
    return "".join(chars)


def encode_text(input_path: str, output_path: str, message: str) -> None:
    """
    Hide message inside the image at input_path and save the
    result to output_path (must be a png format).
    """
    img = Image.open(input_path).convert("RGB")
    pixels = np.array(img, dtype=np.uint8)

    payload = message + END_MARKER
    bits = text_to_bits(payload)

    max_bits = pixels.size
    if len(bits) > max_bits:
        raise ValueError(
            f"Message too long: need {len(bits)} bits but image only holds {max_bits}."
        )

    flat = pixels.flatten()
    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & 0xFE) | bit
    pixels = flat.reshape(pixels.shape)

    Image.fromarray(pixels).save(output_path)
    print(f"[✓] Message encoded into '{output_path}'")
    print(f"    Bits used : {len(bits)} / {max_bits}")
    print(f"    Capacity  : {max_bits // 8} bytes  |  Used: {len(payload)} bytes")


def decode_text(image_path: str) -> str:
    """
    Extract and return the hidden message from image_path.
    Raises ValueError if no valid message is found.
    """
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img, dtype=np.uint8)

    flat = pixels.flatten()
    bits = [int(v & 1) for v in flat]

    decoded = []
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        decoded.append(chr(byte))
        tail = "".join(decoded[-len(END_MARKER):])
        if tail == END_MARKER:
            message = "".join(decoded[: -len(END_MARKER)])
            return message

    raise ValueError("No hidden message found (end marker not detected).")

# Helpers for multi-bit-depth image steganography

def _min_depth_needed(payload_bits: int, carrier_channels: int) -> int:
    """Return the smallest depth (1-8) that fits payload_bits into carrier_channels."""
    for d in range(1, 9):
        if payload_bits <= carrier_channels * d:
            return d
    return None   # impossible even at depth 8


def _embed_bits(flat: np.ndarray, payload_bits: list, depth: int) -> None:
    """
    Write payload_bits into the lowest `depth` bits of flat[], in-place.
    Channels are consumed one at a time; each channel holds `depth` bits.
    """
    mask = 0xFF ^ ((1 << depth) - 1)
    for ch_idx in range(math.ceil(len(payload_bits) / depth)):
        chunk = payload_bits[ch_idx * depth : (ch_idx + 1) * depth]
        while len(chunk) < depth:
            chunk.append(0)
        value = 0
        for b in chunk:
            value = (value << 1) | b
        flat[ch_idx] = (int(flat[ch_idx]) & mask) | value


def _extract_bits(flat: np.ndarray, n_bits: int, depth: int) -> list:
    """
    Read n_bits from the lowest `depth` bits of flat[].
    Returns exactly n_bits bits.
    """
    bits = []
    for ch_idx in range(math.ceil(n_bits / depth)):
        val = int(flat[ch_idx])
        for shift in range(depth - 1, -1, -1):
            bits.append((val >> shift) & 1)
    return bits[:n_bits]


def encode_image(carrier_path: str, secret_path: str, output_path: str,
                 depth: int = 1, scale: float = 1.0) -> None:
    """
    Hide the image at secret_path inside the carrier image at carrier_path
    and save the result to output_path (must be PNG format).

    depth (1-8): how many of the carrier's LSBs per channel are overwritten.
      1 = imperceptible quality loss, requires carrier >= 8x secret pixel count.
      2 = barely visible,            requires carrier >= 4x secret pixel count.
      4 = visible banding,           requires carrier >= 2x secret pixel count.
    scale (0.0-1.0): resize the secret image before embedding.
      Smaller values reduce payload size, allowing a lower depth or smaller carrier.
    The depth and original dimensions are stored in the header so decode_image
    needs no extra flags.
    """
    if not 1 <= depth <= 8:
        raise ValueError("depth must be between 1 and 8.")

    carrier = Image.open(carrier_path).convert("RGB")
    carrier_pixels = np.array(carrier, dtype=np.uint8)
    carrier_channels = carrier_pixels.size

    secret = Image.open(secret_path).convert("RGB")

    if not 0.0 < scale <= 1.0:
        raise ValueError("scale must be between 0.0 (exclusive) and 1.0 (inclusive).")
    if scale < 1.0:
        new_w = max(1, round(secret.width  * scale))
        new_h = max(1, round(secret.height * scale))
        secret = secret.resize((new_w, new_h), Image.LANCZOS)
        print(f"    Scaling   : {round(secret.width/scale)}x{round(secret.height/scale)}"
              f" → {secret.width}x{secret.height} px  (scale={scale})")

    header = f"{IMAGE_MARKER_START}{secret.width}x{secret.height}:d{depth}>>"
    header_bits = text_to_bits(header)
    trailer_bits = text_to_bits(IMAGE_MARKER_END)

    secret_bytes = np.array(secret, dtype=np.uint8).flatten()
    pixel_bits = []
    for byte_val in secret_bytes:
        for i in range(7, -1, -1):
            pixel_bits.append((int(byte_val) >> i) & 1)

    body_bits = pixel_bits + trailer_bits

    header_channels_needed = len(header_bits)
    body_channels_needed   = math.ceil(len(body_bits) / depth)
    total_channels_needed  = header_channels_needed + body_channels_needed

    if total_channels_needed > carrier_channels:
        min_d = _min_depth_needed(len(body_bits), carrier_channels - header_channels_needed)
        if min_d is None:
            raise ValueError(
                f"Secret image is too large to fit even at depth 8. "
                f"Use a larger carrier or a smaller secret image."
            )
        raise ValueError(
            f"Secret image does not fit at depth {depth}: need "
            f"{total_channels_needed} channels but carrier only has {carrier_channels}.\n"
            f"    Minimum depth needed : {min_d}  (try: --depth {min_d})\n"
            f"    Or shrink the secret : try --scale 0.5 to quarter the payload"
        )

    flat = carrier_pixels.flatten().copy()
    _embed_bits(flat[0:header_channels_needed], header_bits, 1)
    _embed_bits(flat[header_channels_needed:header_channels_needed + body_channels_needed],
                body_bits, depth)
    carrier_pixels = flat.reshape(carrier_pixels.shape)

    Image.fromarray(carrier_pixels).save(output_path)

    total_payload = len(header_bits) + len(body_bits)
    capacity_pct = body_channels_needed / (carrier_channels - header_channels_needed) * 100
    quality_label = {1: "imperceptible", 2: "barely visible",
                     3: "slight noise",  4: "visible banding"}.get(depth, "heavy distortion")
    print(f"[✓] Secret image encoded into '{output_path}'")
    print(f"    Depth     : {depth} bit(s)/channel  ({quality_label})")
    print(f"    Bits used : {total_payload} / {carrier_channels * depth}  ({capacity_pct:.1f}%)")
    print(f"    Secret    : {secret.width}x{secret.height} px  (recovered at this size)")


def decode_image(carrier_path: str, output_path: str) -> None:
    """
    Extract a hidden image from carrier_path and save it to output_path.
    The depth used during encoding is read from the header automatically.
    Raises ValueError if no valid hidden image is found.
    """
    carrier = Image.open(carrier_path).convert("RGB")
    flat = np.array(carrier, dtype=np.uint8).flatten()

    header_lsbs = [int(v & 1) for v in flat]

    header_prefix = IMAGE_MARKER_START   # "<<IMG:"
    header_end    = ">>"
    decoded_chars: list = []
    width = height = depth = None
    header_bits_used = 0

    for i in range(0, len(header_lsbs) - 7, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | header_lsbs[i + j]
        decoded_chars.append(chr(byte))
        joined = "".join(decoded_chars)

        if len(joined) <= len(header_prefix):
            if not header_prefix.startswith(joined):
                raise ValueError("No hidden image found (header marker missing).")
            continue

        if joined.startswith(header_prefix) and joined.endswith(header_end):
            inner = joined[len(header_prefix):-2]
            try:
                dims_part, depth_part = inner.split(":d")
                w_str, h_str = dims_part.split("x")
                width, height, depth = int(w_str), int(h_str), int(depth_part)
            except (ValueError, AttributeError):
                raise ValueError(f"Malformed image header: '{joined}'")
            header_bits_used = (i // 8 + 1) * 8
            break
    else:
        raise ValueError("No hidden image found (header not terminated).")

    if not 1 <= depth <= 8:
        raise ValueError(f"Invalid depth {depth} read from header.")

    n_pixel_bits = width * height * 3 * 8
    trailer_bits_needed = len(IMAGE_MARKER_END) * 8

    header_channels = header_bits_used

    pixel_and_trailer_bits = n_pixel_bits + trailer_bits_needed
    channels_needed = math.ceil(pixel_and_trailer_bits / depth)

    if header_channels + channels_needed > len(flat):
        raise ValueError("Carrier image is too small to contain the claimed secret image.")

    pixel_trailer_raw = _extract_bits(flat[header_channels:], pixel_and_trailer_bits, depth)

    pixel_bits   = pixel_trailer_raw[:n_pixel_bits]
    trailer_bits = pixel_trailer_raw[n_pixel_bits: n_pixel_bits + trailer_bits_needed]

    trailer_text = bits_to_text(trailer_bits)
    if trailer_text != IMAGE_MARKER_END:
        raise ValueError("Trailer marker not found — data may be corrupt.")

    pixel_bytes = []
    for i in range(0, len(pixel_bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | pixel_bits[i + j]
        pixel_bytes.append(byte)

    pixel_array = np.array(pixel_bytes, dtype=np.uint8).reshape((height, width, 3))
    Image.fromarray(pixel_array, mode="RGB").save(output_path)
    print(f"[✓] Hidden image recovered: {width}x{height} px, depth={depth} → '{output_path}'")


# CLI

def usage():
    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage()

    command = sys.argv[1].lower()

    if command == "encode_text":
        if len(sys.argv) != 5:
            print("Usage: python stego.py encode_text <input> <output> <message>")
            sys.exit(1)
        _, _, inp, out, msg = sys.argv
        encode_text(inp, out, msg)

    elif command == "decode_text":
        if len(sys.argv) != 3:
            print("Usage: python stego.py decode_text <image>")
            sys.exit(1)
        _, _, img_path = sys.argv
        try:
            secret = decode_text(img_path)
            print(f"[✓] Hidden message:\n\n    {secret}\n")
        except ValueError as e:
            print(f"[✗] {e}")
            sys.exit(1)

    elif command == "encode_image":
        args = sys.argv[2:]
        depth = 1
        scale = 1.0
        if "--depth" in args:
            di = args.index("--depth")
            try:
                depth = int(args[di + 1])
                args = args[:di] + args[di + 2:]
            except (IndexError, ValueError):
                print("[✗] --depth requires an integer argument (1-8)")
                sys.exit(1)
        if "--scale" in args:
            si = args.index("--scale")
            try:
                scale = float(args[si + 1])
                args = args[:si] + args[si + 2:]
            except (IndexError, ValueError):
                print("[✗] --scale requires a float argument (e.g. 0.5)")
                sys.exit(1)
        if len(args) != 3:
            print("Usage: python stego.py encode_image <carrier> <secret_img> <output> [--depth N] [--scale F]")
            sys.exit(1)
        carrier, secret_img, out = args
        try:
            encode_image(carrier, secret_img, out, depth=depth, scale=scale)
        except ValueError as e:
            print(f"[✗] {e}")
            sys.exit(1)

    elif command == "decode_image":
        if len(sys.argv) != 4:
            print("Usage: python stego.py decode_image <carrier> <output_img>")
            sys.exit(1)
        _, _, carrier, out = sys.argv
        try:
            decode_image(carrier, out)
        except ValueError as e:
            print(f"[✗] {e}")
            sys.exit(1)

    else:
        usage()
