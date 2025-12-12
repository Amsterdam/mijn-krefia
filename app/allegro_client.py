import logging
from datetime import date
from typing import Any

from flask import g
from requests import ConnectionError
from zeep import Client
from zeep.settings import Settings
from zeep.transports import Transport
from zeep.xsd.elements.element import Element

from app.config import (
    ALLEGRO_EXCLUDE_OPDRACHTGEVER,
    ALLEGRO_REQUEST_TIMEOUT,
    KREFIA_SSO_FIBU,
    KREFIA_SSO_KREDIETBANK,
    get_allegro_service_description,
)
from app.helpers import dotdict, format_currency

allegro_client = {}

bedrijf = dotdict({"FIBU": "FIBU", "KREDIETBANK": "KREDIETBANK"})
bedrijf_code = dotdict(
    {bedrijf.FIBU: "10", bedrijf.KREDIETBANK: "2"}
)  # Make availabile in ENV, these are not constant

# The Krefia platform doesn't support true deeplinks at the moment so we supply a few generic SSO endpoints.
SRV_DETAIL_URL = KREFIA_SSO_KREDIETBANK
PL_DETAIL_URL = KREFIA_SSO_KREDIETBANK
BBR_DETAIL_URL = KREFIA_SSO_FIBU
FIBU_NOTIFICATION_URL = KREFIA_SSO_FIBU
KREDIETBANK_NOTIFICATION_URL = KREFIA_SSO_KREDIETBANK

notification_urls = {
    bedrijf.FIBU: FIBU_NOTIFICATION_URL,
    bedrijf.KREDIETBANK: KREDIETBANK_NOTIFICATION_URL,
}


def get_client(service_name: str):
    global allegro_client  # flake8 error says it is unused but it is clearly used. # noqa: F824

    if service_name not in allegro_client:
        logging.info(f"Establishing a connection with Allegro service {service_name}")

        try:
            transport = Transport(timeout=ALLEGRO_REQUEST_TIMEOUT)
            client = Client(
                wsdl=get_allegro_service_description(service_name),
                transport=transport,
                settings=Settings(xsd_ignore_sequence_order=True, strict=False),
            )
            allegro_client[service_name] = client
            return client
        except ConnectionError as e:
            # do not rethrow the error, because the error has a object address in it, it is a new error every time.
            logging.error(f"Failed to establish a connection with Allegro: ({type(e)})")
            return None
        except Exception as error:
            logging.error(
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
    g.session_id = id


def get_session_id():
    session_id = getattr(g, "session_id", None)
    return session_id


def get_session_header(service_name: str):
    if not get_session_id():
        logging.debug("Session id not found")
        return []

    client = get_client(service_name)
    header = client.get_element("ns0:ROClientIDHeader")
    session_header = header(
        ID=get_session_id(),
    )
    logging.debug(session_header)

    return [session_header]


def call_service_method(operation: str, *args):
    service_name, method_name = operation.split(".")
    service = get_service(service_name)

    if not service:
        logging.error(f"{operation}, no service.")
        return

    try:
        response = getattr(service, method_name)(
            _soapheaders=get_session_header(service_name), *args
        )
        logging.error(response)

        if not response or "body" not in response:
            logging.error("Unexpected response for %s", operation)
            return None
        else:
            logging.debug("\n\nResponse for %s", operation)
            logging.debug(response)

            return response["body"]
    except Exception as error:
        logging.error(
            f"Could not execute service operation: {operation}, error: {error}"
        )

    return None


def login_tijdelijk():
    response_body = call_service_method(
        "LoginService.AllegroWebLoginTijdelijk",
        "",
        "",
    )
    result = get_result(response_body)

    if result:
        set_session_id(response_body["aUserInfo"]["SessionID"])

    return bool(result)


def get_relatiecode_bedrijf(bsn: str):
    response_body = call_service_method("LoginService.BSNNaarRelatieMetBedrijf", bsn)

    tr_relatiecodes = get_result(response_body, "TRelatiecodeBedrijfcode", [])
    relatiecodes = {}

    if isinstance(tr_relatiecodes, list):
        for relatie in tr_relatiecodes:
            if str(relatie["Bedrijfscode"]) == bedrijf_code.FIBU:
                relatiecodes[bedrijf.FIBU] = relatie["Relatiecode"]
            elif str(relatie["Bedrijfscode"]) == bedrijf_code.KREDIETBANK:
                relatiecodes[bedrijf.KREDIETBANK] = relatie["Relatiecode"]

        logging.debug(relatiecodes)

    return relatiecodes


def login_allowed(relatiecode: str, setSessionId: bool = False):
    response_body = call_service_method(
        "LoginService.AllegroWebMagAanmelden", relatiecode, "", ""
    )

    logging.debug(response_body)

    is_allowed = response_body["Result"]

    if setSessionId and response_body and "aUserInfo" in response_body:
        set_session_id(response_body["aUserInfo"]["SessionID"])

    return is_allowed


def get_schuldhulp_title(status: str, extra_status: str, eind_status: str):
    title = "Lopend"

    if eind_status == "I":
        title = "Schuldeisers akkoord"

    elif eind_status in ["T", "U", "V", "W", "X", "Y", "Z"]:
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

    try:
        result = response_body["Result"]

        if key and result is not None:
            result = result[key]
        elif key:
            return return_default

        # Compensate for XML's weirdness in treating 1 Element = dict, >=1 Element = list
        if (
            result
            and isinstance(return_default, list)
            and not isinstance(result, type(return_default))
        ):
            result = [result]
    except Exception as error:
        logging.error(
            f"Unexpected result for key: {key}, error: {error}",
            extra={"result": result},
        )
        pass

    return result


def value_or_default(source: Element, key: str, default_value: Any):
    return source[key] if key in source and source[key] else default_value


def get_schuldhulp_aanvraag(aanvraag_header: dict):
    aanvraag_header_clean = {
        "RelatieCode": aanvraag_header["RelatieCode"],
        "Volgnummer": aanvraag_header["Volgnummer"],
        "IsNPS": aanvraag_header["IsNPS"],
        "Status": value_or_default(aanvraag_header, "Status", ""),
        "Statustekst": aanvraag_header["Statustekst"],
        "Aanvraagdatum": aanvraag_header["Aanvraagdatum"],
        "ExtraStatus": value_or_default(aanvraag_header, "ExtraStatus", ""),
    }

    TSRV_Header = get_client("SchuldHulpService").get_type("ns0:TSRVAanvraagHeader")

    tsrv_header = TSRV_Header(**aanvraag_header_clean)

    response_body = call_service_method("SchuldHulpService.GetSRVAanvraag", tsrv_header)

    aanvraag_source = get_result(response_body)

    if (
        "Opdrachtgever" in aanvraag_source
        and aanvraag_source["Opdrachtgever"] in ALLEGRO_EXCLUDE_OPDRACHTGEVER
    ):
        return None

    aanvraag = None

    if aanvraag_source:
        title = get_schuldhulp_title(
            aanvraag_header["Status"],
            aanvraag_header["ExtraStatus"],
            aanvraag_source["Eindstatus"],
        )
        aanvraag = {
            "title": title,
            "url": SRV_DETAIL_URL
            # % (aanvraag_header["RelatieCode"], aanvraag_header["Volgnummer"]),
        }

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
        total = format_currency(lening_source["NettoKredietsom"])
        monthly_term = format_currency(lening_source["MaandTermijn"])

        title = f"U hebt {total} geleend. Hierop moet u iedere maand {monthly_term} aflossen."

        lening = {
            "title": title,
            "url": PL_DETAIL_URL
            # % (
            #     lening_source["InfoHeader"]["RelatieCode"],
            #     lening_source["InfoHeader"]["Volgnummer"],
            # ),
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

    title = "Lopend"

    for tbbr_header in tbbr_headers:
        budgetbeheer_link = {
            "title": title,
            "url": BBR_DETAIL_URL
            # % (
            #     tbbr_header["RelatieCode"],
            #     tbbr_header["Volgnummer"],
            # ),
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
            "ovOntvangen",
            "Nee",
            "Nee",
            "Oplopend",
        )

        tbbox_headers = get_result(response_body, "TBBoxHeader", [])

        if tbbox_headers:
            date_published = date.today().strftime("%Y-%m-%d")

            notification = {
                "url": notification_urls[bedrijf],
                "datePublished": date_published,
            }

    return notification


def get_all(bsn: str):
    is_logged_in = login_tijdelijk()

    if is_logged_in:
        relaties = get_relatiecode_bedrijf(bsn)

        schuldhulp = None
        budgetbeheer = None
        lening = None
        notification_triggers = None
        fibu_notification = None
        kredietbank_notification = None

        if not relaties:
            logging.info("No relaties for this user.")
            return None

        fibu_relatie_code = relaties.get(bedrijf.FIBU)
        kredietbank_relatie_code = relaties.get(bedrijf.KREDIETBANK)

        if fibu_relatie_code:
            if login_allowed(fibu_relatie_code, True):
                budgetbeheer = get_budgetbeheer(fibu_relatie_code)
                fibu_notification = get_notification(
                    relaties[bedrijf.FIBU], bedrijf.FIBU
                )

        if kredietbank_relatie_code:
            if login_allowed(kredietbank_relatie_code, fibu_relatie_code is None):
                schuldhulp = get_schuldhulp_aanvragen(kredietbank_relatie_code)
                lening = get_leningen(kredietbank_relatie_code)
                kredietbank_notification = get_notification(
                    relaties[bedrijf.KREDIETBANK], bedrijf.KREDIETBANK
                )

        if not (
            budgetbeheer
            or schuldhulp
            or lening
            or fibu_notification
            or kredietbank_notification
        ):
            return None

        if fibu_notification or kredietbank_notification:
            notification_triggers = {}

            if fibu_notification:
                notification_triggers["fibu"] = fibu_notification

            if kredietbank_notification:
                notification_triggers["krediet"] = kredietbank_notification

        return {
            "deepLinks": {
                "schuldhulp": schuldhulp[0] if schuldhulp else None,
                "lening": lening[0] if lening else None,
                "budgetbeheer": budgetbeheer[0] if budgetbeheer else None,
            },
            "notificationTriggers": notification_triggers,
        }

    raise Exception("Could not login to Allegro")
