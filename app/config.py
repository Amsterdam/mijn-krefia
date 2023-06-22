import logging
import logging.config
import os
from datetime import date, time

from flask.json.provider import DefaultJSONProvider

BASE_PATH = os.path.abspath(os.path.dirname(__file__))

# Sentry configuration.
SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENV = os.getenv("SENTRY_ENVIRONMENT")

# Environment determination
IS_PRODUCTION = SENTRY_ENV == "production"
IS_ACCEPTANCE = SENTRY_ENV == "acceptance"
IS_DEV = SENTRY_ENV == "development"
IS_TEST = SENTRY_ENV == "test"

IS_TAP = IS_PRODUCTION or IS_ACCEPTANCE or IS_TEST
IS_AP = IS_ACCEPTANCE or IS_PRODUCTION
IS_OT = IS_DEV or IS_TEST

# App constants
ENABLE_OPENAPI_VALIDATION = os.getenv("ENABLE_OPENAPI_VALIDATION", not IS_TAP)
VERIFY_JWT_SIGNATURE = os.getenv("VERIFY_JWT_SIGNATURE", IS_AP)

ALLEGRO_SOAP_ENDPOINT = os.getenv("ALLEGRO_SOAP_ENDPOINT", None)
ALLEGRO_SOAP_UA_STRING = "Mijn Amsterdam Krefia API"
ALLEGRO_EXCLUDE_OPDRACHTGEVER = os.getenv("ALLEGRO_EXCLUDE_OPDRACHTGEVER", "").split(
    ","
)
ALLEGRO_REQUEST_TIMEOUT = 60

KREFIA_SSO_KREDIETBANK = os.getenv("KREFIA_SSO_KREDIETBANK", "")
KREFIA_SSO_FIBU = os.getenv("KREFIA_SSO_FIBU", "")

# Set-up logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "ERROR").upper()

logging.basicConfig(
    format="%(asctime)s,%(msecs)d %(levelname)-8s [%(pathname)s:%(lineno)d in function %(funcName)s] %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=LOG_LEVEL,
)


def get_allegro_service_description(service_name: str):
    return get_allegro_service_endpoint(service_name)


def get_allegro_service_endpoint(service_name: str):
    return f"{ALLEGRO_SOAP_ENDPOINT}?service={service_name}"


class UpdatedJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, time):
            return obj.isoformat(timespec="minutes")

        if isinstance(obj, date):
            return obj.isoformat()

        return super().default(obj)
