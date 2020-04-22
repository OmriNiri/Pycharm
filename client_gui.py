from tkinter import *
from socket import socket, error


ENABLE_BUTTON_MESSAGE = "control$true"
UNABLE_BUTTON_MESSAGE = "control$false"
TITLE = "Screen Sharing\n\n\n\n\n\nYou can enable or unable" \
        " the client's control over your computer\n\n\n\n\nYou need to resize your computer" \
        " resolution:\nSettings-->System-->Display-->Resolution-->1280x720" \
        "\n\n\n\n\n\nPress any key to continue"
IP = '127.0.0.1'
PORT = 40000


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
                          font="Broadway 14", bd=0, cursor="arrow", width=50, height=20)
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
        ControlClient(ENABLE_BUTTON_MESSAGE, UNABLE_BUTTON_MESSAGE)


class ControlClient(object):
    """
    the user can control his computer-
    he decides whether the client has control
    over his computer or not
    """
    def __init__(self, enable_button_message, unable_button_message):
        self.enable_button_message = enable_button_message.encode()
        self.unable_button_message = unable_button_message.encode()
        self.root = Tk()
        self.root.title('Control Client')
        self.root.configure(bg="alice blue")
        self.root.geometry("200x150+200+200")
        self.enable_button = Radiobutton(self.root, text='Control Mode',
                                         command=self.enable_control, value=True,
                                         fg="dark violet", bg="alice blue", cursor="exchange")
        self.enable_button.select()
        self.enable_button.pack(anchor=W)
        self.unable_button = Radiobutton(self.root, text='Viewing Mode',
                                         command=self.unable_control, value=False,
                                         fg="dark violet", bg="alice blue", cursor="exchange")
        self.unable_button.pack(anchor=W)
        self.label = Label(self.root, text='\n\n\nServer is running...', fg="dark violet",
                           bg="alice blue", bd=0)
        self.label.pack(anchor=CENTER)
        self.control_socket = socket()
        self.connect_to_server()
        self.root.mainloop()

    def connect_to_server(self):
        """
        tries to connect to the server
        """
        try:
            self.control_socket.connect((IP, PORT))
        except error as msg:
            print(msg)

    def send_data(self, data):
        """
        sends data according to the protocol
        """
        # Send the size of the pixels length
        size = len(data)
        size_len = (size.bit_length() + 7) // 8
        self.control_socket.send(bytes([size_len]))

        # Send the actual pixels length
        size_bytes = size.to_bytes(size_len, 'big')
        self.control_socket.send(size_bytes)

        # Send pixels
        self.control_socket.sendall(data)

    def enable_control(self):
        """
        sends data to the server that
        enables the client to control the
        server's computers
        """
        self.send_data(self.enable_button_message)

    def unable_control(self):
        """
        sends data to the server that
        blocks the client from controlling the
        server's computers
        """
        self.send_data(self.unable_button_message)


def main():
    """
    calls OpeningScreen()
    """
    OpeningScreen()


if __name__ == '__main__':
    main()
