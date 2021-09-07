from attr import s
from requests import ConnectionError
from zeep import Client
from zeep.transports import Transport

from krefia.config import (
    get_allegro_service_description,
    get_allegro_service_endpoint,
    logger,
)

session_id = None
allegro_service = {}


def get_client(service_name: str):
    logger.info("Establishing a connection with Allegro")

    # session = Session()
    # session.headers["User-Agent"] = ALLEGRO_SOAP_UA_STRING
    # session.auth = HTTPBasicAuth()

    timeout = 9  # Timeout period for getting WSDL and operations in seconds

    try:
        transport = Transport(timeout=timeout, operation_timeout=timeout)

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


def get_client_service(service_name: str):
    client = get_client(service_name)

    service = client.create_service(
        "{http://tempuri.org/}%sBinding" % service_name,
        get_allegro_service_endpoint(service_name),
    )

    return service


def get_service(service_name: str):
    global allegro_service

    if service_name not in allegro_service:
        allegro_service[service_name] = get_client_service(service_name)

    return allegro_service[service_name]


def set_session_id(id: str):
    global session_id

    logger.info("Set session-id %s" % id)

    session_id = id


def get_session_id():
    return session_id


def get_session_header(service_name: str):
    """
    <ROClientIDHeader SOAP-ENV:mustUnderstand="0"
        xmlns="http://tempuri.org/">
        <ID>{43B7DD35-848E-4F52-B90A-6D2E4071D9C6}</ID>
    </ROClientIDHeader>
    """

    if not session_id:
        return []

    client = get_client(service_name)
    header = client.get_element("ns0:ROClientIDHeader")
    session_header = header(
        ID=session_id,
    )
    return [session_header]

    # return {"ROClientID": session_id}


# def test_message():
#     client = get_client("LoginService")
#     node = client.create_message(
#         client.service, "result", taskId="0000015ca2e45f838136c6b6000a0000000000ab"
#     )


def call_service_method(operation: str, *args):

    service_name, method_name = operation.split(".")

    service = get_service(service_name)

    if not service:
        logger.error("%s, no service." % method_name)
        return

    response = None

    try:
        response = getattr(service, method_name)(
            _soapheaders=get_session_header(service_name), *args
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
