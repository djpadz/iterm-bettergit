from iterm2 import run_forever

from bettergit.main import main as a_main

run_forever(a_main, retry=True)
