import functools
import logging
import os

from azure.monitor.opentelemetry import configure_azure_monitor
from flask import Flask, request
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.trace import get_tracer_provider
from requests.exceptions import HTTPError

from app import allegro_client
from app.config import (
    IS_DEV,
    DEV_API_KEY,
    API_KEY,
    UpdatedJSONProvider,
    get_application_insights_connection_string,
)
from app.helpers import error_response_json, success_response_json

if not IS_DEV and API_KEY == DEV_API_KEY:
    raise Exception("DEV_API_KEY is used as API_KEY outside of development")

# See also: https://medium.com/@tedisaacs/auto-instrumenting-python-fastapi-and-monitoring-with-azure-application-insights-768a59d2f4b9
if get_application_insights_connection_string():
    configure_azure_monitor()

tracer = trace.get_tracer(__name__, tracer_provider=get_tracer_provider())
app = Flask(__name__)
app.json = UpdatedJSONProvider(app)

FlaskInstrumentor.instrument_app(app)


def api_key_auth(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        try:
            incoming_api_key = request.headers["x-api-key"]
        except KeyError:
            return error_response_json("required header x-api-key not found.", code=401)
        if incoming_api_key != API_KEY:
            return error_response_json(
                "Value of header 'x-api-key' is invalid.", code=401
            )

        return fn(*args, **kwargs)

    return inner


def ensure_bsn(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        data = request.get_json(force=True)
        try:
            bsn = data["bsn"]
        except KeyError:
            return error_response_json("required field bsn not found.", code=400)
        request.bsn = bsn
        return fn(*args, **kwargs)

    return inner


@app.route("/krefia/all", methods=["POST"])
@api_key_auth
@ensure_bsn
def get_all():
    with tracer.start_as_current_span("/all"):
        content = allegro_client.get_all(request.bsn)
        return success_response_json(content)


@app.route("/")
@app.route("/status/health")
def health_check():
    return success_response_json(
        {
            "gitSha": os.getenv("MA_GIT_SHA", -1),
            "buildId": os.getenv("MA_BUILD_ID", -1),
            "otapEnv": os.getenv("MA_OTAP_ENV", None),
        }
    )


@app.errorhandler(Exception)
def handle_error(error):
    error_message_original = f"{type(error)}:{str(error)}"

    msg_request_http_error = "Request error occurred"
    msg_server_error = "Server error occurred"

    logging.exception(error, extra={"error_message_original": error_message_original})

    if IS_DEV:  # pragma: no cover
        msg_request_http_error = error_message_original
        msg_server_error = error_message_original

    if isinstance(error, HTTPError):
        return error_response_json(
            msg_request_http_error,
            error.response.status_code,
        )

    return error_response_json(
        msg_server_error,
        error.code if hasattr(error, "code") else 500,
    )


if __name__ == "__main__":  # pragma: no cover
    app.run()
