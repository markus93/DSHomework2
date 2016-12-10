import Tkinter
from protocol import *


class RootWindow(Tkinter.Tk, object):
    """
    The main GUI window.
    Responsible for switching frames inside it and acts as mediator for all functions called within it.
    """

    def __init__(self, args):
        super(RootWindow, self).__init__()

        # Setup all the frames
        self.server_selection_frame = ServerSelectionFrame(self)

        # Setup connections
        self.rpc = RPCClient(args)
        setup_servers_listener(args, self.update_servers_list)

        # Show the first frame
        self.server_selection_frame.pack(fill=Tkinter.BOTH)

    def update_servers_list(self, servers):
        """
        Update the servers list in ServerSelectionFrame

        Args:
            servers (list[str]): List of server names
        """

        self.server_selection_frame.update_servers_list(servers)


class ServerSelectionFrame(Tkinter.Frame, object):
    """
    Displays a list of available game servers.
    """

    def __init__(self, parent):
        """

        Args:
            parent (RootWindow):
        """
        super(ServerSelectionFrame, self).__init__(parent)

        self.parent = parent
        # Define and position the widgets

        Tkinter.Label(self, text='Nickname:').grid(row=0, column=0)

        self.nickname_input = Tkinter.Entry(self, width=10)
        self.nickname_input.grid(row=0, column=1)

        self.servers_listbox = Tkinter.Listbox(self, selectmode=Tkinter.SINGLE)
        self.servers_listbox.bind('<<ListboxSelect>>', self.toggle_join_button)
        self.servers_listbox.grid(row=1, column=0, columnspan=2)

        self.join_button = Tkinter.Button(self, text="Join server", state=Tkinter.DISABLED,
                                          command=self.join_server)
        self.join_button.grid(row=0, column=3)

    def toggle_join_button(self, event):
        """
        Disable/enable the join_button
        """

        if len(self.servers_listbox.curselection()) > 0:
            self.join_button.configure(state=Tkinter.NORMAL)
        else:
            self.join_button.configure(state=Tkinter.DISABLED)

    def join_server(self):
        """
        Try to join selected server
        """

        server_name = self.servers_listbox.get(self.servers_listbox.curselection()[0])
        nickname = self.nickname_input.get()

        self.parent.join_server(server_name, nickname)

    def update_servers_list(self, servers):
        """
        Update the servers list in servers_listbox

        Args:
            servers (list[str]): List of server names
        """

        for server in servers:
            self.servers_listbox.insert(Tkinter.END, server)
