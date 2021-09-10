from krefia import config
import sys
from pprint import pprint

from krefia.allegro_client import (
    get_all,
)

bsn = None
if len(sys.argv) >= 2:
    bsn = sys.argv[1]

config.set_debug(True)

get_all(bsn)
