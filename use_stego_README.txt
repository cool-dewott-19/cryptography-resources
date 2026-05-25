hey if you're reading this, I made a stenography encode/decoder for you, here's how to use it:

# Hide a message:
python3 stego.py encode example.png example_secret.png "The password is: this is cool"

# Someone with the script can decode it:
python3 stego.py decode example_secret.png

# Windows use "python" instead of "python3"

# [✓] Hidden message:
#     The password is: this is cool
