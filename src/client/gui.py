import Tkinter
import tkMessageBox
import ttk
from protocol import *
from gui_helpers import IntegerEntry


class RootWindow(Tkinter.Tk, object):
    """
    The main GUI window.
    Responsible for switching frames inside it and acts as mediator for all functions called within it.
    """

    def __init__(self, args):
        super(RootWindow, self).__init__()

        self.nickname = None
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Setup all the frames
        self.server_selection_frame = ServerSelectionFrame(self)
        self.lobby_frame = LobbyFrame(self)

        # Setup connections
        self.rpc = RPCClient(args)
        setup_servers_listener(args, self.update_servers_list)

        # Show the first frame
        self.server_selection_frame.pack(fill=Tkinter.BOTH)

    def on_exit(self):
        """
        Close all open connections on closing the window.
        """

        if self.nickname is not None:
            # We are connected to a server
            self.leave_server()

        self.rpc.exit()
        self.destroy()

    def update_servers_list(self, servers):
        """
        Update the servers list in server_selection_frame

        Args:
            servers (list[str]): List of server names
        """

        self.server_selection_frame.update_servers_list(servers)

    def join_server(self, server_name, nickname):
        """
        Join the server and display the lobby_frame

        Args:
            server_name (str):
            nickname (str):

         Returns:
            bool: True if operation was a success
        """

        self.rpc.server_name = server_name

        response = self.rpc.connect(user=nickname)

        if response['err']:
            self.rpc.server_name = None
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            self.nickname = nickname
            self.server_selection_frame.pack_forget()
            self.lobby_frame.pack(fill=Tkinter.BOTH)

            self.lobby_frame.update_games(response['sessions'])

            return True

    def leave_server(self):
        """
        Leave the server and return to the server_selection_frame

        Returns:
            bool: True if operation was a success
        """
        response = self.rpc.disconnect(user=self.nickname)

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            self.nickname = None
            self.rpc.server_name = None

            self.lobby_frame.pack_forget()
            self.server_selection_frame.pack(fill=Tkinter.BOTH)

            return True

    def new_game(self, game_name, game_size):
        """
        Start a new game on the server.

        Args:
            game_name (str): Name of the game
            game_size (int): Max number of players

        Returns:
            bool: True if operation was a success, False on error
        """

        response = self.rpc.create_session(user=self.nickname, sname=game_name, player_count=game_size)

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            self.lobby_frame.pack_forget()
            # TODO: open the game

            return True

    def join_game(self, game_name):
        """
        Join a game on the server.

        Args:
            game_name (str): Name of the game

        Returns:
            bool: True if operation was a success, False on error
        """

        response = self.rpc.join_session(user=self.nickname, sname=game_name)

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            self.lobby_frame.pack_forget()
            # TODO: open the game

            return True


class ServerSelectionFrame(Tkinter.Frame, object):

    def __init__(self, parent):
        """
        Displays a list of available game servers.
        Allows to choose the nickname and join selected game server.

        Args:
            parent (RootWindow):
        """
        super(ServerSelectionFrame, self).__init__(parent)

        self.parent = parent

        # Define and position the widgets

        Tkinter.Label(self, text='Nickname:').grid(row=0, column=0)
        Tkinter.Label(self, text='Servers:').grid(row=1, column=0)

        self.nickname_input = Tkinter.Entry(self, width=10)
        self.nickname_input.grid(row=0, column=1)

        self.servers_listbox = Tkinter.Listbox(self, selectmode=Tkinter.SINGLE)
        self.servers_listbox.bind('<<ListboxSelect>>', self.toggle_join_button)
        self.servers_listbox.grid(row=2, column=0, columnspan=2)

        self.join_button = Tkinter.Button(self, text="Join server >>", state=Tkinter.DISABLED,
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
        self.nickname_input.delete(0, Tkinter.END)

    def update_servers_list(self, servers):
        """
        Update the servers list in servers_listbox

        Args:
            servers (list[str]): List of server names
        """

        for server in servers:
            self.servers_listbox.insert(Tkinter.END, server)


class LobbyFrame(Tkinter.Frame, object):

    def __init__(self, parent):
        """
        Displays a list of available games in server.
        Allows to grate a new game and join existing ones.

        Args:
            parent (RootWindow):
        """
        super(LobbyFrame, self).__init__(parent)

        self.parent = parent

        # Define and position the widgets

        self.leave_button = Tkinter.Button(self, text="<< Leave server", command=self.leave_server)
        self.leave_button.grid(row=0, column=0)

        ttk.Separator(self, orient=Tkinter.HORIZONTAL).grid(row=1, column=0, columnspan=10, sticky='ew')

        Tkinter.Label(self, text='New game name:').grid(row=2, column=0)
        self.game_name_input = Tkinter.Entry(self, width=10)
        self.game_name_input.grid(row=2, column=1)
        Tkinter.Label(self, text='Game size:').grid(row=3, column=0)
        self.game_size_input = IntegerEntry(self, width=10)
        self.game_size_input.grid(row=3, column=1)
        self.new_game_button = Tkinter.Button(self, text="Start a new game", command=self.new_game)
        self.new_game_button.grid(row=4, column=1)

        self.join_game_button = Tkinter.Button(self, text="Join game >>", state=Tkinter.DISABLED,
                                               command=self.join_game)
        self.join_game_button.grid(row=2, column=3)
        self.games_listbox = Tkinter.Listbox(self, selectmode=Tkinter.SINGLE)
        self.games_listbox.bind('<<ListboxSelect>>', self.toggle_join_button)
        self.games_listbox.grid(row=3, column=3, rowspan=5)

    def leave_server(self):
        """
        Return to the server selection frame.
        """
        self.parent.leave_server()
        self.game_name_input.delete(0, Tkinter.END)
        self.game_size_input.delete(0, Tkinter.END)

    def new_game(self):
        """
        Start a new game.
        """

        game_size = int(self.game_size_input.get() or '0')

        if game_size < 3:
            tkMessageBox.showerror('Error', 'Game must have atleast 3 players.')
        else:
            self.parent.new_game(self.game_name_input.get(), game_size)

    def join_game(self):
        """
        Join an existing game.
        """

        game_name = self.games_listbox.get(self.games_listbox.curselection()[0])

        self.parent.join_game(game_name)

    def toggle_join_button(self, event):
        """
        Disable/enable the join_button
        """

        if len(self.games_listbox.curselection()) > 0:
            self.join_game_button.configure(state=Tkinter.NORMAL)
        else:
            self.join_game_button.configure(state=Tkinter.DISABLED)

    def update_games(self, games_list):
        """
        Update the list of games on this server.

        Args:
            games_list list[dict[str, object]]:

        """

        self.games_listbox.delete(0, Tkinter.END)
        for game in games_list:
            self.games_listbox.insert(Tkinter.END, game['session_name'])