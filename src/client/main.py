# Main client methods

# Import------------------------------------------------------------------------
from gui import RootWindow

# Info-------------------------------------------------------------------------

___NAME = 'Battleship Client'
___VER = '0.0.0.1'
___DESC = 'Multiplayer battleship game client using indirect connection and RPC'
___BUILT = '2016-12-14'
___VENDOR = 'Copyright (c) 2016 DSLab'

# Variables


def __info():
    return '%s version %s (%s) %s' % (___NAME, ___VER, ___BUILT, ___VENDOR)


def client_main(args):

    root = RootWindow(args)
    root.mainloop()


