import inspect
from pprint import pprint

from requests import Session, ConnectionError
from requests.auth import HTTPBasicAuth

from flask import g
from zeep import Client
from zeep.transports import Transport

from krefia.config import get_allegro_service_description, logger


def get_user_attributes(cls):
    boring = dir(type("dummy", (object,), {}))
    return [item for item in inspect.getmembers(cls) if item[0] not in boring]


def get_client():
    logger.info("Establishing a connection with Allegro")

    session = Session()
    # session.auth = HTTPBasicAuth()

    timeout = 9  # Timeout period for getting WSDL and operations in seconds

    try:
        transport = Transport(
            session=session, timeout=timeout, operation_timeout=timeout
        )

        client = Client(wsdl=get_allegro_service_description(), transport=transport)

        return client
    except ConnectionError as e:
        # do not relog the error, because the error has a object address in it, it is a new error every time.
        logger.error(
            f"Failed to establish a connection with Allegro: Connection Timeout ({type(e)})"
        )
        return None
    except Exception as error:
        logger.error(
            "Failed to establish a connection with Allegro: {} {}".format(
                type(error), str(error)
            )
        )
        return None


def get_client_service():
    client = get_client()
    if client:
        return client.service

    return None


def get_service():
    allegro_service = g.get("allegro_service", None)
    if not allegro_service:
        service = get_client_service()
        if service:
            allegro_service = g.allegro_service = service
    return allegro_service


def get_relatienummer(bsn=None):
    service = get_client_service()

    if not service:
        logger.error("No service.")
        return

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
