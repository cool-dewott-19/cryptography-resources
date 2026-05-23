hey if you're reading this, I made a stenography encode/decoder for you, here's how to use it:

# Hide a message
python3 steno.py encode example.png example_secret.png "The password is: this is cool"

# Someone with the script can extract it
python3 steno.py decode hello_secret.png

# [✓] Hidden message:
#     The password is: this is cool