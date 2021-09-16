import logging
import pprint
from unittest import TestCase, mock

from krefia import config
from krefia.allegro_client import (
    call_service_method,
    get_relatiecode_bedrijf,
    get_schuldhulp_title,
    get_service,
    get_session_header,
    get_session_id,
    login_allowed,
    login_tijdelijk,
    set_session_id,
)
from krefia.helpers import dotdict
from krefia.tests.mocks import mock_client

pp = pprint.PrettyPrinter(indent=4)

config.ALLEGRO_SOAP_ENDPOINT = "https://localhost/SOAP"


class ClientTests(TestCase):
    def get_service_mocks():
        return {
            "service1": dotdict({"service": "Foo"}),
            "service2": dotdict({"service": "Bar"}),
        }

    @mock.patch("krefia.allegro_client.allegro_client", get_service_mocks())
    def test_get_service(self):
        self.assertEqual(get_service("service1"), "Foo")
        self.assertEqual(get_service("service2"), "Bar")

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client("FakeService", ["fake_method"]),
    )
    def test_session_id(self):
        session_id = "__test-session-id__"
        set_session_id(session_id)
        self.assertEqual(get_session_id(), session_id)

        header = get_session_header("FakeService")[0]
        self.assertTrue("ID" in header.__dict__)
        self.assertEqual(header.ID, session_id)

    fake_client = dotdict(
        {
            "service3": dotdict(
                {
                    "service": dotdict(
                        {"method1": mock.Mock(return_value={"body": "foo"})}
                    )
                }
            )
        }
    )

    @mock.patch("krefia.allegro_client.logger")
    @mock.patch("krefia.allegro_client.allegro_client", fake_client)
    def test_call_service_method(self, logger_mock):
        response = call_service_method("service3.method1", "bar")

        self.assertEqual(response, "foo")
        self.fake_client.service3.service.method1.assert_called_with(
            "bar", _soapheaders=[]
        )
        logger_mock.debug.assert_called_with({"body": "foo"})

        response = call_service_method("service3.method2", "bar")
        logger_mock.error.assert_called_with(
            "Could not execute service method: 'NoneType' object is not callable"
        )
        self.assertIsNone(response)

        response = call_service_method("service3b.method2")
        logger_mock.error.assert_called_with("service3b.method2, no service.")
        self.assertIsNone(response)

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client("LoginService", ["AllegroWebLoginTijdelijk"]),
    )
    def test_login_tijdelijk(self):
        response = login_tijdelijk()
        self.assertEqual(response, True)
        self.assertEqual(get_session_id(), "{43B7DD35-848E-4F52-B90A-6D2E4071D9C6}")

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client("LoginService", ["BSNNaarRelatieMetBedrijf"]),
    )
    def test_get_relatiecode_bedrijf(self):
        bsn = "__test_bsn_123__"
        response = get_relatiecode_bedrijf(bsn)

        response_expected = {"FIBU": "321321", "KREDIETBANK": "123123"}

        self.assertEqual(response, response_expected)

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client("LoginService", ["AllegroWebMagAanmelden"]),
    )
    def test_login_allowed(self):
        relatiecode = "123__123"
        response = login_allowed(relatiecode)

        self.assertEqual(response, True)

    def test_get_schuldhulp_title(self):
        aanvraag_source = {
            "Eindstatus": None,
            "Status": None,
            "ExtraStatus": None,
        }
        title = get_schuldhulp_title(aanvraag_source)

        aanvraag_source = {
            "Eindstatus": "Z",
            "Status": "E",
            "ExtraStatus": "Voorlopig afgewezen",
        }
        title = get_schuldhulp_title(aanvraag_source)

        aanvraag_source = {
            "Eindstatus": None,
            "Status": "C",
            "ExtraStatus": "Voorlopig afgewezen",
        }
        title = get_schuldhulp_title(aanvraag_source)

        self.assertEqual(title, "Dwangprocedure loopt")

        aanvraag_source = {
            "Eindstatus": None,
            "Status": "C",
            "ExtraStatus": "Aanvraag beperkt",
        }
        title = get_schuldhulp_title(aanvraag_source)

        self.assertEqual(title, "Schuldhoogte wordt opgevraagd")

    def test_get_all(self):
        self.assertEqual(True, True)
