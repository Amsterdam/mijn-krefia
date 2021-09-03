import sys
from pprint import pprint

from krefia.allegro_client import connect

bsn = sys.argv[1]

service = connect()

print("=====client=====", bsn)
pprint(service)
