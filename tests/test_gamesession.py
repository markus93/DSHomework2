# Test game session class methods

from unittest import TestCase
from server.gamesession import *


class GameSessionTests(TestCase):

    def setUp(self):
        self.owner = "owner"
        self.player = "p1"
        self.max_players = 2
        self.session_name = "sess"
        self.sess = GameSession(self.session_name, self.max_players, self.owner)
        self.sess.players.append(self.player)
        self.sess.map_pieces = [[0,1,2,3], [4,5,6,7]]  # owner has pieces 0,1,2,3 for simplicity

    def test_getting_ready(self):
        # test check_ready method - whether returns true in correct conditions
        self.sess.assign_pieces(self.player)

        print("Testing getting ready")

        coords = [[0, 0], [0, 1], [0, 2], [0, 3], [2, 7], [3, 7], [4, 0], [4, 4]]
        coords2 = [[6, 0], [6, 1], [6, 2], [6, 3], [8, 7], [9, 7]]

        self.sess.place_ships(self.player, coords2)

        rsp = self.sess.check_ready(self.owner)
        self.assertFalse(rsp)

        self.sess.players_ready = self.player

        rsp = self.sess.check_ready(self.owner)
        self.assertFalse(rsp)

        self.sess.place_ships(self.owner, coords)

        rsp = self.sess.check_ready(self.owner)
        self.assertTrue(rsp)

    def test_ship_ownership(self):
        # test whether right owner is returned

        print("Testing ship ownership")
        self.sess.assign_pieces(self.player)
        coords2 = [[6, 0], [6, 1], [6, 2], [6, 3], [8, 7], [9, 7]]
        self.sess.place_ships(self.player, coords2)

        owner = self.sess.get_ship_owner([6,0])

        self.assertEqual(owner, self.player)

    def test_get_ship_coordinates(self):
        # test whether returns correct ship coordinates

        print("Testing ship ownership")
        self.sess.assign_pieces(self.player)
        coords2 = [[6, 0], [6, 1], [6, 2], [6, 3], [8, 7], [9, 7]]
        self.sess.place_ships(self.player, coords2)

        coords = self.sess.get_ship_coordinates([6, 0])
        self.assertEqual(coords, [[6, 0], [6, 1], [6, 2], [6, 3]])

        coords = self.sess.get_ship_coordinates([8, 7])
        self.assertEqual(coords, [[8, 7], [9, 7]])

    def test_shooting(self):
        # test whether shot is handled correctly, tests also ship_sunk method

        print("Testing shooting")

        self.sess.assign_pieces(self.player)
        coords2 = [[6, 0], [6, 1], [6, 2], [6, 3], [8, 7], [9, 7]]
        self.sess.place_ships(self.player, coords2)

        res = self.sess.check_shot([5, 0])
        self.assertEqual(0, res)

        res = self.sess.check_shot([8, 7])
        self.assertEqual(1, res)

        res = self.sess.check_shot([9, 7])
        self.assertEqual(2, res)

    def test_end_game(self):
        # test whether end game returns player who have no ships left

        print("Testing end game")

        self.sess.assign_pieces(self.player)
        coords2 = [[8, 7]]
        self.sess.place_ships(self.player, coords2)
        self.sess.place_ships(self.owner, [])

        self.sess.start_game()  # start game in order to activate game

        rsp = self.sess.check_end_game()
        self.assertEqual(rsp, self.owner)

        rsp = self.sess.check_end_game()
        self.assertEqual(rsp, None)

        self.sess.check_shot([8, 7])

        rsp = self.sess.check_end_game()
        self.assertEqual(rsp, self.player)

    def test_get_next_player(self):
        # test whether selecting next player works as intended

        print("Testing getting next player")
        self.sess.start_game()

        current = self.sess.next_shot_by
        self.assertEqual(current, self.owner)

        next = self.sess.get_next_player()
        self.assertEqual(next, self.player)

        next = self.sess.get_next_player()
        self.assertEqual(next, self.owner)

        self.sess.players_active.remove(self.player)
        next = self.sess.get_next_player()
        self.assertEqual(next, self.owner)

        self.sess.players_active.append(self.player)
        self.sess.players_alive.remove(self.player)
        next = self.sess.get_next_player()
        self.assertEqual(next, self.owner)

    def test_get_player_battlefield(self):

        self.sess.assign_pieces(self.player)

        print("Testing getting player battlefield.")

        coords = [[0, 0], [0, 1], [0, 2], [0, 3], [2, 7], [3, 7], [4, 0], [4, 4]]
        coords2 = [[6, 0], [6, 1], [6, 2], [6, 3], [8, 7], [9, 7]]

        self.sess.place_ships(self.owner, coords)
        self.sess.place_ships(self.player, coords2)

        # shots on owner field
        self.sess.check_shot([4, 1])
        self.sess.check_shot([0, 1])
        # shots on player field
        self.sess.check_shot([8, 7])
        self.sess.check_shot([9, 7])

        player_field = self.sess.get_player_battlefield(self.owner)

        test_field = [[2, 1, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [2, -1, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]

        self.assertEqual(player_field, test_field)
