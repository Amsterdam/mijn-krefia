from krefia.config import ALLEGRO_SOAP_ENDPOINT
from zeep import Client
from flask import g, request
import inspect
from pprint import pprint


def get_user_attributes(cls):
    boring = dir(type("dummy", (object,), {}))
    return [item for item in inspect.getmembers(cls) if item[0] not in boring]


def connect():
    client = Client(wsdl=ALLEGRO_SOAP_ENDPOINT)
    print("==client==")
    pprint(get_user_attributes(client))
    print("==service==")
    pprint(get_user_attributes(client.service))
    print("service:", client.service.AllegroWebLoginTijdelijk())
    factory = client.type_factory("ns0")
    print("==factory==")
    pprint(get_user_attributes(factory))
    return client.service


def get_service():
    """Creates a DecosJoin connection instance if there is none yet for the
    current application context.
    """
    allegro_service = g.get("allegro_service", None)
    if not allegro_service:
        allegro_service = g.allegro_service = connect()
    return allegro_service


def get_all(user_id: str):
    # get_service().service.get()
    return []
