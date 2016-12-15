# Contains game sessions and game logic

# Import
import random


class GameSession:

    def __init__(self, session_name, max_players, owner):

        self.session_name = session_name  # name of game session
        self.max_players = max_players  # maximum count of players
        self.owner = owner  # owner of given session (can start game)
        self.in_game = False  # is game currently on going or in lobby
        self.players = [owner]  # players joined in session
        self.players_ready = []  # can't start before all players ready (owner doesn't matter)
        # self.map_size = [(6*max_players - 1), (20+3)]  # players-1 buffer rows,
        # 3 buffer columns between pieces
        self.map_pieces = divide_map_pieces(max_players, 4)  # map pieces divided into 4 (each player 4 random squares)
        self.map_pieces_assigned = [owner] + [None]*(max_players-1)  # which map piece is assigned to who (add to dict?)
        self.battlefield = [x[:] for x in [[0] * (20 + 3)] * (max_players * 6 - 1)]  # init ship placement matrix
        # 5 lines for each player + 1 for buffer between player pieces
        self.ships_placed = []  # players who have placed ships, needed in order to start game
        self.next_shot_by = owner  # player who is shooting atm (or going to)
        self.players_active = []  # name of players who are communicating actively with server
        self.players_alive = []  # player names that still have ships left
        # where the ships are (-1, 0, 1, 2) 2 for healthy ship part,
        # 1 for hit ship and 0 for empty spot, should server take also into account what spot is shot?
        # So if player reconnects he can get the info about what spot is shot already. -1 for shot empty spot

    def info(self):
        """
        Gives back dictionary containing game session info

        Returns:
            dict[str, object]: dictionary containing game session info
        """
        dict_info = {'session_name': self.session_name,
                     'owner': self.owner,
                     'in_game': self.in_game,
                     'player_count': len(self.players),
                     'max_count': self.max_players,
                     'ready': self.players_ready,
                     'map': self.map_pieces_assigned}
        return dict_info

    def check_shot(self, coords):
        """
        checks whether given square was a hit

        Args:
            coords ([int,int]): coordinates of hit point
        Returns:
            int: 0 - miss, 1 - hit, 2 - hit and sunk
        """
        x = coords[0]
        y = coords[1]

        result = self.battlefield[x][y]

        if result == 0:  # no ship, not shot
            self.battlefield[x][y] = -1
            return 0
        elif result == 2:  # ship, not shot
            self.battlefield[x][y] = 1
            if self.check_ship_sunk(x, y):
                return 2
            else:
                return 1
        else:
            print("Square [%d,%d] was already shot" % (x, y))
            return 0  # miss, however spot was already shot

    def check_end_game(self):
        """
        Checks who are still in game, if only one player then game over.

        Returns:
            str: player name if some one just lost a game, else None
        """

        max_x = len(self.battlefield)
        max_y = len(self.battlefield[0])

        list_players_left = []

        for x in range(0, max_x):
            for y in range(0, max_y):
                if self.battlefield[x][y] == 2:
                    owner = self.get_ship_owner([x, y])
                    if owner not in list_players_left:
                        list_players_left.append(owner)

        if list_players_left != len(self.players_alive):
            for player in self.players_alive:
                if player not in list_players_left:  # in this case all of player's ships have been destroyed
                    self.players_alive.remove(player)
                    return player
        else:
            return None

    def check_ship_sunk(self, x, y):
        # check whether ship is sunk or not

        ship_coords = self.get_ship_coordinates([x, y])

        for coords in ship_coords:
            value = self.battlefield[coords[0]][coords[1]]
            if value == 2:
                return False  # at least one part of ship is unbroken

        # All ship parts been shot at
        return True

    def get_next_player(self):
        """
        Returns Next player who can shoot
        Returns:
            str: name of player, who is next
        """

        current = self.next_shot_by

        for i in range(1, len(self.players)+1):

            if current in self.players:

                next_idx = self.players.index(current) + i
                next_p = self.players[next_idx % len(self.players)]
            else:
                next_p = self.players[0]

            if next_p in self.players_active and next_p in self.players_alive:
                self.next_shot_by = next_p
                return next_p

        return current

    def get_ship_coordinates(self, coords):
        """
        Gets all coordinates of given ship, atm not checked whether given coordinate has ship.

        Args:
            coords:
        Returns:
            list[[int,int]]: list of coordinates containing ship coordinates
        """

        field_length_x = self.max_players * 6 - 1
        field_length_y = 20 + 3
        x = coords[0]
        y = coords[1]


        ship_coords = [coords]

        for i in range(1, 5):  # max length of ship is 5 (each square is 5X5)
            if (y - i) >= 0:  # check up
                spot_info = self.battlefield[x][y - i]
                if spot_info == 2 or spot_info == 1:
                    ship_coords.append([x, y-i])
                else:
                    break
            else:
                break

        for i in range(1, 4):  # max length of ship is 4
            if (y + i) < field_length_y:  # check down (y must be smaller than field width)
                spot_info = self.battlefield[x][y + i]
                if spot_info == 2 or spot_info == 1:
                    ship_coords.append([x, y+i])
                else:
                    break
            else:
                break

        for i in range(1, 4):  # max length of ship is 4
            if (x - i) >= 0:  # check left
                spot_info = self.battlefield[x - i][y]
                if spot_info == 2 or spot_info == 1:
                    ship_coords.append([x-i, y])
                else:
                    break
            else:
                break

        for i in range(1, 4):  # max length of ship is 4
            if (x + i) < field_length_x:  # check right (x must be smaller than field height)
                spot_info = self.battlefield[x + i][y]
                if spot_info == 2 or spot_info == 1:
                    ship_coords.append([x+i, y])
                else:
                    break
            else:
                break

        return ship_coords  # if no 2-s found around ship, then ship is sunk

    def assign_pieces(self, user_name):
        """
        Assign map pieces to player (user), where he/she can place ships.

        Args:
            user_name (str): Name of the player (user)

        Returns:
            list[int]: map pieces assigned to player
        """
        if None in self.map_pieces_assigned:
            idx = self.map_pieces_assigned.index(None)
            self.map_pieces_assigned[idx] = user_name
            return self.map_pieces[idx]
        else:
            return []

    def unassign_pieces(self, user_name):

        if user_name in self.map_pieces_assigned:
            idx = self.map_pieces_assigned.index(user_name)
            self.map_pieces_assigned[idx] = None

    def check_ready(self, owner):
        """
        check if all players have placed ships and are ready to start, should be called by owner

        Args:
            owner (str): owner of the game session
        Returns:
            bool: True if all players are ready, False otherwise
        """
        for player in self.players:
            if player not in self.ships_placed:
                return False
            elif player != owner and player not in self.players_ready:
                return False

        return True

    def place_ships(self, user_name, coords):
        """
        Place ships to given coordinates. Coordinates should contain all squares that ships fill

        Args:
            user_name (str): name of the player
            coords (list[list[int]]: x and y coordinates of all ships
        Returns:
            str: error messages
        """

        err = self.remove_ships(user_name)  # clean old ship placement

        if err != "":
            return err

        ship_map = self.battlefield

        # Add ships to map
        for coord in coords:
            ship_map[coord[0]][coord[1]] = 2

        self.battlefield = ship_map

        if user_name not in self.ships_placed:
            self.ships_placed.append(user_name)

        return ""

    def remove_ships(self, user_name):
        """
        Remove ships of given player

        Args:
            user_name (str): name of the player
        Returns:
            str: error messages
        """

        ship_map = self.battlefield

        if user_name in self.map_pieces_assigned:
            idx = self.map_pieces_assigned.index(user_name)
        else:
            return "No pieces of map are assigned to user %s" % user_name

        pieces = self.map_pieces[idx]

        # clear player assigned map pieces
        for p in pieces:  # piece 0 - 0..4, 6..10, 12..16, 18..22
            column_start = p % 4 * 6  # 4 pieces in row, 5 elements + 1 in piece (1 buffer element)
            row_start = p // 4 * 6  # divided by 4 pieces in row

            for i in range(column_start, column_start+5):  # 5 elements in piece
                for j in range(row_start, row_start+5):
                    ship_map[j][i] = 0

        self.battlefield = ship_map

        return ""

    def get_ship_owner(self, coords):
        """
        returns to who given square belongs to (does not have to have ship on it necessarily)

        Args:
            coords ([int,int]): coordinates of hit point
        Returns:
            str: player name, to who this square belongs to
        """
        x = coords[0]
        y = coords[1]

        piece_nr = self.get_piece_nr(x,y)

        owner_of_square = None

        for pieces in self.map_pieces:
            if piece_nr in pieces:
                idx = self.map_pieces.index(pieces)
                owner_of_square = self.map_pieces_assigned[idx]

        if owner_of_square is None:
            print("ERR: Piece is not assigned to anyone!!")

        return owner_of_square

    def clean_player_info(self, user_name):
        """
        Removes all player info from server. Player ship placement, ready status, player from players list, unassign
        map pieces from player (so other player could get them)

        Args:
            user_name (str): Name of player (user)
        """

        self.remove_ships(user_name)  # remove also player added ships
        self.players.remove(user_name)
        self.unassign_pieces(user_name)

        if user_name in self.players_ready:
            self.players_ready.remove(user_name)
        if user_name in self.ships_placed:
            self.ships_placed.remove(user_name)
        if user_name in self.players_active:
            self.players_active.remove(user_name)
        if user_name in self.players_alive:
            self.players_alive.remove(user_name)

    def get_map_pieces(self, user_name):
        """
        Gets map pieces assigned to given player

        Args:
            user_name (str): Name of player (user)
        Returns:
             list[int]: containing indexes of player map pieces
        """

        if user_name in self.map_pieces_assigned:
            idx = self.map_pieces_assigned.index(user_name)
            return self.map_pieces[idx]
        else:
            return []

    def start_game(self):
        self.in_game = True
        self.players_alive = self.players[:]
        self.players_active = self.players[:]

    def reset_session(self):
        """
        Resets ship placement, battlefield and in game info
        """
        self.in_game = False
        self.players_ready = []
        self.battlefield = [x[:] for x in [[0] * (20 + 3)] * (self.max_players * 6 - 1)]
        self.ships_placed = []
        self.next_shot_by = self.owner
        self.players = self.players_active[:]
        self.players_active = []
        self.players_alive = []

    def get_player_battlefield(self, user_name):
        """
        Gives back battlefield showing only user ships and coordinates that are already shot

        Args:
            user_name (str) : Name of player (user)
        Returns:
             list[list[int]]: matrix of battlefield, meant for reconnecting user
        """

        map_pieces = self.get_map_pieces(user_name)
        player_battlefield = [x[:] for x in [[]] * (self.max_players * 6 - 1)]

        # go through battlefield, replace 1 with -1 and 2 with 0 only if they are not on player piece
        for x in range(0, len(self.battlefield)):
            for y in range(0, len(self.battlefield[0])):
                piece_nr = self.get_piece_nr(x, y)
                if piece_nr in map_pieces:  # player map piece, can show ships and stuff
                    player_battlefield[x].append(self.battlefield[x][y])
                else:  # opponents map pieces, hide ships and hits
                    value = self.battlefield[x][y]
                    if value == 1:
                        value = -1
                    elif value == 2:
                        value = 0

                    player_battlefield[x].append(value)

        return player_battlefield

    @staticmethod
    def get_piece_nr(x, y):
        """
        Gets map piece number to which given coordinate belongs to

        Args:
            x (int): x coordinate of battlefield (row number)
            y (int): y coordinate of battlefield (column number)
        Returns:
            int: Number to which map piece given coordinate belongs to
        """

        # get which piece from row, 0th, 1st, 2nd, 3rd
        piece_nr_row = y // 6  # divided by 6 because each piece have 6 squares (except last)
        # get on which column player assigned piece is (6 squares per piece)
        piece_nr_column = x // 6

        piece_nr = piece_nr_column * 4 + piece_nr_row  # every column has 4 pieces (column nr start from zero)
        # and then added piece number of row

        return piece_nr


def divide_map_pieces(number_of_players, pieces_per_player):
    """
    divide map pieces based on number of players (each player have 4 pieces of map)

    Args:
        number_of_players (int): how many players are going to be in game
        pieces_per_player (int): how many pieces player is going to have
    Returns:
        list[list[int]]: list of lists containing map pieces
    """

    number_of_pieces = number_of_players*pieces_per_player
    list_pieces = range(0, number_of_pieces)
    divided_pieces = []

    for i in range(0, number_of_players):
        temp_list = []
        for j in range(0, 4):
            piece = random.choice(list_pieces)
            list_pieces.remove(piece)
            temp_list.append(piece)

        divided_pieces.append(temp_list)

    return divided_pieces
