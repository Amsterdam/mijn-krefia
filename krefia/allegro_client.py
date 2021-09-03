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
        return client.service

    return None


def get_service(service_name):
    allegro_service = g.get("allegro_service" + service_name, None)
    if not allegro_service:
        service = get_client_service(service_name)
        if service:
            allegro_service = g["allegro_service" + service_name] = service
    return allegro_service


def call_service_method(method_name: str, service_name: str = "LoginService", *kwargs):
    service = get_client_service(service_name)

    if not service:
        logger.error(f"%s, no service." % method_name)
        return

    response = None

    try:
        response = getattr(service, method_name)(*kwargs)
        response_xml = response.content.replace("\n", "")
        response_key = "v1:%s___%sResponse" % (service_name, method_name)
        match = re.search(
            r"<" + response_key + ">.*<\/" + response_key + ">", response_xml
        )
        response = xmltodict.parse(match.group(0))[response_key]
    except Exception as error:
        logger.error(error)

    return response


def login_tijdelijk():
    response = call_service_method("AllegroWebLoginTijdelijk")

    if not response["v1:aUserInfo"]["v1:SessionID"]:
        return None

    session_id = re.compile(r"[\{\}]")
    session_id = re.sub(session_id, "", response["v1:aUserInfo"]["v1:SessionID"])

    return {"session_id": session_id}


def get_relatienummer(bsn=None):
    return call_service_method("BSNNaarRelatie", bsn=bsn)


def get_all(user_id: str):
    # get_service().service.get()
    return []
