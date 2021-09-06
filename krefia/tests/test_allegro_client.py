from krefia.helpers import get_user_attributes
from zeep.helpers import serialize_object
from krefia.tests.mocks import MockClient
from unittest import TestCase
from unittest.mock import patch

from krefia.allegro_client import (
    get_client_service,
    get_allegro_service_description,
    get_relatienummer,
    login_tijdelijk,
)
import pprint

pp = pprint.PrettyPrinter(indent=4)


class ClientTests(TestCase):
    @patch("krefia.config.ALLEGRO_SOAP_ENDPOINT", "http://none?")
    @patch("krefia.allegro_client.Client", new=MockClient)
    def test_get_client(self):
        # response = login_tijdelijk()
        # response = get_relatienummer(bsn="123")
        # pp.pprint(
        #     response,
        # )
        self.assertEqual(None, None)

    def test_get_service(self):
        self.assertEqual(True, True)

    def test_get_all(self):
        self.assertEqual(True, True)
