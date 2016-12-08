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
        self.map_size = [5*max_players, 20]
        self.map_pieces = divide_map_pieces(max_players, 4)
        self.map_pieces_assigned = [owner] + [None]*(max_players-1)

        #TODO add additional variables - ship placement info

        # add game session to dictionary for easy access
        #SESSIONS[session_name] = self

    def info(self):
        dict_info = {'session_name':self.session_name,
                     'owner': self.owner,
                     'in_game': self.in_game,
                     'player_count': len(self.players),
                     'max_count': self.max_players}
        return dict_info

    def check_shot(self):
        # check whether hit/miss, did ship sink or not
        # if hit, also return who was hit
        # if ship sunk, check end_game
        pass

    def end_game(self):
        pass

    def assign_pieces(self, user_name):
        pass

    def place_ships(self):
        pass


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
