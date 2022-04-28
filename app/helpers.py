import os
from functools import wraps

import yaml
from flask import g, request
from flask.helpers import make_response
from openapi_core import create_spec
from openapi_core.contrib.flask import FlaskOpenAPIRequest, FlaskOpenAPIResponse
from openapi_core.validation.request.validators import RequestValidator
from openapi_core.validation.response.validators import ResponseValidator

from app.config import BASE_PATH, ENABLE_OPENAPI_VALIDATION

openapi_spec = None


def get_openapi_spec():
    global openapi_spec
    if not openapi_spec:
        with open(os.path.join(BASE_PATH, "openapi.yml"), "r") as spec_file:
            spec_dict = yaml.load(spec_file, Loader=yaml.Loader)
        openapi_spec = create_spec(spec_dict)

    return openapi_spec


def validate_openapi(function):
    @wraps(function)
    def validate(*args, **kwargs):

        if ENABLE_OPENAPI_VALIDATION:
            spec = get_openapi_spec()
            openapi_request = FlaskOpenAPIRequest(request)
            validator = RequestValidator(spec)
            result = validator.validate(openapi_request)
            result.raise_for_errors()

        response = function(*args, **kwargs)

        if ENABLE_OPENAPI_VALIDATION:
            openapi_response = FlaskOpenAPIResponse(response)
            validator = ResponseValidator(spec)
            result = validator.validate(openapi_request, openapi_response)
            result.raise_for_errors()

        return response

    return validate


def success_response_json(response_content):
    return make_response({"status": "OK", "content": response_content}, 200)


def error_response_json(message: str, code: int = 500):
    return make_response({"status": "ERROR", "message": message}, code)


class dotdict(dict):
    """dot.notation access to dictionary attributes"""

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def format_currency(fval: str):
    return (
        "€ {:_.2f}".format(float(fval))
        .replace(".", ",")
        .replace("_", ".")
        .replace(",00", ",-")
    )
