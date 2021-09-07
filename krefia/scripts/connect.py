import sys
from pprint import pprint

from krefia.allegro_client import (
    get_relatienummer,
    get_relatienummer_bedrijf,
    login_tijdelijk,
)

bsn = None
if len(sys.argv) >= 2:
    bsn = sys.argv[1]

response = login_tijdelijk()

response = get_relatienummer_bedrijf(bsn)
pprint(response)

# response = get_relatienummer(bsn)
# pprint(response)

# relatienummer = None
# response = get_relatienummer(relatienummer)
# pprint(response)
