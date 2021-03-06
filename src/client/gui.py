import tkMessageBox
import ttk
import re
from protocol import *
from gui_helpers import *


class RootWindow(Tkinter.Tk, object):
    """
    The main GUI window.
    Responsible for switching frames inside it and acts as mediator for all functions called within it.
    """

    def __init__(self, args):
        super(RootWindow, self).__init__()

        self.connection_args = args

        self.player_name = None
        self.game_name = None
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Setup all the frames
        self.server_selection_frame = ServerSelectionFrame(self)
        self.lobby_frame = LobbyFrame(self)
        self.game_setup_frame = GameSetupFrame(self)
        self.game_frame = GameFrame(self)

        # Setup connections
        self.rpc = RPCClient(args, self)
        self.global_listener = GlobalListener(args, self.server_selection_frame.update_servers_list)
        self.server_listener = None
        self.game_listener = None
        self.player_listener = None
        self.player_announcements = None


        # Show the first frame
        self.show_frame(self.server_selection_frame)

    def on_exit(self):
        """
        Close all open connections on closing the window.
        """

        if self.player_name is not None:
            # We are connected to a server
            if self.game_name is not None:
                # We are in game
                self.leave_game()

            self.leave_server()

        self.rpc.exit()
        self.global_listener.exit()

        if self.server_listener is not None:
            self.server_listener.exit()
        if self.game_listener is not None:
            self.game_listener.exit()
        if self.player_listener is not None:
            self.player_listener.exit()
        if self.player_announcements is not None:
            self.player_announcements.exit()

        self.destroy()

    def show_frame(self, new_frame):
        """
        Hide all other frames
        """
        for frame in (self.server_selection_frame, self.lobby_frame, self.game_setup_frame, self.game_frame):
            if frame.winfo_ismapped():
                frame.pack_forget()

        new_frame.pack(fill=Tkinter.BOTH)

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
            self.player_name = nickname
            self.show_frame(self.lobby_frame)

            self.lobby_frame.update_games_list(response['sessions'])
            self.server_listener = ServerListener('{0}.sessions.info'.format(self.rpc.server_name),
                                                  self.connection_args, self.lobby_frame.update_games_list)
            # Also start announcing player activity to server
            self.player_announcements = PlayerAnnouncements(self.player_name, self.connection_args)
            self.player_announcements.start()
            return True

    def leave_server(self):
        """
        Leave the server and return to the server_selection_frame

        Returns:
            bool: True if operation was a success
        """
        response = self.rpc.disconnect(user=self.player_name)

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            self.player_name = None
            self.rpc.server_name = None

            self.show_frame(self.server_selection_frame)

            self.server_listener.exit()
            self.server_listener = None
            self.player_announcements.exit()
            self.player_announcements = None

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

        response = self.rpc.create_session(user=self.player_name, sname=game_name, player_count=game_size)

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            self.show_frame(self.game_setup_frame)

            self.game_name = game_name
            self.game_size = game_size
            self.game_setup_frame.join_game(game_size, response['map'], owner=True)
            self.game_listener = GameListener('{0}.{1}.info'.format(self.rpc.server_name, self.game_name),
                                              self.connection_args, self.game_setup_frame.update_players_list)

            self.game_setup_frame.update_players_list(joined=self.player_name)
            self.game_setup_frame.update_players_list(owner=self.player_name)

            return True

    def join_game(self, game_name, game_size):
        """
        Join a game on the server.

        Args:
            game_name (str): Name of the game
            game_size (int): Max number of players

        Returns:
            bool: True if operation was a success, False on error
        """

        response = self.rpc.join_session(user=self.player_name, sname=game_name)

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False

        elif 'battlefield' in response:

            # Lets reconnect to the game

            self.show_frame(self.game_frame)
            self.game_name = game_name
            self.game_size = game_size

            self.game_listener = GameListener('{0}.{1}.info'.format(self.rpc.server_name, self.game_name),
                                              self.connection_args, self.game_frame.update_game_info)

            self.player_listener = PlayerListener('{0}.{1}.{2}'.format(
                    self.rpc.server_name, self.game_name, self.player_name),
                    self.connection_args, self.game_frame.update_player_info)

            players_list = [{'name': player_name} for player_name in response['players_list']]

            self.game_frame.reconnect_game(response['players_list'], response['next'], response['battlefield'], response['map'], self.game_size)

        else:
            self.show_frame(self.game_setup_frame)

            self.game_name = game_name
            self.game_size = game_size
            self.game_setup_frame.join_game(game_size, response['map'])
            self.game_listener = GameListener('{0}.{1}.info'.format(self.rpc.server_name, self.game_name),
                                              self.connection_args, self.game_setup_frame.update_players_list)

            # Update the players list with excisting players
            self.game_setup_frame.update_players_list(joined=self.player_name)
            self.game_setup_frame.update_players_list(joined=response['owner'])
            self.game_setup_frame.update_players_list(owner=response['owner'])
            for player_name in response['players']:
                self.game_setup_frame.update_players_list(joined=player_name)
            for player_name in response['ready']:
                self.game_setup_frame.update_players_list(ready=player_name)

            return True

    def leave_game(self, connected=True):
        """
        Leave the game session.

        Args:
            connected (bool): if not connected, then don't have to ask the server anything.

        Returns:
            bool: True if operation was a success, False on error
        """

        connected = connected and not self.game_frame.game_over

        if connected:
            response = self.rpc.leave_session(user=self.player_name, sname=self.game_name)

        if connected and response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            self.show_frame(self.lobby_frame)

            if self.game_listener is not None:
                self.game_listener.exit()
                self.game_listener = None

            if self.player_listener is not None:
                self.player_listener.exit()
                self.player_listener = None

            self.game_name = None

            return True

    def ship_placement(self, coords):
        """
        Send ship coordinates to the server.

        Args:
            coords (list[(int, int)]):

        Returns:
            bool: True if operation was a success, False on error
        """

        response = self.rpc.send_ship_placement(user=self.player_name, sname=self.game_name, coords=coords)

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            return True

    def ready(self):
        """
        Signal the server that the player is ready.

        Returns:
            bool: True if operation was a success, False on error
        """

        response = self.rpc.ready(user=self.player_name, sname=self.game_name)

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            return True

    def start_game(self):
        """
        Signal the server that the game can start.

        Returns:
            bool: True if operation was a success, False on error
        """

        response = self.rpc.start_game(user=self.player_name, sname=self.game_name)

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            return True

    def begin(self, players_list, next_player, my_ships, map_pieces):
        """
        Begin the actual game.

        Args:
            players_list (list[dict]): List of players
            next_player (str): Player who will start the game
            my_ships (list[tuple]): List of my ships coordinates
            map_pieces (list[int]): List of map pieces that belong to the user.
        """
        self.show_frame(self.game_frame)
        self.game_listener.exit()

        self.game_listener = GameListener('{0}.{1}.info'.format(self.rpc.server_name, self.game_name),
                                          self.connection_args, self.game_frame.update_game_info)

        self.player_listener = PlayerListener('{0}.{1}.{2}'.format(
                self.rpc.server_name, self.game_name, self.player_name),
                self.connection_args, self.game_frame.update_player_info)

        self.game_frame.start_game(players_list, next_player, my_ships, map_pieces, self.game_size)

    def shoot(self, x, y):
        """
        Take a shot

        Args:
            x (int): x-coordinate
            y (int): y-coordinate

        Returns:
            bool: True if operation was a success, False on error
        """

        response = self.rpc.shoot(user=self.player_name, sname=self.game_name, coords=(y, x))

        if response['err']:
            tkMessageBox.showerror('Error', response['err'])
            return False
        else:
            return response['hit']


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

    def toggle_join_button(self, event=None):
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

        try:
            selected_server = self.servers_listbox.get(self.servers_listbox.curselection()[0])
        except IndexError:
            selected_server = None
        except RuntimeError:
            return

        self.servers_listbox.delete(0, Tkinter.END,)
        for i, server in enumerate(servers):
            self.servers_listbox.insert(Tkinter.END, server)

            if server == selected_server:
                self.servers_listbox.select_set(i)

        self.toggle_join_button()


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
        Tkinter.Label(self, text='Players:').grid(row=3, column=0)
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

        # Other varaibles
        self.games_list = []

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

        if game_size < 2 or 6 < game_size:
            tkMessageBox.showerror('Error', 'The number of players must be between 2 and 6.')

        else:
            self.parent.new_game(self.game_name_input.get(), game_size)

    def join_game(self):
        """
        Join an existing game.
        """

        game_name = self.games_listbox.get(self.games_listbox.curselection()[0])
        game_dict = re.match('(?P<name>.*) \(\d+/(?P<size>\d+)\)', game_name).groupdict()

        self.parent.join_game(game_dict['name'].rstrip(), int(game_dict['size']))

    def toggle_join_button(self, event):
        """
        Disable/enable the join_button
        """

        if len(self.games_listbox.curselection()) > 0:
            self.join_game_button.configure(state=Tkinter.NORMAL)
        else:
            self.join_game_button.configure(state=Tkinter.DISABLED)

    def update_games_list(self, games_list):
        """
        Update the list of games on this server.

        Args:
            games_list list[dict[str, object]]:

        """

        new_games_list = []
        for new_game in games_list:
            for game in self.games_list:
                if new_game['session_name'] == game['session_name']:
                    if new_game['player_count'] == 0:
                        # Delete the game
                        break
                    else:
                        new_games_list.append(new_game)
                        break
            else:
                new_games_list.append(new_game)

        self.games_list = new_games_list

        self.games_listbox.delete(0, Tkinter.END)
        for game in self.games_list:
            game_name = '{0:<15} ({1}/{2})'.format(game['session_name'], game['player_count'], game['max_count'])
            self.games_listbox.insert(Tkinter.END, game_name)


class GameSetupFrame(BaseGameFrame):

    def __init__(self, parent):
        """
        Choose the positions for your ships.
        """
        super(GameSetupFrame, self).__init__(parent)

        # Define and position the widgets

        self.start_game_button = Tkinter.Button(self, text="Start game", command=self.start_game)
        self.reset_field_button = Tkinter.Button(self, text="Reset field", command=self.reset_field)

        # Some variables
        self.game_owner = False
        self.game_field = [[]]
        self.next_ships = []
        self.current_ship_size = -1
        self.current_ship_start = None

    def start_game(self):
        """
        Signal the server, that the game can start.
        """
        if self.parent.ship_placement(self.ship_coords):
            if self.parent.start_game():
                self.clear_field()

    def ready(self):
        """
        Signal the server, that player is ready.
        """
        if self.parent.ship_placement(self.ship_coords):
            self.parent.ready()

    def join_game(self, game_size, map_pieces, owner=False):
        """
        Join the game and initialize the field

        Args:
            game_size (int): number of players
            map_pieces (list[int]): Squares available to the player
            owner (bool): Is the player the owner of game?
        """

        self.game_size = game_size
        self.map_pieces = map_pieces
        self.game_owner = owner

        self.ship_coords = []
        self.players_list = []

        self.init_field()

    def init_field(self):
        """
        Initialize the playing field
        """

        super(GameSetupFrame, self).init_field()

        self.next_ships = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]
        self.reset_field_button.grid(row=0, column=SQUARES_IN_A_ROW * (SQUARE_SIDE_LENGTH + SQUARE_BUFFER_SIZE))

        for y in self.ys:
            for x in self.xs:
                if self.can_have_my_ship(x, y):
                    self.game_field[y][x].change_state()

    def clear_field(self):
        """
        Clear the field of all widgets.
        """

        super(GameSetupFrame, self).clear_field()

        self.start_game_button.grid_remove()
        self.next_ships = []
        self.current_ship_size = -1
        self.current_ship_start = None

    def on_click(self, x, y):
        """
        Click event handler for field squares.

        Args:
            x (int): x-coordinate
            y (int): y-coordinate
        """

        if self.current_ship_size == -1:
            # Start adding the ship
            self.current_ship_size = self.next_ships.pop(0)
            self.current_ship_start = x, y

            # Lets turn all to false:
            for widgets in self.game_field:
                for widget in widgets:
                    widget.change_state(False)

            # Where can the ship end?
            # I'l look at the four possible directions

            for direction in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pos = x, y

                for i in range(1, self.current_ship_size):
                    pos = pos[0] + direction[0], pos[1] + direction[1]

                    if not self.can_have_my_ship(*pos):
                        break
                else:
                    self.game_field[y + direction[1]*(self.current_ship_size - 1)][x + direction[0]*(self.current_ship_size - 1)].change_state(True)

            # No need to double click on same square
            if self.current_ship_size == 1:
                self.on_click(x, y)

        else:
            # End adding ship
            x_min, x_max = sorted([x, self.current_ship_start[0]])
            y_min, y_max = sorted([y, self.current_ship_start[1]])

            for row in range(y_min, y_max + 1):
                for col in range(x_min, x_max + 1):
                    self.ship_coords.append((row, col)) # Serveril on x y teisipidi
                    self.game_field[row][col].make_ship()

            for row, widgets in enumerate(self.game_field):
                for col, widget in enumerate(widgets):
                    widget.change_state(self.is_mine(col, row) and self.can_have_ship(col, row))

            self.current_ship_size = -1
            self.current_ship_start = None

            if not self.next_ships:
                self.placing_ships_done()

    def placing_ships_done(self):
        """
        All ships are placed, now player can say hes ready!
        """
        for widgets in self.game_field:
            for widget in widgets:
                widget.change_state(False)

        if self.game_owner:
            self.start_game_button.grid(row=0, column=SQUARES_IN_A_ROW*(SQUARE_SIDE_LENGTH + SQUARE_BUFFER_SIZE))
        else:
            self.ready()

        self.reset_field_button.grid_remove()

    def update_players_list(self, joined=None, owner=None, ready=None, left=None, **kwargs):
        """
        Update the list of players in game

        Args:
            joined (str): players name
            owner (str): players name
            ready (str): players name
            left (str): players name
            **kwargs:
        """

        if joined is not None:
            self.players_list.append({'name': joined, 'ready': False, 'owner': False})

        if owner is not None:
            for player in self.players_list:
                if player['name'] == owner:
                    player['owner'] = True
                else:
                    player['owner'] = False

        if ready is not None:
            for player in self.players_list:
                if player['name'] == ready:
                    player['ready'] = True
                    break

        if left is not None:
            self.players_list = [player for player in self.players_list if player['name'] != left]

        if kwargs.get('active', False):
            # Start playing the actual game.
            self.parent.begin(players_list=self.players_list, next_player=kwargs['next'], my_ships=self.ship_coords,
                              map_pieces=self.map_pieces)

            return

        # Edit the actual listbox

        self.players_listbox.delete(0, Tkinter.END)
        for player in self.players_list:
            player_name = player['name']

            if player['owner']:
                player_name += ' (owner)'

            if player['ready']:
                player_name += ' (ready)'

            self.players_listbox.insert(Tkinter.END, player_name)


class GameFrame(BaseGameFrame):

    def __init__(self, parent):
        """
        Play the game.
        """
        super(GameFrame, self).__init__(parent)

        self.my_turn = False

        # Define and position the widgets

        self.messages_listbox = Tkinter.Listbox(self, selectmode=Tkinter.SINGLE, width=50)
        self.messages_listbox.grid(row=1, column=SQUARES_IN_A_ROW * (SQUARE_SIDE_LENGTH + SQUARE_BUFFER_SIZE) + 1,
                                   rowspan=10, sticky=Tkinter.N)

    def start_game(self, players_list, next_player, my_ships, map_pieces, game_size):
        """
        Start playing the game.

        Args:
            players_list (list[dict]): List of players
            next_player (str): Name of the next player
            my_ships (list[tuple]): List of ship coordinates
            map_pieces (list[int]): List of indices of map pieces, that belong to the user
            game_size (int): Max number of players

        Returns:

        """

        self.ship_coords = my_ships
        self.game_size = game_size
        self.map_pieces = map_pieces
        self.players_list = [{'name': player['name'], 'next': next_player == player['name'], 'gameover': False}
                             for player in players_list]

        self.init_field()
        if next_player == self.parent.player_name:
            self.start_turn()

        self.update_players_list()

    def reconnect_game(self, player_list, next_player, battlefield, map_pieces, game_size):
        """
        Reconnect after becoming inactive. Restores the playing field. (a mess)
        """

        self.players_list = [{'name': player_name, 'next': next_player == player_name, 'gameover': False}
                             for player_name in player_list]

        self.game_size = game_size
        self.map_pieces = map_pieces

        self.ship_coords = []
        for x in self.xs:
            for y in self.ys:
                if battlefield[y][x] in (1, 2) and self.can_have_my_ship(x, y):
                    self.ship_coords.append((y, x))

        self.init_field()
        if next_player == self.parent.player_name:
            self.start_turn()

        self.update_players_list()

        for x in self.xs:
            for y in self.ys:

                if battlefield[y][x] in (1, 2):
                    self.game_field[y][x].make_ship()

                if abs(battlefield[y][x]) == 1:
                    self.game_field[y][x].hit()

    def start_turn(self):
        """
        Make the field active and start the turn.
        """

        self.my_turn = True

        for y in self.ys:
            for x in self.xs:
                if not self.is_mine(x, y):
                    self.game_field[y][x].change_state()

    def end_turn(self):
        """
        End the players turn
        """

        self.my_turn = False

        for y in self.ys:
            for x in self.xs:
                if not self.is_mine(x, y):
                    self.game_field[y][x].change_state(active=False)

    def on_click(self, x, y):
        """
        Click event handler for field squares.

        Args:
            x (int): x-coordinate
            y (int): y-coordinate
        """

        if self.parent.shoot(x, y):
            self.game_field[y][x].make_ship()

    def update_game_info(self, next=None, shot=None, sunk=None, gameover=None,
                         active=None, msg=None,  owner=None, left=None, **kwargs):
        """
        Updates based on information sent to everybody.

        Args:
            next (str): Next players name
            shot (tuple): coordinates of shot
            sunk (list[(int, int)]): list of coordinates of sunken ship
            gameover (str): Player who lost
            active (bool): False if game is over
            **kwargs:
        """

        if next is not None:
            if next == self.parent.player_name and self.my_turn:
                pass # I made a successfull hit

            elif next == self.parent.player_name:
                self.start_turn()

            elif self.my_turn:
                self.end_turn()

        if shot is not None:
            self.game_field[shot[0]][shot[1]].hit()

        if sunk is not None:
            for y, x in sunk:
                self.game_field[y][x].sunk()

        if gameover is not None:
            for player in self.players_list:
                if player['name'] == gameover:
                    player['gameover'] = True

        if active is not None:
            # Game has ended
            self.game_over = True
            self.end_turn()

        if msg is not None:
            self.add_message(msg)

        if owner is not None:
            for player in self.players_list:
                if player['name'] == owner:
                    player['owner'] = True
                else:
                    player['owner'] = False

        if left is not None:
            self.players_list = [player for player in self.players_list if player['name'] != left]

        self.update_players_list()

    def update_player_info(self, spec_field=None, msg=None, **kwargs):
        """
        Updates that are directed to single player

        Args:
            spec_field (list[list[int]]): info about all the positions
                -1 - water, with a hit
                0 - water
                1 - ship, hit
                2 - ship
            **kwargs:
        """

        if spec_field is not None:
            for x in self.xs:
                for y in self.ys:

                    if spec_field[y][x] in (1, 2):
                        self.game_field[y][x].make_ship()

                    if spec_field[y][x] == 1:
                        self.game_field[y][x].hit()

        if msg is not None:
            self.add_message(msg)

    def update_players_list(self):
        """
        Update the list of players
        """

        self.players_listbox.delete(0, Tkinter.END)
        for player in self.players_list:
            player_name = player['name']

            if player['next']:
                player_name += ' (shooting)'

            if player['gameover']:
                player_name += ' (game over)'

            self.players_listbox.insert(Tkinter.END, player_name)

    def add_message(self, msg):
        """
        Add message to self.message_listbox

        Args:
            msg (str): message froms erver
        """

        self.messages_listbox.insert(0, msg)
