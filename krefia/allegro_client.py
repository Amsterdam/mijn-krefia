from krefia.config import WSDL_PATH
from zeep import Client
from flask import g, request


def connect():
    client = Client(wsdl=WSDL_PATH)
    print(client.service.Method1("Zeep", "is cool"))
    return client


def get_client():
    """Creates a DecosJoin connection instance if there is none yet for the
    current application context.
    """
    allegro_client = g.get("allegro_client", None)
    if not allegro_client:
        allegro_client = g.allegro_client = connect()
    return allegro_client


def get_all(user_id: str):
    # get_client().service.get()
    return []
