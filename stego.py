"""
LSB Steganography Project

To use:

  Use the bash commands:
  
  encode: python3 stego.py encode input.png output.png "secret message"
  decode: python3 stego.py decode output.png
  
  For windows, use "python"

Requirements: Pillow, numpy
"""

import sys
import numpy as np
from PIL import Image

END_MARKER = "<<END>>"

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

def encode(input_path: str, output_path: str, message: str) -> None:
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

def decode(image_path: str) -> str:
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

def usage():
    print(__doc__)
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage()

    command = sys.argv[1].lower()

    if command == "encode":
        if len(sys.argv) != 5:
            print("Usage: python steganography.py encode <input> <output> <message>")
            sys.exit(1)
        _, _, inp, out, msg = sys.argv
        encode(inp, out, msg)

    elif command == "decode":
        if len(sys.argv) != 3:
            print("Usage: python steganography.py decode <image>")
            sys.exit(1)
        _, _, img_path = sys.argv
        try:
            secret = decode(img_path)
            print(f"[✓] Hidden message:\n\n    {secret}\n")
        except ValueError as e:
            print(f"[✗] {e}")
            sys.exit(1)

    else:
        usage()
