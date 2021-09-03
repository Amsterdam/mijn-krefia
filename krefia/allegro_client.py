import inspect
from pprint import pprint

from flask import g
from zeep import Client

from krefia.config import get_allegro_service_description


def get_user_attributes(cls):
    boring = dir(type("dummy", (object,), {}))
    return [item for item in inspect.getmembers(cls) if item[0] not in boring]


def connect():
    client = Client(wsdl=get_allegro_service_description())
    print("==service==")
    pprint(get_user_attributes(client.service))
    return client.service


def get_service():
    """Creates a DecosJoin connection instance if there is none yet for the
    current application context.
    """
    allegro_service = g.get("allegro_service", None)
    if not allegro_service:
        allegro_service = g.allegro_service = connect()
    return allegro_service


def get_relatienummer(bsn=None):
    service = connect()

    try:
        print("service:", service.AllegroWebLoginTijdelijk())
    except Exception as e:
        print(e)

    try:
        print("service:", service.BSNNaarRelatie(bsn))
    except Exception as e:
        print(e)


def get_all(user_id: str):
    # get_service().service.get()
    return []
