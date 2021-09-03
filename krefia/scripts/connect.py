import sys
from pprint import pprint

from krefia.allegro_client import get_relatienummer

bsn = sys.argv[1]


get_relatienummer(bsn)
