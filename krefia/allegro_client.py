from typing import List, Union
from zeep.proxy import ServiceProxy

from zeep.xsd.elements.element import Element
from krefia.helpers import enum
from attr import s
from requests import ConnectionError
from zeep import Client
from zeep.transports import Transport

from krefia.config import (
    IS_DEBUG,
    get_allegro_service_description,
    get_allegro_service_endpoint,
    logger,
)

session_id = None
allegro_service = {}

bedrijf = enum({"FIBU": "FIBU", "KRED": "Kredietbank"})
bedrijf_code = enum({bedrijf.FIBU: 10, bedrijf.KREDIETBANK: 2})

SRV_DETAIL_URL = "http://host/srv/{RelatieCode}/{Volgnummer}"
PL_DETAIL_URL = "http://?"
BBR_DETAIL_URL = "http://?"
FIBU_NOTIFICATION_URL = "http://?"
KREDIETBANK_NOTIFICATION_URL = "http://?"

notification_urls = {
    bedrijf.FIBU: FIBU_NOTIFICATION_URL,
    bedrijf.KREDIETBANK: KREDIETBANK_NOTIFICATION_URL,
}


def get_client(service_name: str) -> Union[Client, None]:
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


def get_client_service(service_name: str) -> ServiceProxy:
    client = get_client(service_name)

    service = client.create_service(
        "{http://tempuri.org/}%sBinding" % service_name,
        get_allegro_service_endpoint(service_name),
    )

    return service


def get_service(service_name: str) -> ServiceProxy:
    global allegro_service

    if service_name not in allegro_service:
        allegro_service[service_name] = get_client_service(service_name)

    return allegro_service[service_name]


def set_session_id(id: str) -> None:
    global session_id

    logger.info(f"Set session-id {id}")

    session_id = id


def get_session_id() -> str:
    return session_id


def get_session_header(service_name: str) -> List[Element]:
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


def call_service_method(operation: str, *args) -> Union[dict, None]:

    service_name, method_name = operation.split(".")

    service = get_service(service_name)

    if not service:
        logger.error("%s, no service." % method_name)
        return

    try:
        response = getattr(service, method_name)(
            _soapheaders=get_session_header(service_name), *args
        )
        if IS_DEBUG:
            logger.debug(f"{operation} response", response)

        return response["body"]
    except Exception as error:
        logger.error(error)

    return None


def login_tijdelijk() -> bool:
    response_body = call_service_method("LoginService.AllegroWebLoginTijdelijk")

    result = response_body["Result"]

    if result:
        set_session_id(response_body["aUserInfo"]["SessionID"])

    return result


def get_relatiecode_bedrijf(bsn: str) -> Union[dict, None]:
    response_body = call_service_method("LoginService.BSNNaarRelatieMetBedrijf", bsn)

    result = response_body["Result"]
    relatiecodes = None

    if result:
        relatiecodes = {}
        for relatie in result["TRelatiecodeBedrijfcode"]:
            if relatie["Bedrijfscode"] == bedrijf_code.FIBU:
                relatiecodes[bedrijf.FIBU] = relatie["Relatiecode"]
            elif relatie["Bedrijfscode"] == bedrijf_code.KREDIETBANK:
                relatiecodes[bedrijf.KREDIETBANK] = relatie["Relatiecode"]

    return relatiecodes


def login_allowed(relatiecode: str) -> bool:
    response_body = call_service_method(
        "LoginService.AllegroWebMagAanmelden", relatiecode
    )

    is_allowed = response_body["Result"]

    return is_allowed


def get_schuldhulp_title(aanvraag_source: dict) -> str:
    title = ""
    eind_status = aanvraag_source["Eindstatus"]
    status = aanvraag_source["Status"]
    extra_status = aanvraag_source["ExtraStatus"]

    if eind_status == "I":
        title = "Schuldeisers akkoord"

    elif eind_status == "Z":
        title = "Aanvraag afgewezen"

    elif extra_status == "Voorlopig afgewezen":
        title = "Dwangprocedure loopt"

    elif status == "A":
        title = "Inventariseren ingediende aanvraag"

    elif status in ["B", "C", "D"]:
        title = "Schuldhoogte wordt opgevraagd"

    elif status in ["E", "F", "G"]:
        title = "Afkoopvoorstellen zijn verstuurd"

    return title


def get_schuldhulp_aanvraag(aanvraag_header: dict):
    response_body = call_service_method(
        "SchuldHulpService.GetSRVAanvraag", aanvraag_header
    )

    aanvraag_source = response_body["TSRVAanvraag"]
    aanvraag = None

    if aanvraag_source:
        title = get_schuldhulp_title(aanvraag_source)
        aanvraag = {"title": title, "url": SRV_DETAIL_URL.format(**aanvraag_source)}

    return aanvraag


def get_schuldhulp_aanvragen(relatiecode_fibu: str) -> List[dict]:
    response_body = call_service_method(
        "SchuldHulpService.GetSRVOverzicht", relatiecode_fibu
    )

    schuldhulp_aanvragen = []

    for aanvraag_header in response_body["TSRVAanvraagHeader"]:
        aanvraag = get_schuldhulp_aanvraag(aanvraag_header)
        schuldhulp_aanvragen.append(aanvraag)

    return schuldhulp_aanvragen


def get_lening(tpl_header: dict) -> dict:
    response_body = call_service_method("FinancieringService.GetPL", tpl_header)

    lening_source = response_body["TPL"]
    lening = None

    if lening_source:
        total = 0
        current = 0
        title = f"Kredietsom {total}  met openstaand termijnbedrag {current}"

        lening = {"title": title, "url": PL_DETAIL_URL.format(**lening_source)}

    return lening


def get_leningen(relatiecode_kredietbank: str) -> List[dict]:
    response_body = call_service_method(
        "FinancieringService.GetPLOverzicht", relatiecode_kredietbank
    )

    tpl_headers = response_body["TPLHeader"]

    leningen = [get_lening(tpl_header) for tpl_header in tpl_headers]

    return leningen


def get_budgetbeheer(relatiecode_fibu: str) -> List[dict]:
    response_body = call_service_method("BBRService.GetBBROverzicht", relatiecode_fibu)

    budgetbeheer_headers = response_body["TBBRHeader"]
    budgetbeheer = None

    if budgetbeheer_headers:
        title = "Beheer uw budget op FiBu"

        for header in budgetbeheer_headers:
            budgetbeheer_link = {
                "title": title,
                "url": BBR_DETAIL_URL.format(**header),
            }
            budgetbeheer.append(budgetbeheer_link)

    return budgetbeheer


def get_notification(relatiecode: str, bedrijf: str) -> Union[dict, None]:
    notification = None
    response_body = None

    if relatiecode:
        query = {
            "Relatiecode": relatiecode,
            # "OntvangenVerzonden": "ovOntvangen",
            "Gelezen": "Nee",
        }
        response_body = call_service_method("BerichtenboxService.GetBerichten", query)
        trigger = response_body["TBBoxHeader"]

        if trigger:
            # TODO: Which notification to take?
            trigger = response_body["TBBoxHeader"][0]
            date_published = trigger["Tijdstip"]

            notification = {
                "url": notification_urls[bedrijf].format(**trigger),
                "datePublished": date_published,
            }

            return notification


def get_notification_triggers(relaties: dict) -> dict:
    fibu_notification = None
    kredietbank_notification = None

    if relaties[bedrijf.FIBU]:
        fibu_notification = get_notification(relaties[bedrijf.FIBU], bedrijf.FIBU)

    if relaties[bedrijf.KREDIETBANK]:
        kredietbank_notification = get_notification(
            relaties[bedrijf.KREDIETBANK], bedrijf.KREDIETBANK
        )

    return {
        "fibu": fibu_notification,
        "krediet": kredietbank_notification,
    }


def get_all(bsn: str) -> dict:
    is_logged_in = login_tijdelijk()

    if is_logged_in:
        relaties = get_relatiecode_bedrijf(bsn)

        if not relaties:
            return None

        fibu_relatie_code = relaties.get(bedrijf.FIBU)
        kredietbank_relatie_code = relaties.get(bedrijf.KREDIETBANK)

        schuldhulp = None
        budgetbeheer = None
        lening = None

        if fibu_relatie_code:
            if login_allowed(fibu_relatie_code):
                schuldhulp = get_schuldhulp_aanvragen(fibu_relatie_code)
                budgetbeheer = get_budgetbeheer(fibu_relatie_code)

        if kredietbank_relatie_code:
            if login_allowed(kredietbank_relatie_code):
                lening = get_leningen(kredietbank_relatie_code)

        notification_triggers = get_notification_triggers(relaties)

        return {
            "deepLinks": {
                "schuldhulp": schuldhulp,
                "lening": lening,
                "budgetbeheer": budgetbeheer,
            },
            "notificationTriggers": notification_triggers,
        }
