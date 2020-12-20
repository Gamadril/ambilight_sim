# TPM2 Ambilight Simulator

Cross platform ambilight simulator written in Python. Acts as UDP Server and waits for incomming messages with RGB data in TPM2(.net) format.

First LED is at the bottom left corner running anti-clockwise around the window.

I use it for tests of the lightoros LED engine.

Configuration
-------------
Check the config.py file for configuration of the LEDs.

Notes
-----
Seems that Python's socketserver library is leaking memory. I can confirm that with Python 3.7.3 on macOS. Follow the issue: https://bugs.python.org/issue37193 for more info.

For information about TPM2 protocol check this page: https://gist.github.com/jblang/89e24e2655be6c463c56

License
-------
MIT license, see [LICENSE](./LICENSE)