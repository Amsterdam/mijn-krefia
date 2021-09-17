from datetime import datetime
import logging
import pprint
from unittest import TestCase, mock

from krefia import config
from krefia.allegro_client import (
    call_service_method,
    get_all,
    get_budgetbeheer,
    get_lening,
    get_leningen,
    get_notification,
    get_notification_triggers,
    get_relatiecode_bedrijf,
    get_result,
    get_schuldhulp_aanvraag,
    get_schuldhulp_aanvragen,
    get_schuldhulp_title,
    get_service,
    get_session_header,
    get_session_id,
    login_allowed,
    login_tijdelijk,
    set_session_id,
    bedrijf,
    notification_urls,
)
from krefia.helpers import dotdict
from krefia.tests.mocks import mock_client, mock_clients

pp = pprint.PrettyPrinter(indent=4)

config.ALLEGRO_SOAP_ENDPOINT = "https://localhost/SOAP"


class ClientTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        set_session_id(None)

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

    def test_get_result(self):
        response_test = {"Result": None}
        result = get_result(response_test, "Foo")
        self.assertEqual(result, None)

        response_test = {"Result": None}
        result = get_result(response_test, "Foo", {})
        self.assertEqual(result, {})

        response_test = {"Result": {"Foo": "Bar"}}
        result = get_result(response_test, "Foo")
        self.assertEqual(result, "Bar")


class SchuldHulpTests(TestCase):
    srv_aanvraag_result = mock.Mock(
        return_value={
            "body": {
                "Result": {
                    "TSRVAanvraag": {
                        "Volgnummer": 1,
                        "RelatieCode": "blap",
                        "Eindstatus": None,
                        "Status": "C",
                        "ExtraStatus": "Voorlopig afgewezen",
                    }
                }
            }
        }
    )

    srv_overzicht_result = mock.Mock(
        return_value={
            "body": {"Result": {"TSRVAanvraagHeader": [{"ID": 1}, {"ID": 2}]}}
        }
    )

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

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client("SchuldHulpService", [("GetSRVAanvraag", srv_aanvraag_result)]),
    )
    def test_get_schuldhulp_aanvraag(self):
        aanvraag_header = {"Foo": "Bar"}
        response = get_schuldhulp_aanvraag(aanvraag_header)

        self.srv_aanvraag_result.assert_called_with(aanvraag_header, _soapheaders=[])

        self.assertEqual(
            response, {"title": "Dwangprocedure loopt", "url": "http://host/srv/blap/1"}
        )

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client(
            "SchuldHulpService",
            [
                ("GetSRVOverzicht", srv_overzicht_result),
                ("GetSRVAanvraag", srv_aanvraag_result),
            ],
        ),
    )
    def test_get_schuldhulp_aanvragen(self):
        self.srv_aanvraag_result.reset_mock()

        relatiecode_fibu = "__456__456__"
        response = get_schuldhulp_aanvragen(relatiecode_fibu)

        self.srv_overzicht_result.assert_called_with(relatiecode_fibu, _soapheaders=[])
        self.assertEqual(self.srv_aanvraag_result.call_count, 2)
        self.assertEqual(
            self.srv_aanvraag_result.call_args_list,
            [
                mock.call({"ID": 1}, _soapheaders=[]),
                mock.call({"ID": 2}, _soapheaders=[]),
            ],
        )

        self.assertEqual(
            response,
            [
                {"title": "Dwangprocedure loopt", "url": "http://host/srv/blap/1"},
                {"title": "Dwangprocedure loopt", "url": "http://host/srv/blap/1"},
            ],
        )


class LeningBudgetbeheerTests(TestCase):
    pl_overzicht_result = mock.Mock(
        return_value={"body": {"Result": {"TPLHeader": [{"ID": 99}, {"ID": 88}]}}}
    )

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client("FinancieringService", ["GetPL"]),
    )
    def test_get_lening(self):
        tpl_header = {}
        response = get_lening(tpl_header)

        response_expected = {
            "title": "Kredietsom 1689.12  met openstaand termijnbedrag 79.66",
            "url": "http://host/pl/321321/1",
        }
        self.assertEqual(response, response_expected)

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client(
            "FinancieringService", [("GetPLOverzicht", pl_overzicht_result), "GetPL"]
        ),
    )
    def test_get_leningen(self):
        relatiecode_kredietbank = "__777__888__"
        response = get_leningen(relatiecode_kredietbank)

        self.pl_overzicht_result.assert_called_with(
            relatiecode_kredietbank, _soapheaders=[]
        )

        response_expected = [
            {
                "title": "Kredietsom 1689.12  met openstaand termijnbedrag 79.66",
                "url": "http://host/pl/321321/1",
            },
            {
                "title": "Kredietsom 1689.12  met openstaand termijnbedrag 79.66",
                "url": "http://host/pl/321321/1",
            },
        ]
        self.assertEqual(response, response_expected)

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client("BBRService", ["GetBBROverzicht"]),
    )
    def test_get_budgetbeheer(self):
        relatiecode_fibu = "__456__456__"
        response = get_budgetbeheer(relatiecode_fibu)

        response_expected = [
            {
                "title": "Beheer uw budget op FiBu",
                "url": "http://host/bbr/123123123/3",
            }
        ]
        self.assertEqual(response, response_expected)


class ClientTests2(TestCase):
    @classmethod
    def tearDownClass(cls):
        set_session_id(None)

    trigger_fibu = {
        "url": notification_urls[bedrijf.FIBU],
        "datePublished": "2021-07-14T12:34:17",
    }

    trigger_kredietbank = {
        "url": notification_urls[bedrijf.KREDIETBANK],
        "datePublished": "2021-07-14T12:34:17",
    }

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client("BerichtenBoxService", ["GetBerichten"]),
    )
    def test_get_notification(self):
        relatiecode_fibu = "__123_fibu__"
        response = get_notification(relatiecode_fibu, bedrijf.FIBU)

        self.assertEqual(response, self.trigger_fibu)

        relatiecode_kredietbank = "__123_kredietbank__"
        response = get_notification(relatiecode_kredietbank, bedrijf.KREDIETBANK)

        self.assertEqual(response, self.trigger_kredietbank)

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_client("BerichtenBoxService", ["GetBerichten"]),
    )
    def test_get_notification_triggers(self):
        relaties = {
            bedrijf.FIBU: "123123",
            bedrijf.KREDIETBANK: "890678",
        }
        response = get_notification_triggers(relaties)

        response_expected = {
            "fibu": self.trigger_fibu,
            "krediet": self.trigger_kredietbank,
        }

        self.assertEqual(response, response_expected)

    @mock.patch(
        "krefia.allegro_client.allegro_client",
        mock_clients(
            [
                (
                    "LoginService",
                    [
                        "AllegroWebMagAanmelden",
                        "BSNNaarRelatieMetBedrijf",
                        "AllegroWebLoginTijdelijk",
                    ],
                ),
                ("SchuldHulpService", ["GetSRVAanvraag", "GetSRVOverzicht"]),
                ("FinancieringService", ["GetPLOverzicht", "GetPL"]),
                ("BBRService", ["GetBBROverzicht"]),
                ("BerichtenBoxService", ["GetBerichten"]),
            ]
        ),
    )
    def test_get_all1(self):

        self.maxDiff = None

        bsn = "_1_2_3_4_5_6_"
        response = get_all(bsn)

        response_expected = {
            "deepLinks": {
                "budgetbeheer": [
                    {
                        "title": "Beheer uw budget op FiBu",
                        "url": "http://host/bbr/123123123/3",
                    }
                ],
                "lening": [
                    {
                        "title": "Kredietsom 1689.12  met openstaand termijnbedrag 79.66",
                        "url": "http://host/pl/321321/1",
                    }
                ],
                "schuldhulp": [],
            },
            "notificationTriggers": {
                "fibu": {
                    "datePublished": "2021-07-14T12:34:17",
                    "url": "http://host/berichten/fibu",
                },
                "krediet": {
                    "datePublished": "2021-07-14T12:34:17",
                    "url": "http://host/berichten/kredietbank",
                },
            },
        }

        self.assertEqual(response, response_expected)
