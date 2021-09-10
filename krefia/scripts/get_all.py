import sys
from pprint import pprint

from krefia.allegro_client import (
    get_all,
    get_relatiecode_bedrijf,
    login_allowed,
    login_tijdelijk,
    get_schuldhulp_aanvragen,
)

bsn = None
if len(sys.argv) >= 2:
    bsn = sys.argv[1]

get_all(bsn)
