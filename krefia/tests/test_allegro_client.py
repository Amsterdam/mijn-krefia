import pprint
from unittest import TestCase, mock

from krefia.allegro_client import (
    get_allegro_service_description,
    get_client_service,
    get_session_header,
    get_session_id,
    login_tijdelijk,
    set_session_id,
)
from krefia.tests.mocks import mock_soap_response

pp = pprint.PrettyPrinter(indent=4)


class ClientTests(TestCase):
    @mock.patch("krefia.config.ALLEGRO_SOAP_ENDPOINT", "https://localhost/SOAP")
    @mock.patch(
        "krefia.allegro_client.Transport.post",
        side_effect=mock_soap_response("LoginService.AllegroWebLoginTijdelijk.xml"),
    )
    def test_login_tijdelijk(self, magicMock):
        response = login_tijdelijk()
        self.assertEqual(response, True)
        self.assertEqual(get_session_id(), "{43B7DD35-848E-4F52-B90A-6D2E4071D9C6}")

    def test_get_service(self):
        self.assertEqual(True, True)

    def test_get_all(self):
        self.assertEqual(True, True)
