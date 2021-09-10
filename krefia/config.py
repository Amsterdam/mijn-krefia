import logging
import logging.config
import os
import sys
import os.path
from datetime import date, time

from flask.json import JSONEncoder
from tma_saml.exceptions import (
    InvalidBSNException,
    SamlExpiredException,
    SamlVerificationException,
)

BASE_PATH = os.path.abspath(os.path.dirname(__file__))

# Use the Sentry environment
IS_PRODUCTION = os.getenv("SENTRY_ENVIRONMENT") == "production"
IS_ACCEPTANCE = os.getenv("SENTRY_ENVIRONMENT") == "acceptance"
IS_AP = IS_PRODUCTION or IS_ACCEPTANCE
IS_DEV = os.getenv("FLASK_ENV") == "development" and not IS_AP

TMAException = (SamlVerificationException, InvalidBSNException, SamlExpiredException)


logger = logging.getLogger(__name__)
stdout_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    handlers=[stdout_handler],
)

ALLEGRO_SOAP_ENDPOINT = os.getenv("ALLEGRO_SOAP_ENDPOINT", None)
ALLEGRO_SOAP_UA_STRING = "Mijn Amsterdam Krefia API"


def get_allegro_service_description(service_name: str):
    if service_name == "LoginService":
        return f"krefia/Allegro-{service_name}-modified.wsdl"

    return get_allegro_service_endpoint(service_name)


def get_allegro_service_endpoint(service_name: str):
    return f"{ALLEGRO_SOAP_ENDPOINT}?service={service_name}"


def get_sentry_dsn():
    return os.getenv("SENTRY_DSN", None)


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, time):
            return obj.isoformat(timespec="minutes")
        if isinstance(obj, date):
            return obj.isoformat()

        return JSONEncoder.default(self, obj)


# logging.config.dictConfig(
#     {
#         "version": 1,
#         "formatters": {
#             "verbose": {
#                 "format": "(%(process)d) %(asctime)s %(name)s (line %(lineno)s) | %(levelname)s %(message)s"
#             }
#         },
#         "handlers": {
#             "console": {
#                 "level": "DEBUG",
#                 "class": "logging.StreamHandler",
#                 "formatter": "verbose",
#                 "stream": sys.stdout,
#             },
#         },
#         "loggers": {
#             "zeep.transports": {
#                 "level": "DEBUG",
#                 "propagate": True,
#                 "handlers": ["console"],
#             },
#         },
#     }
# )
