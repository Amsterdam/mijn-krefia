# Mock the soap client
import os

from krefia.config import BASE_PATH

RESPONSES_PATH = os.path.join(BASE_PATH, "tests", "responses")


class MockClient:
    def __init__(self, wsdl, transport):
        self.service = MockService()

    def settings(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockService:
    def AllegroWebLoginTijdelijk(self):
        return MockResponse(reply=load_fixture_as_bytes("AllegroWebLoginTijdelijk.xml"))


class MockResponse:
    def __init__(self, reply, status_code=200):
        self.reply = reply
        self.status_code = status_code

    @property
    def content(self):
        return self.reply

    @property
    def data(self):
        return self.reply

    def json(self):
        return self.data


def load_fixture_as_bytes(file_name):
    with open(os.path.join(RESPONSES_PATH, file_name)) as fp:
        return fp.read()
