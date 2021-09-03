import sys
from pprint import pprint

from krefia.allegro_client import login_tijdelijk

bsn = sys.argv[1]


response = login_tijdelijk()

pprint(response)
