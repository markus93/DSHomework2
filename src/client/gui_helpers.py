import Tkinter


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


class GameSquare(Tkinter.Button, object):

    def __init__(self, parent, owner, mode, command=None):
        """

        Args:
            parent: Parent widget
            owner (bool): True if you are owner, false otherwise
            mode (int): 0 - Setup, 1 - in game waiting, 2 - in game moving
            command (func): on_click handler
        """
        super(GameSquare, self).__init__(parent, height=1, width=1, command=command)

        self.owner = owner

        # Setup mode
        if mode == 0:

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
