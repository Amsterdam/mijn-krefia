import sys
from pprint import pprint

from krefia.allegro_client import (
    get_relatienummer,
    get_relatienummer_bedrijf,
    login_allowed,
    login_tijdelijk,
    get_schuldhulp_aanvragen,
)

bsn = None
if len(sys.argv) >= 2:
    bsn = sys.argv[1]

response = login_tijdelijk()

response = get_relatienummer_bedrijf(bsn)
pprint(response)

# response = get_relatienummer(bsn)
# pprint(response)
print("\n\n-----\n\n")
relatiecode = response["body"]["Result"]["TRelatiecodeBedrijfcode"][0]["Relatiecode"]
response = login_allowed(relatiecode)
pprint(response)
print("\n\n-----\n\n")
response = get_relatienummer(relatiecode)
pprint(response)
