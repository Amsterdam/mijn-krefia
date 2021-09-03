from krefia.config import ALLEGRO_SOAP_ENDPOINT, WSDL_PATH
from zeep import Client
from flask import g, request


def connect():
    client = Client(wsdl=WSDL_PATH)
    service = client.create_service("krefia_allegro", ALLEGRO_SOAP_ENDPOINT)
    print(service)
    print("service:", service.LoginService.AllegroWebLoginTijdelijk())
    return service


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
