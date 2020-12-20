from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Rectangle, Color
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.clock import Clock
import socket
import threading
import socketserver
from kivy.utils import rgba
from config import *

MIN_DOT_SIDE = 6
MAX_DOT_SIDE = 15
MIN_DOT_SPACE = 2
DOT_SPACE_X = MIN_DOT_SPACE
DOT_SPACE_Y = MIN_DOT_SPACE

msg_buffer = []
sim = None
data_lock = threading.Lock()


class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        global msg_buffer
        message, socket = self.request[0], self.request[1]
        # TPM2
        # 0: Packet start byte: 0xC9
        # 1: Packet type: 0xDA - Data frame
        # 2: Fame size: High Byte
        # 3: Fame size: Low Byte
        # User-data
        # Packet end byte: 0x36
        if message[0] == 0xC9 and message[1] == 0xDA:
            frame_size = message[2] << 8
            frame_size |= message[3]
            ledCount = frame_size // 3
            index = 4
            buffer = []
            for i in range(ledCount):
                buffer.append({
                    "r": message[index + 1],
                    "g": message[index],
                    "b": message[index + 2]
                })
                index = index + 3
            with data_lock:
                msg_buffer = buffer
                sim.update()
        # TPM2.net
        # 0: Packet start byte: 0x9C
        # 1: Packet type: 0xDA - Data frame
        # 2: Fame size: High Byte
        # 3: Fame size: Low Byte
        # 4: Packet number: 1-255
        # 5: Number of packets: 1-255
        # User-data
        # Packet end byte: 0x36
        elif message[0] == 0x9C and message[1] == 0xDA:
            frame_size = message[2] << 8
            frame_size |= message[3]
            ledCount = frame_size // 3
            index = 6
            buffer = []
            for i in range(ledCount):
                buffer.append({
                    "r": message[index + 1],
                    "g": message[index],
                    "b": message[index + 2]
                })
                index = index + 3
            frame_index = message[4] - 1
            with data_lock:
                msg_buffer[frame_index] = buffer
                if len(msg_buffer) == message[5]:
                    flat_buffer = []
                    for buf in msg_buffer:
                        for clr in buf:
                            flat_buffer.append(clr)
                    msg_buffer = flat_buffer
                    sim.update()


class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    pass


class LightDot(Label):
    def __init__(self, **kwargs):
        super(LightDot, self).__init__(**kwargs)
        self.bind(pos=self.update_rect, size=self.update_rect)

    def set_bgcolor(self, r, g, b, a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(r, g, b, a)
            self.rect = Rectangle(pos=self.pos, size=self.size)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class Simulator(App):
    dots = []
    server = None

    def on_win_resize(self, window, width, height):
        print("RESIZE: {}x{}".format(width, height))
        size = window.system_size
        self.create_dots(size[0], size[1])
        self.root.clear_widgets()
        for dot in self.dots:
            dot.set_bgcolor(1, 1, 1, 0.4)
            self.root.add_widget(dot)

    def update(self):
        clrs_count = len(msg_buffer)
        dots_count = len(self.dots)
        if clrs_count != dots_count:
            print("Number of colors {} in UDP message is not equal to number of dots {} in simulator".format(
                clrs_count, dots_count))
            return
        for i in range(clrs_count):
            col = msg_buffer[i]
            col_rgba = rgba(col["r"], col["g"], col["b"])
            self.dots[i].set_bgcolor(
                col_rgba[0], col_rgba[1], col_rgba[2], col_rgba[3])

    def build(self):
        self.server = ThreadedUDPServer((HOST, PORT), RequestHandler)
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        screen_size = Window.size
        self.create_dots(screen_size[0], screen_size[1])

        layout = FloatLayout()
        for dot in self.dots:
            dot.set_bgcolor(1, 1, 1, 0.4)
            layout.add_widget(dot)

        Window.bind(on_resize=self.on_win_resize)
        return layout

    def calc_dot_side(self, width, height):
        global DOT_SPACE_X
        global DOT_SPACE_Y

        dot_side = (width - (DOTS_H - 1) * DOT_SPACE_X) / (2 + DOTS_H)
        if dot_side > MAX_DOT_SIDE:
            dot_side = MAX_DOT_SIDE
        elif dot_side < MIN_DOT_SIDE:
            dot_side = MIN_DOT_SIDE

        while True:
            DOT_SPACE_X = (width - 2 * dot_side - DOTS_H *
                           dot_side) / (DOTS_H - 1)
            DOT_SPACE_Y = (height - 2 * dot_side -
                           DOTS_V * dot_side) / (DOTS_V - 1)
            if (DOT_SPACE_X <= MIN_DOT_SPACE or DOT_SPACE_Y <= MIN_DOT_SPACE) and dot_side > MIN_DOT_SIDE:
                dot_side = dot_side - 1
            else:
                break

        return dot_side

    def create_dots(self, width, height):
        global DOT_SIDE

        self.dots = []

        DOT_SIDE = self.calc_dot_side(width, height)
        dot_size = (DOT_SIDE, DOT_SIDE)

        led_idx = 0
        if CORNERS is True:
            pos = (0, 0)
            dot = LightDot(text=str(led_idx), size=(DOT_SIDE * 0.75, DOT_SIDE * 0.75),
                           pos=pos, size_hint=(None, None))
            self.dots.append(dot)
            led_idx += 1

        for i in range(DOTS_H):
            x = DOT_SIDE + i * (DOT_SIDE + DOT_SPACE_X)
            y = 0
            pos = (x, y)
            dot = LightDot(size=dot_size,
                           pos=pos, size_hint=(None, None))
            self.dots.append(dot)
            led_idx += 1

        if CORNERS is True:
            pos = (width - DOT_SIDE * 0.75, 0)
            dot = LightDot(size=(DOT_SIDE * 0.75, DOT_SIDE * 0.75),
                           pos=pos, size_hint=(None, None))
            self.dots.append(dot)
            led_idx += 1

        for i in range(DOTS_V):
            x = width - DOT_SIDE
            y = DOT_SIDE + i * (DOT_SIDE + DOT_SPACE_Y)
            pos = (x, y)
            dot = LightDot(size=dot_size,
                           pos=pos, size_hint=(None, None))
            self.dots.append(dot)
            led_idx += 1

        if CORNERS is True:
            pos = (width - DOT_SIDE * 0.75, height - DOT_SIDE * 0.75)
            dot = LightDot(size=(DOT_SIDE * 0.75, DOT_SIDE * 0.75),
                           pos=pos, size_hint=(None, None))
            self.dots.append(dot)
            led_idx += 1

        for i in range(DOTS_H):
            x = width - 2 * DOT_SIDE - i * (DOT_SIDE + DOT_SPACE_X)
            y = height - DOT_SIDE
            pos = (x, y)
            dot = LightDot(size=dot_size,
                           pos=pos, size_hint=(None, None))
            self.dots.append(dot)
            led_idx += 1

        if CORNERS is True:
            pos = (0, height - DOT_SIDE * 0.75)
            dot = LightDot(size=(DOT_SIDE * 0.75, DOT_SIDE * 0.75),
                           pos=pos, size_hint=(None, None))
            self.dots.append(dot)
            led_idx += 1

        for i in range(DOTS_V):
            x = 0
            y = height - 2 * DOT_SIDE - i * (DOT_SIDE + DOT_SPACE_Y)
            pos = (x, y)
            dot = LightDot(size=dot_size,
                           pos=pos, size_hint=(None, None))
            self.dots.append(dot)
            led_idx += 1


if __name__ == '__main__':
    sim = Simulator()
    sim.run()
