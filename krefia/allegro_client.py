import zeep
from requests import ConnectionError, Session
from requests.auth import HTTPBasicAuth
from zeep import Client
from zeep.transports import Transport

from krefia.config import (
    ALLEGRO_SOAP_UA_STRING,
    get_allegro_service_description,
    logger,
)

session_id = None
allegro_service = None


def get_client():
    logger.info("Establishing a connection with Allegro")

    # session = Session()
    # session.headers["User-Agent"] = ALLEGRO_SOAP_UA_STRING
    # session.auth = HTTPBasicAuth()

    timeout = 9  # Timeout period for getting WSDL and operations in seconds

    try:
        transport = Transport(timeout=timeout, operation_timeout=timeout)

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

    # if client:
    #     with client.settings(raw_response=True):

    return client.service


def get_service():
    global allegro_service

    if not allegro_service:
        allegro_service = get_client_service()

    return allegro_service


def set_session_id(id: str):
    global session_id
    session_id = id


def get_session_header():
    client = get_client()
    header = client.get_element("ns0:ROClientIDHeader")

    """"
    <ROClientIDHeader SOAP-ENV:mustUnderstand="0"
        xmlns="http://tempuri.org/">
        <ID>{43B7DD35-848E-4F52-B90A-6D2E4071D9C6}</ID>
    </ROClientIDHeader>
    """

    # session_header = header(
    #     ID=session_id,
    # )
    # print(session_header)

    # return [session_header]
    return {"ROClientID": session_id}


def call_service_method(operation: str, *args):

    service_name, method_name = operation.split(".")

    service = get_service(service_name)

    if not service:
        logger.error("%s, no service." % method_name)
        return

    response = None

    try:
        response = getattr(service, method_name)(
            _soapheaders=get_session_header(), *args
        )
    except Exception as error:
        logger.error(error)

    return response


def login_tijdelijk():
    response = call_service_method("LoginService.AllegroWebLoginTijdelijk")

    result = response["body"]["Result"]

    if result:
        set_session_id(response["body"]["aUserInfo"]["SessionID"])

    return result


def get_relatienummer(bsn=None):
    return call_service_method("LoginService.BSNNaarRelatie", bsn)


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
