from logging import log
import logging
from pprint import pprint
from typing import Any, List, Union
from zeep.proxy import ServiceProxy

from zeep.xsd.elements.element import Element
from krefia.helpers import enum
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

bedrijf = enum({"FIBU": "FIBU", "KREDIETBANK": "KREDIETBANK"})
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
    logger.info("Establishing a connection with Allegro service %s", service_name)
    timeout = 9  # Timeout period for getting WSDL and operations in seconds

    try:
        transport = Transport(timeout=timeout, operation_timeout=timeout)

        client = Client(
            wsdl=get_allegro_service_description(service_name),
            transport=transport,
            settings={
                "xsd_ignore_sequence_order": True,
                "strict": False,
            },
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
        logger.error("%s, no service.", operation)
        return

    try:
        response = getattr(service, method_name)(
            _soapheaders=get_session_header(service_name), *args
        )

        logger.debug("\n\nResponse for %s", operation)
        logger.debug(response)

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

    tr_relatiecodes = get_result(response_body, "TRelatiecodeBedrijfcode", [])
    relatiecodes = {}

    for relatie in tr_relatiecodes:
        if relatie["Bedrijfscode"] == bedrijf_code.FIBU:
            relatiecodes[bedrijf.FIBU] = relatie["Relatiecode"]
        elif relatie["Bedrijfscode"] == bedrijf_code.KREDIETBANK:
            relatiecodes[bedrijf.KREDIETBANK] = relatie["Relatiecode"]

    logger.debug(relatiecodes)

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


def get_result(response_body: dict, key: str, return_type: Any = None):
    result = return_type
    try:
        result = response_body["Result"][key]
    except Exception:
        logger.info("No result.%s", key)
        pass

    return result


def get_schuldhulp_aanvraag(aanvraag_header: dict):
    response_body = call_service_method(
        "SchuldHulpService.GetSRVAanvraag", aanvraag_header
    )
    aanvraag_source = get_result(response_body, "TSRVAanvraag")
    aanvraag = None

    if aanvraag_source:
        title = get_schuldhulp_title(aanvraag_source)
        aanvraag = {"title": title, "url": SRV_DETAIL_URL.format({})}

    return aanvraag


def get_schuldhulp_aanvragen(relatiecode_fibu: str) -> List[dict]:
    response_body = call_service_method(
        "SchuldHulpService.GetSRVOverzicht", relatiecode_fibu
    )
    tsrv_headers = get_result(response_body, "TSRVAanvraagHeader", [])
    schuldhulp_aanvragen = []

    for aanvraag_header in tsrv_headers:
        aanvraag = get_schuldhulp_aanvraag(aanvraag_header)
        if aanvraag:
            schuldhulp_aanvragen.append(aanvraag)

    return schuldhulp_aanvragen


def get_lening(tpl_header: dict) -> dict:
    response_body = call_service_method("FinancieringService.GetPL", tpl_header)
    lening_source = get_result(response_body, "TPL")
    lening = None

    if lening_source:
        total = 0
        current = 0
        title = f"Kredietsom {total}  met openstaand termijnbedrag {current}"

        lening = {"title": title, "url": PL_DETAIL_URL.format({})}

    return lening


def get_leningen(relatiecode_kredietbank: str) -> List[dict]:
    response_body = call_service_method(
        "FinancieringService.GetPLOverzicht", relatiecode_kredietbank
    )
    tpl_headers = get_result(response_body, "TPLHeader", [])
    leningen = []

    for tpl_header in tpl_headers:
        lening = get_lening(tpl_header)
        if lening:
            leningen.append(lening)

    return leningen


def get_budgetbeheer(relatiecode_fibu: str) -> List[dict]:
    response_body = call_service_method("BBRService.GetBBROverzicht", relatiecode_fibu)
    tbbr_headers = get_result(response_body, "TBBRHeader", [])
    budgetbeheer = []

    title = "Beheer uw budget op FiBu"

    for header in tbbr_headers:
        budgetbeheer_link = {
            "title": title,
            "url": BBR_DETAIL_URL.format({}),
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
        response_body = call_service_method("BerichtenBoxService.GetBerichten", query)
        tbbox_headers = get_result(response_body, "TBBoxHeader", [])

        # TODO: Which notification to take?
        if tbbox_headers:
            trigger = tbbox_headers[0]
            date_published = trigger["Tijdstip"]

            notification = {
                "url": notification_urls[bedrijf].format({}),
                "datePublished": date_published,
            }

    return notification


def get_notification_triggers(relaties: dict) -> dict:
    fibu_notification = None
    kredietbank_notification = None

    if bedrijf.FIBU in relaties:
        fibu_notification = get_notification(relaties[bedrijf.FIBU], bedrijf.FIBU)

    if bedrijf.KREDIETBANK in relaties:
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
