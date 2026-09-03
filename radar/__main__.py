import sys

from .collectors import open_login_session
from .pipeline import run

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "login":
        open_login_session()
    else:
        run()
