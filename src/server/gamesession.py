# Contains game sessions and game logic

# Import
import random


class GameSession:

    def __init__(self, session_name, max_players, owner):

        self.session_name = session_name
        self.max_players = max_players
        self.owner = owner
        self.in_game = False
        self.players = [owner]
        self.players_ready = []  # can't start before all players ready (owner doesn't matter)
        self.map_size = [(6*max_players - 1), (20+3)]  # players-1 buffer rows,
        # 3 buffer columns between pieces
        self.map_pieces = divide_map_pieces(max_players, 4)
        self.map_pieces_assigned = [owner] + [None]*(max_players-1)
        self.ship_placement = [x[:] for x in [[0] * (20+3)] * (max_players*6-1)]  # init ship placement matrix
        # 5 lines for each player + 1 for buffer between player pieces
        self.ships_placed = []
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

    def check_shot(self):
        # check whether hit/miss, did ship sink or not
        # if hit, also return who was hit
        # if ship sunk, check end_game
        pass

    def end_game(self):
        pass

    def assign_pieces(self, user_name):
        """
        Assign map pieces to player (user), where he/she can place ships.

        Args:
            user_name (str): Name of the player (user)

        Returns:
            list[int]: map pieces assigned to player
        """

        idx = self.map_pieces_assigned.index(None)
        map_pieces = []
        if idx != -1:
            self.map_pieces_assigned[idx] = user_name
            map_pieces = self.map_pieces[idx]

        return map_pieces

    def unassign_pieces(self, user_name):
        idx = self.map_pieces_assigned.index(user_name)

        if idx != -1:
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

        ship_map = self.ship_placement

        # Add ships to map
        for coord in coords:
            ship_map[coord[0]][coord[1]] = 2

        # TODO check if ship placement is valid - are right ships assigned, are ships placed right way,
        # TODO are ships in right map pieces

        print ship_map

        self.ship_placement = ship_map

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

        ship_map = self.ship_placement
        idx = self.map_pieces_assigned.index(user_name)

        if idx == -1:
            return "User %s have no pieces assigned to" % user_name

        pieces = self.map_pieces[idx]

        # clear player assigned map pieces
        for p in pieces:  # piece 0 - 0..4, 6..10, 12..16, 18..22
            column_start = p % 4 * 6  # 4 pieces in row, 5 elements + 1 in piece (1 buffer element)
            row_start = p // 4 * 6  # divided by 4 pieces in row

            for i in range(column_start, column_start+5):  # 5 elements in piece
                for j in range(row_start, row_start+5):
                    ship_map[j][i] = 0

        self.ship_placement = ship_map

        return ""

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
