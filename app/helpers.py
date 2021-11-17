import inspect
import os
from functools import wraps
from pprint import pprint

from flask import g, request
from tma_saml import (
    HR_KVK_NUMBER_KEY,
    SamlVerificationException,
    get_digi_d_bsn,
    get_e_herkenning_attribs,
)
from tma_saml.tma_saml import get_user_type
from tma_saml.user_type import UserType


def get_tma_certificate():

    tma_certificate = g.get("tma_certificate", None)

    if not tma_certificate:
        tma_cert_location = os.getenv("TMA_CERTIFICATE")

        if tma_cert_location:
            with open(tma_cert_location) as f:
                tma_certificate = g.tma_certificate = f.read()

    return tma_certificate


def get_bsn_from_request():
    """
    Get the BSN based on a request, expecting a SAML token in the headers
    """
    # Load the TMA certificate
    tma_certificate = get_tma_certificate()

    # Decode the BSN from the request with the TMA certificate
    bsn = get_digi_d_bsn(request, tma_certificate)
    return bsn


def get_kvk_number_from_request():
    """
    Get the KVK number from the request headers.
    """
    # Load the TMA certificate
    tma_certificate = get_tma_certificate()

    # Decode the BSN from the request with the TMA certificate
    attribs = get_e_herkenning_attribs(request, tma_certificate)
    kvk = attribs[HR_KVK_NUMBER_KEY]
    return kvk


def get_tma_user():
    user_type = get_user_type(request, get_tma_certificate())
    user_id = None

    if user_type is UserType.BEDRIJF:
        user_id = get_kvk_number_from_request()
    elif user_type is UserType.BURGER:
        user_id = get_bsn_from_request()
    else:
        raise SamlVerificationException("TMA user type not found")

    if not user_id:
        raise SamlVerificationException("TMA user id not found")

    return {"id": user_id, "type": user_type}


def verify_tma_user(function):
    @wraps(function)
    def verify(*args, **kwargs):
        get_tma_user()
        return function(*args, **kwargs)

    return verify


def get_connection():
    """Creates a DecosJoin connection instance if there is none yet for the
    current application context.
    """

    return None


def success_response_json(response_content, response_code=200):
    return {"status": "OK", "content": response_content}, response_code


def error_response_json(message: str, code: int = 500):
    return {"status": "ERROR", "message": message}, code


def get_user_attributes(cls):
    boring = dir(type("dummy", (object,), {}))
    return [item for item in inspect.getmembers(cls) if item[0] not in boring]


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def format_currency(fval: str):
    return "€{:_.2f}".format(float(fval)).replace(".", ",").replace("_", ".")
