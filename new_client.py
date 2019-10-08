from tkinter import *
from tkinter import messagebox
from socket import socket, error, timeout
from io import BytesIO
from PIL import Image, ImageTk
import tkinter
import select
from time import time, sleep


STREAM_PORT = 50000
CONTROL_PORT = 60000
KEY_PROTOCOL = 'key$'
CLICK_PROTOCOL = 'click$'
MOTION_PROTOCOL = 'motion$'
SCROLL_PROTOCOL = 'scroll$'
GEOMETRY = '1280x720+200+200'
KEY_PRESS = "<KeyPress>"
BUTTON1 = "<Button-1>"
BUTTON3 = "<Button-3>"
MOTION = '<Motion>'
WHEEL = "<MouseWheel>"
TITLE = "Screen Sharing\n\n\n\n\n\nYou can see the screen" \
        " of the controlled computer and\n control it: every" \
        " mouse motion, click or keyboard\n commands will be executed\n\n\n\n\n" \
        "Press any key to continue"


class Client(object):
    """
    the client communicates with the server- it
    receives images and it sends control commands
    such as: mouse and keyboard
    """
    def __init__(self, stream_socket, control_socket):
        self.stream_socket = stream_socket
        self.control_sock = control_socket
        self.root = Tk()
        self.root.geometry(GEOMETRY)
        self.root.bind(KEY_PRESS, self.key_down)
        self.root.bind(BUTTON1, self.left_click)
        self.root.bind(BUTTON3, self.right_click)
        self.root.bind(MOTION, self.motion)
        self.root.bind(WHEEL, self.scroll)
        self.root.bind()
        self.panel = None
        self.open_client_sockets = []
        self.send_sockets = []
        self.key = ""
        self.click = ""
        self.scroll_num = 0
        self.mouse_position = []
        self.key_protocol = KEY_PROTOCOL
        self.click_protocol = CLICK_PROTOCOL
        self.motion_protocol = MOTION_PROTOCOL
        self.scroll_protocol = SCROLL_PROTOCOL
        self.motion_time = time()

    def scroll(self, event):
        """
        the function is called whenever the user scrolls
        takes the delta of the scroll and sends it
        """
        self.scroll_num = event.delta
        message_to_send = self.scroll_protocol + self.scroll_num
        self.send_control_commands(message_to_send.encode())

    def left_click(self, event):
        """
        the function is called whenever the user clicks
        sends the left click to the server
        """
        self.click = 'left'
        message_to_send = self.click_protocol + self.click
        self.send_control_commands(message_to_send.encode())

    def right_click(self, event):
        """
        the function is called whenever the user clicks
        sends the right click to the server
        """
        self.click = 'right'
        message_to_send = self.click_protocol + self.click
        self.send_control_commands(message_to_send.encode())

    def key_down(self, e):
        """
        the function is called whenever the user presses the key
        sends the key to the server
        """
        self.key = e.keysym
        correct_key_str = self.correct_key()
        message_to_send = self.key_protocol + correct_key_str
        self.send_control_commands(message_to_send.encode())

    def high_pass_filter(self):
        """
        calculates the time since the last movement
        of the mouse and returns true if it is
        greater than 0.2
        """
        current_time = time()
        delta = current_time - self.motion_time
        if delta > 0.2:
            self.motion_time = current_time
            return True
        return False

    def motion(self, event):
        """
        the function is called whenever the user moves the mouse
        gets the location of the mouse and sends
        it to the server
        """
        x, y = event.x, event.y
        if len(self.mouse_position) == 0:
            self.mouse_position.append(x)
            self.mouse_position.append(y)
        else:
            self.mouse_position[0] = x
            self.mouse_position[1] = y
        if self.high_pass_filter():
            message_to_send = self.motion_protocol + self.correct_mouse_position()
            self.send_control_commands(message_to_send.encode())

    def recvall(self, length):
        """
        Retrieve all pixels
        """
        buf = b''
        while len(buf) < length:
            data = self.stream_socket.recv(length - len(buf))
            if not data:
                return data
            buf += data
        return buf

    def recv_data(self):
        """
        receive the data according to the protocol
        """
        size_len = int.from_bytes(self.stream_socket.recv(1), byteorder='big')
        size = int.from_bytes(self.stream_socket.recv(size_len), byteorder='big')
        data = self.recvall(size)
        return data

    def send_control_commands(self, data):
        """
        sends control commands according to the protocol
        """
        # Send the size of the data length
        size = len(data)
        size_len = (size.bit_length() + 7) // 8
        self.control_sock.send(bytes([size_len]))

        # Send the actual data length
        size_bytes = size.to_bytes(size_len, 'big')
        self.control_sock.send(size_bytes)

        # Send data
        self.control_sock.sendall(data)

    def display_screen(self):
        """
        it transforms the pixels and display it
        """
        pixels = self.recv_data()
        # Create the Surface from raw pixels
        buf1 = BytesIO()
        buf1.write(pixels)
        img = Image.open(buf1).convert('RGB')
        tk_img = ImageTk.PhotoImage(image=img)

        if self.panel is None:
            self.panel = tkinter.Label(self.root, image=tk_img)
            self.panel.pack(side="bottom", fill="both", expand="yes")
            self.panel.image = tk_img
        else:
            self.panel.configure(image=tk_img)
            self.panel.image = tk_img

    def correct_key(self):
        """
        it changes the different keys to the
        proper format
        """
        key_list = self.key.split('_')
        correct_key_str = ''
        for i in key_list:
            if i == 'L':
                i = 'left'
            elif i == 'R':
                i = 'right'
            elif i == 'Return':
                i = 'enter'
            correct_key_str += i
        return correct_key_str.lower()

    def correct_mouse_position(self):
        """
        takes the x and y positions and returns a
        str with ',' between them
        """
        correct_position_str = str(self.mouse_position[0]) + ',' + str(self.mouse_position[1])
        return correct_position_str

    def start(self):
        """
        calls all the function
        loops with after
        """
        try:
            rlist, wlist, xlist = select.select([self.stream_socket] + self.open_client_sockets,
                                                [self.control_sock] + self.send_sockets, self.open_client_sockets)
            for current_socket in xlist:
                current_socket.close()
                self.open_client_sockets.pop(self.open_client_sockets.index(
                    current_socket))
            for current_socket in rlist:
                if current_socket is self.stream_socket:
                    self.display_screen()
        except error:
            self.close_connection()
            Connect(True)
        finally:
            self.root.after(1, self.start)

    def run(self):
        """
        creates the tkinter mainloop and calls start
        """
        try:
            self.root.after(1, self.start)
            self.root.mainloop()
        except error as msg:
            print(msg)

    def close_connection(self):
        """
        closes the sockets and the root
        """
        self.stream_socket.close()
        self.control_sock.close()
        self.root.destroy()


class OpeningScreen(object):
    """
    presents the opening screen of
    the client
    """
    def __init__(self):
        self.root = Tk()
        self.root.title("Opening Screen")
        self.root.configure(bg="DarkOrchid4")
        self.root.bind("<KeyPress>", self.run_client)
        self.title = Text(self.root, fg="ghost white", bg="DarkOrchid4",
                          font="Broadway 14", bd=0, cursor="arrow", width=50, height=15)
        self.title.tag_configure("center", justify='center')
        self.title.insert("1.0", TITLE)
        self.title.tag_add("center", "1.0", "end")
        self.title.config(state=DISABLED)
        self.title.pack()
        self.root.mainloop()

    def run_client(self, event):
        """
        destroys the opening screen and
        runs the connect panel
        """
        self.root.destroy()
        Connect(False)


class Connect(object):
    """
    creates the sockets for the Client
    and asks the user to enter the server's
    IP
    it checks if the IP is valid and tries to
    connect to the server
    """
    def __init__(self, is_alive):
        self.stream_socket = socket()
        self.control_sock = socket()
        self.stream_socket.settimeout(2)
        self.control_sock.settimeout(2)

        self.root = Tk()
        self.root.title('Connect')
        self.root.configure(bg="alice blue")
        self.root.bind("<KeyPress>", self.key_pressed)
        self.title = Text(self.root, fg="purple2", bg="alice blue", font="Broadway 14", bd=0,
                          cursor="arrow", width=30, height=6)
        self.title.tag_configure("center", justify='center')
        self.title.insert("1.0", "Connect Panel")
        self.title.tag_add("center", "1.0", "end")
        self.title.config(state=DISABLED)
        self.title.grid(row=0)
        index = 1
        if is_alive:
            self.label = Label(self.root, text="Server is disconnected...Try to connect again\n\n",
                               fg="purple2", bg="alice blue", bd=0)
            self.label.grid(row=index)
            index += 1
        self.entry = Entry(self.root, fg="purple2", bg="alice blue", width=30)
        self.entry.insert(0, "Enter IP:")
        self.entry.bind("<1>", self.delete_type)
        self.entry.grid(row=index)
        self.button = Button(self.root, text="Connect", fg="purple2", bg="alice blue",
                             bd=1, cursor="hand2", command=self.check_ip)
        self.button.grid(row=index + 1)
        self.is_delete = True
        self.root.mainloop()

    def key_pressed(self, e):
        """
        checks if enter is pressed and
        calls check_ip()
        """
        key = e.keysym
        if key == "Return":
            self.check_ip()

    def delete_type(self, e):
        """
        deletes the 'Enter IP:' str whenever
        the user clicks on the entry
        """
        if self.is_delete:
            self.entry.delete(0, 10)
            self.is_delete = False

    def check_list(self, list1):
        """
        returns true if all list items are numbers and
        between 0 and 255
        """
        if len(list1) == 0:
            return True
        if list1[0].isdigit() and 0 <= int(list1[0]) <= 255:
            return self.check_list(list1[1:])
        return False

    def check_ip(self):
        """
        takes the IP from the client
        checks if it's valid and calls
        check_connect()
        """
        ip = self.entry.get()
        self.entry.delete(0, 16)
        ip_list = ip.split('.')
        if len(ip_list) == 4:
            is_valid = self.check_list(ip_list)
            if is_valid:
                self.check_connect(ip)
            else:
                messagebox.showwarning("Invalid Input", "The IP you put is not valid")
        else:
            messagebox.showwarning("Invalid Input", "The IP you put is not valid")

    def check_connect(self, ip):
        """
        tries to connect tp the server
        if there is an error (timeout)
        it displays a proper message
        if it succeeds it destroys
        the GUI and opens the screen
        with the stream from the server
        """
        try:
            self.stream_socket.connect((ip, STREAM_PORT))
            self.control_sock.connect((ip, CONTROL_PORT))
            self.root.destroy()
            sleep(2)
            client = Client(self.stream_socket, self.control_sock)
            client.run()
        except error or timeout as msg:
            if "10056" in str(msg):
                self.stream_socket = socket()
                self.control_sock = socket()
                self.stream_socket.settimeout(2)
                self.control_sock.settimeout(2)
                self.check_connect(ip)
            else:
                messagebox.showerror("IP Problem", "Either the server is not working or the IP is incorrect")


def main():
    """
    calls OpeningScreen()
    """
    OpeningScreen()


if __name__ == '__main__':
    main()
