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
        self.map_size = [5*max_players, 20]
        self.map_pieces = divide_map_pieces(max_players, 4)
        self.map_pieces_assigned = [owner] + [None]*(max_players-1)
        self.ship_placement = [x[:] for x in [[0] * 20] * max_players*5]  # init ship placement matrix

        # TODO add additional variables - ship placement info -
        # where the ships are (0, 1, 2) 2 for healthy ship part,
        # 1 for hit ship and 0 for empty spot, should server take also into account what spot is shot?
        # So if player reconnects he can get the info about what spot is shot already. -1 for shot empty spot

    def info(self):
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
        idx = self.map_pieces_assigned.index(None)
        map = []
        if idx != -1:
            self.map_pieces_assigned[idx] = user_name
            map = self.map_pieces[idx]

        return map

    def unassign_pieces(self, user_name):
        idx = self.map_pieces_assigned.index(user_name)

        if idx != -1:
            self.map_pieces_assigned[idx] = None

    def check_ready(self, owner):
        # check if all players in players list, except owner are also ready to start
        # TODO what about owner ships?
        for player in self.players:
            if player != owner and player not in self.players_ready:
                return False

        return True

    def place_ships(self, user_name, coords):
        ship_map = self.ship_placement
        idx = self.map_pieces_assigned.index(user_name)

        if idx == -1:
            return "User %s have no pieces assigned to" % user_name

        pieces = self.map_pieces[idx]

        print ship_map

        # clear player assigned map pieces
        for p in pieces:  # piece 0 - 0..4, 5..9, 10..14, 15..19
            column_start = p % 4 * 5  # 4 pieces in row, 5 elements in piece
            row_start = p // 4 * 5  # divided by 4 pieces in row

            for i in range(column_start, column_start+5):  # 5 elements in piece
                for j in range(row_start, row_start+5):
                    ship_map[j][i] = 0

        # TODO test if cleaned properly

        print ship_map

        for coord in coords:
            ship_map[coord[0]][coord[1]] = 2

        # TODO check if ship placement is valid - are right ships assigned, are ships placed right way,
        # TODO are ships in right map pieces

        print ship_map

        self.ship_placement = ship_map

        return ""


# divide map pieces based on number of players (each player have 4 pieces of map)
def divide_map_pieces(number_of_players, pieces_per_player):
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
