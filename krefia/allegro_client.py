from requests import Session, ConnectionError
from requests.auth import HTTPBasicAuth

from flask import g
from zeep import Client
from zeep.transports import Transport
import re
from krefia.config import (
    ALLEGRO_SOAP_UA_STRING,
    get_allegro_service_description,
    logger,
)

import xmltodict


def get_client(service_name: str = "LoginService"):
    logger.info("Establishing a connection with Allegro")

    session = Session()
    session.headers["User-Agent"] = ALLEGRO_SOAP_UA_STRING
    # session.auth = HTTPBasicAuth()

    timeout = 9  # Timeout period for getting WSDL and operations in seconds

    try:
        transport = Transport(
            session=session, timeout=timeout, operation_timeout=timeout
        )

        client = Client(
            wsdl=get_allegro_service_description(service_name), transport=transport
        )

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


def get_client_service(service_name):
    client = get_client(service_name)
    if client:
        with client.settings(raw_response=True):
            return client.service

    return None


def get_service(service_name):
    allegro_service = g.get("allegro_service" + service_name, None)
    if not allegro_service:
        service = get_client_service(service_name)
        if service:
            allegro_service = g["allegro_service" + service_name] = service
    return allegro_service


def call_service_method(method_name: str, service_name: str = "LoginService", *args):
    service = get_client_service(service_name)

    if not service:
        logger.error("%s, no service." % method_name)
        return

    response = None

    try:
        response = getattr(service, method_name)(*args)
    except Exception as error:
        logger.error(error)

    return response


def login_tijdelijk():
    response = call_service_method("AllegroWebLoginTijdelijk")

    if not response["body"]["Result"]:
        return None

    return {"session_id": response["body"]["aUserInfo"]["SessionID"]}


def get_relatienummer(bsn=None):
    return call_service_method(method_name="BSNNaarRelatie", bsn=bsn)


def get_schuldhulp_link():
    response = call_service_method("")

    if not response[""]:
        return None

    url = ""
    title = ""

    return {"title": title, "url": url}


def get_budgetbeheer_link():
    response = call_service_method("")

    if not response[""]:
        return None

    url = ""
    title = ""

    return {"title": title, "url": url}


def get_lening_link():
    response = call_service_method("")

    if not response[""]:
        return None

    url = ""
    title = ""

    return {"title": title, "url": url}


def get_notification_triggers():

    fibu_notification = None
    krediet_notification = None

    response = call_service_method("")

    if not response[""]:
        return None

    return {
        "fibu": fibu_notification,
        "krediet": krediet_notification,
    }


def get_all(user_id: str):
    schuldhulp = None  # get_schuldhulp_link()
    lening = None  # get_lening_link()
    budgetbeheer = None  # get_budgetbeheer_link()

    notification_triggers = None  # get_notification_triggers()

    return {
        "deepLinks": {
            "schuldhulp": schuldhulp,
            "lening": lening,
            "budgetbeheer": budgetbeheer,
        },
        "notificationTriggers": notification_triggers,
    }
