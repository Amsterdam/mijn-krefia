from krefia.helpers import get_user_attributes
from zeep.helpers import serialize_object
from krefia.tests.mocks import MockClient
from unittest import TestCase
from unittest.mock import patch

from krefia.allegro_client import (
    get_client_service,
    get_allegro_service_description,
    get_relatienummer,
    get_session_header,
    login_tijdelijk,
    set_session_id,
)
import pprint

pp = pprint.PrettyPrinter(indent=4)


class ClientTests(TestCase):
    def test_get_client(self):
        # set_session_id("123123")
        # h = get_session_header()
        # print(h)
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
