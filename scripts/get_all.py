import logging
import sys
from pprint import pprint

from app.config import set_debug
from app.allegro_client import get_all

bsn = None
if len(sys.argv) >= 2:
    bsn = sys.argv[1]

set_debug(True)
wdsl = logging.getLogger("zeep.wsdl.wsdl")
schema = logging.getLogger("zeep.xsd.schema")
wdsl.setLevel(logging.ERROR)
schema.setLevel(logging.ERROR)

content = get_all(bsn)

pprint(content)
