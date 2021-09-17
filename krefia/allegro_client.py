from datetime import date
from typing import Any

from requests import ConnectionError
from zeep import Client
from zeep.settings import Settings
from zeep.transports import Transport

from krefia.config import get_allegro_service_description, logger
from krefia.helpers import dotdict

session_id = None
allegro_client = {}

bedrijf = dotdict({"FIBU": "FIBU", "KREDIETBANK": "KREDIETBANK"})
bedrijf_code = dotdict({bedrijf.FIBU: "10", bedrijf.KREDIETBANK: "2"})

SRV_DETAIL_URL = "http://host/srv/{RelatieCode}/{Volgnummer}"
PL_DETAIL_URL = "http://host/pl/{RelatieCode}/{Volgnummer}"
BBR_DETAIL_URL = "http://host/bbr/{RelatieCode}/{Volgnummer}"
FIBU_NOTIFICATION_URL = "http://host/berichten/fibu"
KREDIETBANK_NOTIFICATION_URL = "http://host/berichten/kredietbank"

notification_urls = {
    bedrijf.FIBU: FIBU_NOTIFICATION_URL,
    bedrijf.KREDIETBANK: KREDIETBANK_NOTIFICATION_URL,
}


def get_client(service_name: str):
    global allegro_client

    if service_name not in allegro_client:
        logger.info(f"Establishing a connection with Allegro service {service_name}")
        timeout = 9  # Timeout period for getting WSDL and operations in seconds

        try:
            transport = Transport(timeout=timeout, operation_timeout=timeout)

            client = Client(
                wsdl=get_allegro_service_description(service_name),
                transport=transport,
                settings=Settings(xsd_ignore_sequence_order=True, strict=False),
            )
            allegro_client[service_name] = client
            return client
        except ConnectionError as e:
            # do not rethrow the error, because the error has a object address in it, it is a new error every time.
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

    return allegro_client[service_name]


def get_service(service_name: str):
    client = get_client(service_name)
    try:
        return client.service
    except Exception:
        return None


def set_session_id(id: str):
    global session_id

    logger.info(f"Set session-id {id}")

    session_id = id


def get_session_id():
    return session_id


def get_session_header(service_name: str):
    if not session_id:
        return []

    client = get_client(service_name)
    header = client.get_element("ns0:ROClientIDHeader")
    session_header = header(
        ID=session_id,
    )

    return [session_header]


def call_service_method(operation: str, *args):
    service_name, method_name = operation.split(".")
    service = get_service(service_name)

    if not service:
        logger.error(f"{operation}, no service.")
        return

    try:
        response = getattr(service, method_name)(
            _soapheaders=get_session_header(service_name), *args
        )

        if "body" not in response:
            logger.error("Unexpected response for %s", operation)
            return None
        else:

            logger.debug("\n\nResponse for %s", operation)
            logger.debug(response)

            return response["body"]
    except Exception as error:
        logger.error(f"Could not execute service method: {error}")

    return None


def login_tijdelijk():
    response_body = call_service_method("LoginService.AllegroWebLoginTijdelijk")

    result = get_result(response_body)

    if result:
        set_session_id(response_body["aUserInfo"]["SessionID"])

    return bool(result)


def get_relatiecode_bedrijf(bsn: str):
    response_body = call_service_method("LoginService.BSNNaarRelatieMetBedrijf", bsn)

    tr_relatiecodes = get_result(response_body, "TRelatiecodeBedrijfcode", [])
    relatiecodes = {}

    for relatie in tr_relatiecodes:
        if str(relatie["Bedrijfscode"]) == bedrijf_code.FIBU:
            relatiecodes[bedrijf.FIBU] = relatie["Relatiecode"]
        elif str(relatie["Bedrijfscode"]) == bedrijf_code.KREDIETBANK:
            relatiecodes[bedrijf.KREDIETBANK] = relatie["Relatiecode"]

    logger.debug(relatiecodes)

    return relatiecodes


def login_allowed(relatiecode: str):
    response_body = call_service_method(
        "LoginService.AllegroWebMagAanmelden", relatiecode
    )

    is_allowed = response_body["Result"]

    return is_allowed


def get_schuldhulp_title(aanvraag_source: dict):
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


def get_result(response_body: dict, key: str = None, return_default: Any = None):
    if not response_body:
        return return_default

    result = return_default

    if response_body.get("Result", False):
        result = response_body["Result"]

        if result and key:
            result = result.get(key)

        # Compensate for XML's weirdness in treating 1 Element = dict, >=1 Element = list
        if (
            result
            and isinstance(return_default, list)
            and not isinstance(result, type(return_default))
        ):
            result = [result]

    return result


def get_schuldhulp_aanvraag(aanvraag_header: dict):
    response_body = call_service_method(
        "SchuldHulpService.GetSRVAanvraag", aanvraag_header
    )
    aanvraag_source = get_result(response_body, "TSRVAanvraag")
    aanvraag = None

    if aanvraag_source:
        title = get_schuldhulp_title(aanvraag_source)
        aanvraag = {"title": title, "url": SRV_DETAIL_URL.format(**aanvraag_source)}

    return aanvraag


def get_schuldhulp_aanvragen(relatiecode_fibu: str):
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


def get_lening(tpl_header: dict):
    response_body = call_service_method("FinancieringService.GetPL", tpl_header)
    lening_source = get_result(response_body)
    lening = None

    if lening_source:
        total = lening_source["BrutoKredietsom"]
        current = lening_source["OpenstaandeKredietvergoeding"]
        title = f"Kredietsom {total}  met openstaand termijnbedrag {current}"
        lening = {
            "title": title,
            "url": PL_DETAIL_URL.format(**lening_source["InfoHeader"]),
        }

    return lening


def get_leningen(relatiecode_kredietbank: str):
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


def get_budgetbeheer(relatiecode_fibu: str):
    response_body = call_service_method("BBRService.GetBBROverzicht", relatiecode_fibu)
    tbbr_headers = get_result(response_body, "TBBRHeader", [])
    budgetbeheer = []

    title = "Beheer uw budget op FiBu"

    for tbbr_header in tbbr_headers:
        budgetbeheer_link = {
            "title": title,
            "url": BBR_DETAIL_URL.format(**tbbr_header),
        }
        budgetbeheer.append(budgetbeheer_link)

    return budgetbeheer


def get_notification(relatiecode: str, bedrijf: str):
    notification = None
    response_body = None

    if relatiecode:
        # "Relatiecode": relatiecode,
        # "DatumVan": date(2020, 1, 1),
        # "DatumTotEnMet": date.today(),
        # "OntvangenVerzonden": "ovBeide",
        # "Gelezen": "Nee",
        # "Gearchiveerd": "Nee",
        # "Sortering": "Oplopend",

        response_body = call_service_method(
            "BerichtenBoxService.GetBerichten",
            relatiecode,
            date(2020, 1, 1),
            date.today(),
            "ovBeide",
            "Nee",
            "Nee",
            "Oplopend",
        )

        tbbox_headers = get_result(response_body, "TBBoxHeader", [])

        # TODO: Which notification to take?
        if tbbox_headers:
            trigger = tbbox_headers[0]
            date_published = trigger["Tijdstip"]

            notification = {
                "url": notification_urls[bedrijf],
                "datePublished": date_published,
            }

    return notification


def get_notification_triggers(relaties: dict):
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


def get_all(bsn: str):
    is_logged_in = login_tijdelijk()

    if is_logged_in:
        relaties = get_relatiecode_bedrijf(bsn)

        schuldhulp = None
        budgetbeheer = None
        lening = None
        notification_triggers = None

        if not relaties:
            return None

        fibu_relatie_code = relaties.get(bedrijf.FIBU)
        kredietbank_relatie_code = relaties.get(bedrijf.KREDIETBANK)

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

    raise Exception("Could not login to Allegro")
