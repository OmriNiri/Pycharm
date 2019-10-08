from socket import socket, error
from pyautogui import *
from PIL import Image
from io import BytesIO
import select
from threading import Thread
import subprocess
import sys
from mss import mss


DETACHED_PROCESS = 0x00000008
IP = '0.0.0.0'
GUI_PORT = 40000
STREAM_PORT = 50000
CONTROL_PORT = 60000
KEY_PROTOCOL = 'key'
CLICK_PROTOCOL = 'click'
MOTION_PROTOCOL = 'motion'
SCROLL_PROTOCOL = 'scroll'
INNER_SEPARATOR = '$'
MONITOR = {"top": 0, "left": 0, "width": 1280, "height": 720}


class Server(object):
    """
    creates the sockets
    runs the gui_client.py
    takes screen shots and sends them
    to the client when it connects
    it receives control commands and it
    does them
    """
    def __init__(self):
        self.stream_sock = socket()
        self.stream_sock.bind((IP, STREAM_PORT))
        self.stream_conn = None
        self.control_sock = socket()
        self.control_sock.bind((IP, CONTROL_PORT))
        self.control_conn = None
        self.gui_sock = socket()
        self.gui_sock.bind((IP, GUI_PORT))
        self.gui_conn = None
        self.open_client_sockets = []
        self.send_sockets = []
        self.key_protocol = KEY_PROTOCOL
        self.click_protocol = CLICK_PROTOCOL
        self.motion_protocol = MOTION_PROTOCOL
        self.scroll_protocol = SCROLL_PROTOCOL
        self.inner_separator = INNER_SEPARATOR
        self.is_control = True
        self.w, self.h = 1280, 720
        self.is_alive = True
        self.monitor = MONITOR

    def grab(self):
        """
        grabs a screen shot and returns
        an Image with the pixels in it
        """
        with mss() as sct:
            screen = sct.grab(self.monitor)
            return Image.frombytes('RGB', (self.w, self.h), screen.rgb, 'raw', 'RGB')

    def send_stream(self, data):
        """
        sends the pixels to the client with
        the stream socket according to the
        protocol
        """
        try:
            # Send the size of the pixels length
            size = len(data)
            size_len = (size.bit_length() + 7) // 8
            self.stream_conn.send(bytes([size_len]))

            # Send the actual pixels length
            size_bytes = size.to_bytes(size_len, 'big')
            self.stream_conn.send(size_bytes)

            # Send pixels
            self.stream_conn.sendall(data)
        except error:
            self.is_alive = False
            if self.stream_conn is not None and self.control_conn is not None:
                self.stream_conn.close()
                self.control_conn.close()

    def recv_control_data(self):
        """
        receives data from the client
        according to the protocol and
        returns it
        """
        try:
            size_len = int.from_bytes(self.control_conn.recv(1), byteorder='big')
            size = int.from_bytes(self.control_conn.recv(size_len), byteorder='big')
            data = self.control_conn.recv(size)
            return data.decode()
        except error:
            self.is_alive = False
            self.stream_conn.close()
            self.control_conn.close()

    def recv_gui_data(self):
        """
        receives data from the gui_client.py
        and returns it
        """
        try:
            size_len = int.from_bytes(self.gui_conn.recv(1), byteorder='big')
            size = int.from_bytes(self.gui_conn.recv(size_len), byteorder='big')
            data = self.gui_conn.recv(size)
            return data.decode()
        except error:
            self.gui_conn.close()

    def send_screen_shots(self):
        """
        takes the Image from grab()
        and saves on the buffer as
        JPEG. then, it takes the
        pixels and calls send_stream()
        """
        while self.is_alive:
            im = self.grab()
            buf = BytesIO()
            im.save(buf, format='JPEG', quality=60)
            pixels = buf.getvalue()
            self.send_stream(pixels)

    def control_key(self, key_message):
        """
        takes the key and presses it
        """
        key_list = key_message.split(self.inner_separator)
        if len(key_list) == 2 and self.is_control:
            press(key_list[1])

    def control_click(self, click_message):
        """
        takes the click and clicks it
        """
        click_list = click_message.split(self.inner_separator)
        if len(click_list) == 2 and self.is_control:
            click(button=click_list[1])

    def control_motion(self, motion_message):
        """
        takes the position and moves it
        """
        motion_list = motion_message.split(self.inner_separator)
        if len(motion_list) == 2 and self.is_control:
            x, y = motion_list[1].split(',')
            new_x = int(int(x) * 1)
            new_y = int(int(y) * 1)
            moveTo(new_x, new_y)

    def control_scroll(self, scroll_message):
        """
        takes the scroll and scrolls it
        """
        scroll_list = scroll_message.split(self.inner_separator)
        if len(scroll_list) == 2 and self.is_control:
            scroll(int(scroll_list[1]))

    def check_control_data(self, data):
        """
        checks which type of control command
        is the data and calls the proper
        function
        """
        if self.key_protocol in data:
            self.control_key(data)
        elif self.click_protocol in data:
            self.control_click(data)
        elif self.scroll_protocol in data:
            self.control_scroll(data)
        else:
            self.control_motion(data)

    def check_gui_data(self, data):
        """
        checks the gui_client.py data and sets
        self.is_control according to the data
        """
        is_control = data.split(self.inner_separator)[1]
        if is_control == 'true':
            self.is_control = True
        else:
            self.is_control = False

    def handle_gui(self):
        """
        receives the data from the gui_client
        and calls check_gui_data()
        """
        while True:
            data = self.recv_gui_data()
            if data == '' or data is None:
                self.gui_conn.close()
            else:
                self.check_gui_data(data)

    def start(self):
        """
        starts the listen in the sockets
        runs the gui_client.py
        calls the above functions
        """
        self.stream_sock.listen(1)
        self.control_sock.listen(1)
        self.gui_sock.listen(1)
        print('Server started.')
        pid = subprocess.Popen([sys.executable, "gui_client.py"],
                               creationflags=DETACHED_PROCESS).pid
        while True:
            rlist, wlist, xlist = select.select([self.stream_sock, self.control_sock, self.gui_sock]
                                                + self.open_client_sockets,
                                                self.send_sockets, self.open_client_sockets)
            for current_socket in xlist:
                current_socket.close()
                self.open_client_sockets.pop(self.open_client_sockets.index(
                    current_socket))
            for current_socket in rlist:
                # check for new connection
                if current_socket is self.stream_sock:
                    self.stream_conn, client_address = current_socket.accept()
                    self.is_alive = True
                    t = Thread(target=self.send_screen_shots)
                    t.start()
                elif current_socket is self.control_sock:
                    self.control_conn, client_address = current_socket.accept()
                    self.open_client_sockets.append(self.control_conn)
                elif current_socket is self.gui_sock:
                    self.gui_conn, client_address = current_socket.accept()
                    self.is_alive = True
                    t = Thread(target=self.handle_gui)
                    t.start()
                else:
                    # control sock sends data
                    if self.control_conn is not None:
                        data = self.recv_control_data()
                        if data == '' or data is None:
                            current_socket.close()
                            self.open_client_sockets.pop(self.open_client_sockets.index(
                                current_socket))
                        else:
                            self.check_control_data(data)

    def close_connection(self):
        """
        closes all the sockets
        """
        self.stream_sock.close()
        self.control_sock.close()
        self.gui_sock.close()


def main():
    """
    creates the server and runs it
    """
    server = Server()
    try:
        server.start()
    finally:
        server.close_connection()


if __name__ == '__main__':
    main()
