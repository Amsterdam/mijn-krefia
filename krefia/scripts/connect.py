import sys
from pprint import pprint

from krefia.allegro_client import get_relatienummer, login_tijdelijk

bsn = None
if len(sys.argv) >= 2:
    bsn = sys.argv[1]

if bsn:
    response = get_relatienummer(bsn)
else:
    response = login_tijdelijk()

pprint(response)
