import sentry_sdk
from flask import Flask
from requests.exceptions import HTTPError
from sentry_sdk.integrations.flask import FlaskIntegration

from app import allegro_client
from app.config import (
    IS_DEV,
    CustomJSONEncoder,
    TMAException,
    get_sentry_dsn,
    logger,
)
from app.helpers import (
    error_response_json,
    get_connection,
    get_tma_user,
    success_response_json,
    verify_tma_user,
)

app = Flask(__name__)
app.json_encoder = CustomJSONEncoder

sentry_dsn = get_sentry_dsn()
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn, integrations=[FlaskIntegration()], with_locals=False
    )


@app.route("/krefia/all", methods=["GET"])
@verify_tma_user
def get_all():
    user = get_tma_user()
    content = allegro_client.get_all(user["id"])

    if content is None:
        return success_response_json(None)

    return success_response_json(content)


@app.route("/status/health")
def health_check():
    return success_response_json("OK")


@app.errorhandler(Exception)
def handle_error(error):

    error_message_original = str(error)

    msg_tma_exception = "TMA error occurred"
    msg_request_http_error = "Request error occurred"
    msg_server_error = "Server error occurred"

    if not app.config["TESTING"]:
        logger.exception(
            error, extra={"error_message_original": error_message_original}
        )

    if IS_DEV:
        msg_tma_exception = error_message_original
        msg_request_http_error = error_message_original
        msg_server_error = error_message_original

    if isinstance(error, HTTPError):
        return error_response_json(
            msg_request_http_error,
            error.response.status_code,
        )
    elif isinstance(error, TMAException):
        return error_response_json(msg_tma_exception, 400)

    return error_response_json(msg_server_error, 500)


if __name__ == "__main__":
    app.run()
