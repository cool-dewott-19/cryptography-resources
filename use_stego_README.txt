Stego v1.0

***************************************************************************************
For all images, use png format.
Requires: Pillow, numpy
Commands for MacOS; Windows use python or py instead of "python3."
***************************************************************************************

# Hide a text message inside an image

    python3 stego.py encode_text input.png output.png "secret message"

# Decode a hidden text message

    python3 stego.py decode_text output.png

# Encode an image inside an image

    python3 stego.py encode_image carrier.png secret.png output.png --depth N --scale F

    ***********************************************************************************
    --depth N  bits per channel to use (1-8).
               1 = imperceptible, 2 = barely visible, 4 = noticeable.
               
    --scale F  resizes the secret image before embedding (0.5 = half size).
               Reduces payload so a lower depth can be used.
               Both flags can be combined: --scale 0.5 --depth 2

    Omitting both flags is the same as: --scale 1.0 --depth 1.

    If the carrier image is too small, the tool will recommend a different depth. If
    the image is too large to fit even at depth 8, the scale factor will need to be
    used.
    ***********************************************************************************

# Decode a hidden image

    python3 stego.py decode_image output.png recovered.png
