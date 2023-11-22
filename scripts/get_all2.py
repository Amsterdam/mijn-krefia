import logging
import sys
from pprint import pprint
from app.server import app

from app.allegro_client import (
    bedrijf,
    get_leningen,
    get_relatiecode_bedrijf,
    get_schuldhulp_aanvragen,
    login_tijdelijk,
)

bsn = None
if len(sys.argv) >= 2:
    bsn = sys.argv[1]

wdsl = logging.getLogger("zeep.wsdl.wsdl")
schema = logging.getLogger("zeep.xsd.schema")
wdsl.setLevel(logging.DEBUG)
schema.setLevel(logging.DEBUG)

with app.app_context():
    is_logged_in = login_tijdelijk()

    if is_logged_in:
        relaties = get_relatiecode_bedrijf(bsn)

        if not relaties:
            print("No relaties found!")
            exit(1)

        fibu_relatie_code = relaties[bedrijf.FIBU]
        kredietbank_relatie_code = relaties[bedrijf.KREDIETBANK]

        schuldhulp = None
        budgetbeheer = None
        lening = None

        if fibu_relatie_code:
            schuldhulp = get_schuldhulp_aanvragen(fibu_relatie_code)
            budgetbeheer = get_leningen(fibu_relatie_code)

        if kredietbank_relatie_code:
            lening = get_leningen(kredietbank_relatie_code)
