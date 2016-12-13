import Tkinter

SQUARE_SIDE_LENGTH = 5
SQUARE_BUFFER_SIZE = 1
SQUARES_IN_A_ROW = 4


class ValidatingEntry(Tkinter.Entry):
    """
    code taken from http://effbot.org/zone/tkinter-entry-validate.htm
    """

    # base class for validating entry widgets

    def __init__(self, master, value="", **kw):
        apply(Tkinter.Entry.__init__, (self, master), kw)
        self.__value = value
        self.__variable = Tkinter.StringVar()
        self.__variable.set(value)
        self.__variable.trace("w", self.__callback)
        self.config(textvariable=self.__variable)

    def __callback(self, *dummy):
        value = self.__variable.get()
        newvalue = self.validate(value)
        if newvalue is None:
            self.__variable.set(self.__value)
        elif newvalue != value:
            self.__value = newvalue
            self.__variable.set(self.newvalue)
        else:
            self.__value = value

    def validate(self, value):
        # override: return value, new value, or None if invalid
        return value


class IntegerEntry(ValidatingEntry):
    """
    Code taken from http://effbot.org/zone/tkinter-entry-validate.htm
    """

    def validate(self, value):
        try:
            if value:
                v = int(value)
            return value
        except ValueError:
            return None


class BaseGameFrame(Tkinter.Frame, object):

    def __init__(self, parent):
        """
        Baseclass for game frames (setup and actual playing).
        """
        super(BaseGameFrame, self).__init__(parent)
        self.parent = parent

        self.game_field = []
        self.ship_coords = []
        self.map_pieces = []
        self.game_size = None

    def leave_game(self):
        """
        Leave the game session and clear the field.
        """

        self.parent.leave_game()

        self.game_size = None
        self.map_pieces = []

        self.clear_field()

    def init_field(self):
        """
        Initialize the playing field
        """

        self.game_field = []
        for y in range(self.game_size * SQUARE_SIDE_LENGTH + (self.game_size - 1) * SQUARE_BUFFER_SIZE):
            game_field_row = []

            for x in range(SQUARES_IN_A_ROW * SQUARE_SIDE_LENGTH + (SQUARES_IN_A_ROW - 1) * SQUARE_BUFFER_SIZE):

                game_field_row.append(GameSquare(self,
                                                 owner=self.is_mine(x, y),
                                                 command=lambda x_=x, y_=y: self.on_click(x_, y_)))

                if (y, x) in self.ship_coords:
                    game_field_row[-1].make_ship()
                else:
                    game_field_row[-1].make_water()

                game_field_row[-1].grid(row=y+1, column=x)

            self.game_field.append(game_field_row)

    def clear_field(self):
        """
        Clear the field of all widgets.
        """

        for widgets in self.game_field:
            for widget in widgets:
                widget.grid_remove()
                widget.destroy()

        self.game_field = [[]]
        self.ship_coords = []

    def reset_field(self):
        """
        Clear the field and the initialize it again.
        """

        self.clear_field()
        self.init_field()

    def on_click(self, x, y):
        """
        Override this
        """
        pass

    def can_have_my_ship(self, x, y):
        return not self.is_buffer(x, y) and self.is_mine(x, y) and self.can_have_ship(x, y)

    def can_have_enemy_ship(self, x, y):
        return not self.is_buffer(x, y) and not self.is_mine(x, y) and self.can_have_ship(x, y)

    def can_have_ship(self, x, y):
        return not any(abs(x-xs) <= 1 and abs(y-ys) <= 1 for ys, xs in self.ship_coords)

    def is_mine(self, x, y):
        return self.square_n(x, y) in self.map_pieces and not self.is_buffer(x, y)

    @classmethod
    def square_n(cls, x, y):
        return cls.square_cord(x) + SQUARES_IN_A_ROW*cls.square_cord(y)

    @staticmethod
    def square_cord(x):
        return x // (SQUARE_SIDE_LENGTH + SQUARE_BUFFER_SIZE)

    @staticmethod
    def is_buffer(x, y):
        return x % (SQUARE_SIDE_LENGTH + SQUARE_BUFFER_SIZE) >= SQUARE_SIDE_LENGTH or \
               y % (SQUARE_SIDE_LENGTH + SQUARE_BUFFER_SIZE) >= SQUARE_SIDE_LENGTH


class GameSquare(Tkinter.Button, object):

    def __init__(self, parent, owner, command=None):
        """

        Args:
            parent: Parent widget
            owner (bool): True if you are owner, false otherwise
            command (func): on_click handler
        """
        super(GameSquare, self).__init__(parent, height=1, width=1, command=command)

        self.owner = owner

        self.make_water()

    def make_water(self):
        """
        Turn the square into water
        """

        self.configure(bg='blue' if self.owner else 'blue4')
        self.change_state(self.owner)

    def make_ship(self):
        """
        Turn the square into ship
        """

        self.change_state(False)
        self.configure(bg='green2' if self.owner else 'red2')

    def change_state(self, active=True):
        self.configure(state=Tkinter.NORMAL if active else Tkinter.DISABLED)
        self.config(highlightbackground='alice blue' if active else 'blue')
