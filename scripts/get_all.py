import logging
import sys
from pprint import pprint

from app.allegro_client import get_all
from app.server import app

bsn = None
if len(sys.argv) >= 2:
    bsn = sys.argv[1]

wdsl = logging.getLogger("zeep.wsdl.wsdl")
schema = logging.getLogger("zeep.xsd.schema")
wdsl.setLevel(logging.ERROR)
schema.setLevel(logging.ERROR)

with app.app_context():
    content = get_all(bsn)

pprint(content)
