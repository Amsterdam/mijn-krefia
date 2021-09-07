# Mock the soap client
import os
from requests import Response
from krefia.config import BASE_PATH
from unittest import mock

RESPONSES_PATH = os.path.join(BASE_PATH, "tests", "responses")


def load_fixture_as_bytes(file_name):
    with open(os.path.join(RESPONSES_PATH, file_name)) as fp:
        return bytes(fp.read(), encoding="utf8")


def mock_soap_response(file_name: str):
    def response(*args):
        r = Response()
        r.headers.setdefault("Content-type", "text/xml")
        r.status_code = 200
        response_content = load_fixture_as_bytes(file_name)
        type(r).content = mock.PropertyMock(return_value=response_content)
        return r

    return response
