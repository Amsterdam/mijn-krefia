import datetime
import pprint
from unittest import TestCase, mock
from flask import Flask
from freezegun import freeze_time
from app import config

config.KREFIA_SSO_KREDIETBANK = "https://localhost/kredietbank/sso-login"
config.KREFIA_SSO_FIBU = "https://localhost/fibu/sso-login"
config.ALLEGRO_SOAP_ENDPOINT = "https://localhost/SOAP"

from app.allegro_client import (
    bedrijf,
    call_service_method,
    get_all,
    get_budgetbeheer,
    get_lening,
    get_leningen,
    get_notification,
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
    notification_urls,
    set_session_id,
)
from app.helpers import dotdict
from app.fixtures.mocks import mock_client, mock_clients

pp = pprint.PrettyPrinter(indent=4)


class FlaskTestCase(TestCase):
    app = Flask(__name__)

    def setUp(self) -> None:
        self.app.config["TESTING"] = True


class ClientTests(FlaskTestCase):
    @classmethod
    def tearDownClass(self):
        with self.app.test_request_context():
            set_session_id(None)

    def get_service_mocks():
        return {
            "service1": dotdict({"service": "Foo"}),
            "service2": dotdict({"service": "Bar"}),
        }

    @mock.patch("app.allegro_client.allegro_client", get_service_mocks())
    def test_get_service(self):
        with self.app.test_request_context():
            self.assertEqual(get_service("service1"), "Foo")
            self.assertEqual(get_service("service2"), "Bar")

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client("FakeService", ["fake_method"]),
    )
    def test_session_id(self):
        session_id = "__test-session-id__"

        with self.app.test_request_context():
            set_session_id(session_id)
            sess_id = get_session_id()

            self.assertEqual(sess_id, session_id)
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

    @mock.patch("app.allegro_client.logging")
    @mock.patch("app.allegro_client.allegro_client", fake_client)
    def test_call_service_method(self, logging_mock):
        with self.app.test_request_context():
            content = call_service_method("service3.method1", "bar")

        self.assertEqual(content, "foo")
        self.fake_client.service3.service.method1.assert_called_with(
            "bar", _soapheaders=[]
        )
        logging_mock.debug.assert_called_with({"body": "foo"})

        with self.app.test_request_context():
            content = call_service_method("service3.method2", "bar")

        logging_mock.error.assert_called_with(
            "Could not execute service operation: service3.method2, error: 'NoneType' object is not callable"
        )
        self.assertIsNone(content)

        with self.app.test_request_context():
            content = call_service_method("service3b.method2")

        logging_mock.error.assert_called_with("service3b.method2, no service.")
        self.assertIsNone(content)

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client("LoginService", ["AllegroWebLoginTijdelijk"]),
    )
    def test_login_tijdelijk(self):
        with self.app.test_request_context():
            content = login_tijdelijk()
            self.assertEqual(content, True)
            self.assertEqual(get_session_id(), "{43B7DD35-848E-4F52-B90A-6D2E4071D9C6}")

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client("LoginService", ["BSNNaarRelatieMetBedrijf"]),
    )
    def test_get_relatiecode_bedrijf(self):
        bsn = "__test_bsn_123__"
        with self.app.test_request_context():
            content = get_relatiecode_bedrijf(bsn)

        content_expected = {"FIBU": "321321", "KREDIETBANK": "123123"}

        self.assertEqual(content, content_expected)

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client("LoginService", ["AllegroWebMagAanmelden"]),
    )
    def test_login_allowed(self):
        relatiecode = "123__123"
        with self.app.test_request_context():
            content = login_allowed(relatiecode)

        self.assertEqual(content, True)

    def test_get_result(self):
        content_test = {"Result": None}
        result = get_result(content_test, "Foo")
        self.assertEqual(result, None)

        content_test = {"Result": None}
        result = get_result(content_test, "Foo", {})
        self.assertEqual(result, {})

        content_test = {"Result": {"Foo": "Bar"}}
        result = get_result(content_test, "Foo")
        self.assertEqual(result, "Bar")


class SchuldHulpTests(FlaskTestCase):
    srv_aanvraag_result = mock.Mock(
        return_value={
            "body": {
                "Result": {
                    "Eindstatus": None,
                }
            }
        }
    )
    srv_aanvraag_result2 = mock.Mock(
        return_value={
            "body": {
                "Result": {
                    "Eindstatus": None,
                    "Opdrachtgever": "123123123",
                }
            }
        }
    )

    srv_header = {
        "RelatieCode": 2442531,
        "Volgnummer": 2,
        "IsNPS": False,
        "Status": "E",
        "Statustekst": "Derde fiattering akkoord- wacht op accoord client.",
        "Aanvraagdatum": datetime.datetime(2020, 6, 22, 0, 0),
        "ExtraStatus": None,
    }

    srv_overzicht_result = mock.Mock(
        return_value={
            "body": {
                "Result": {
                    "TSRVAanvraagHeader": [
                        srv_header,
                    ]
                }
            }
        }
    )

    def test_get_schuldhulp_title(self):
        aanvraag_source = {
            "eind_status": None,
            "status": None,
            "extra_status": None,
        }
        title = get_schuldhulp_title(**aanvraag_source)
        self.assertEqual(title, "Lopend")

        aanvraag_source = {
            "eind_status": "I",
            "status": "E",
            "extra_status": "Voorlopig afgewezen",
        }
        title = get_schuldhulp_title(**aanvraag_source)
        self.assertEqual(title, "Schuldeisers akkoord")

        for eind_status in ["T", "U", "V", "W", "X", "Y", "Z"]:
            aanvraag_source = {
                "eind_status": eind_status,
                "status": "E",
                "extra_status": "Voorlopig afgewezen",
            }
            title = get_schuldhulp_title(**aanvraag_source)
            self.assertEqual(title, "Aanvraag afgewezen")

        aanvraag_source = {
            "eind_status": None,
            "status": "C",
            "extra_status": "Voorlopig afgewezen",
        }
        title = get_schuldhulp_title(**aanvraag_source)
        self.assertEqual(title, "Dwangprocedure loopt")

        for status in ["A"]:
            aanvraag_source = {
                "eind_status": None,
                "status": status,
                "extra_status": None,
            }
            title = get_schuldhulp_title(**aanvraag_source)
            self.assertEqual(title, "Inventariseren ingediende aanvraag")

        for status in ["B", "C", "D"]:
            aanvraag_source = {
                "eind_status": None,
                "status": status,
                "extra_status": None,
            }
            title = get_schuldhulp_title(**aanvraag_source)
            self.assertEqual(title, "Schuldhoogte wordt opgevraagd")

        for status in ["E", "F", "G"]:
            aanvraag_source = {
                "eind_status": None,
                "status": status,
                "extra_status": None,
            }
            title = get_schuldhulp_title(**aanvraag_source)
            self.assertEqual(title, "Afkoopvoorstellen zijn verstuurd")

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client("SchuldHulpService", [("GetSRVAanvraag", srv_aanvraag_result)]),
    )
    def test_get_schuldhulp_aanvraag(self):
        with self.app.test_request_context():
            content = get_schuldhulp_aanvraag(self.srv_header)

        tsrv_header = self.srv_aanvraag_result.call_args[0][0]
        self.assertTrue("Volgnummer" in tsrv_header.__dict__)
        self.assertEqual(tsrv_header.Volgnummer, 2)

        self.assertEqual(
            content,
            {
                "title": "Afkoopvoorstellen zijn verstuurd",
                "url": config.KREFIA_SSO_KREDIETBANK,
            },
        )

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client("SchuldHulpService", [("GetSRVAanvraag", srv_aanvraag_result2)]),
    )
    @mock.patch(
        "app.allegro_client.ALLEGRO_EXCLUDE_OPDRACHTGEVER",
        ["123123123"],
    )
    def test_get_schuldhulp_aanvraag_exclude_opdrachtgever(self):
        with self.app.test_request_context():
            content = get_schuldhulp_aanvraag(self.srv_header)

        tsrv_header = self.srv_aanvraag_result2.call_args[0][0]
        self.assertTrue("Volgnummer" in tsrv_header.__dict__)
        self.assertEqual(tsrv_header.Volgnummer, 2)

        self.assertEqual(
            content,
            None,
        )

    @mock.patch(
        "app.allegro_client.allegro_client",
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
        with self.app.test_request_context():
            content = get_schuldhulp_aanvragen(relatiecode_fibu)

        self.srv_overzicht_result.assert_called_with(relatiecode_fibu, _soapheaders=[])
        self.assertEqual(self.srv_aanvraag_result.call_count, 1)

        tsrv_header = self.srv_aanvraag_result.call_args[0][0]
        self.assertTrue("Volgnummer" in tsrv_header.__dict__)
        self.assertEqual(tsrv_header.Volgnummer, 2)

        self.assertEqual(
            content,
            [
                {
                    "title": "Afkoopvoorstellen zijn verstuurd",
                    "url": config.KREFIA_SSO_KREDIETBANK,
                },
            ],
        )


class LeningBudgetbeheerTests(FlaskTestCase):
    pl_overzicht_result = mock.Mock(
        return_value={"body": {"Result": {"TPLHeader": [{"ID": 99}, {"ID": 88}]}}}
    )

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client("FinancieringService", ["GetPL"]),
    )
    def test_get_lening(self):
        tpl_header = {}
        with self.app.test_request_context():
            content = get_lening(tpl_header)

        content_expected = {
            "title": "U hebt € 1.600,- geleend. Hierop moet u iedere maand € 46,92 aflossen.",
            "url": config.KREFIA_SSO_KREDIETBANK,
        }
        self.assertEqual(content, content_expected)

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client(
            "FinancieringService", [("GetPLOverzicht", pl_overzicht_result), "GetPL"]
        ),
    )
    def test_get_leningen(self):
        relatiecode_kredietbank = "__777__888__"
        with self.app.test_request_context():
            content = get_leningen(relatiecode_kredietbank)

        self.pl_overzicht_result.assert_called_with(
            relatiecode_kredietbank, _soapheaders=[]
        )

        content_expected = [
            {
                "title": "U hebt € 1.600,- geleend. Hierop moet u iedere maand € 46,92 aflossen.",
                "url": config.KREFIA_SSO_KREDIETBANK,
            },
            {
                "title": "U hebt € 1.600,- geleend. Hierop moet u iedere maand € 46,92 aflossen.",
                "url": config.KREFIA_SSO_KREDIETBANK,
            },
        ]
        self.assertEqual(content, content_expected)

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client("BBRService", ["GetBBROverzicht"]),
    )
    def test_get_budgetbeheer(self):
        relatiecode_fibu = "__456__456__"

        with self.app.test_request_context():
            content = get_budgetbeheer(relatiecode_fibu)

        content_expected = [
            {
                "title": "Lopend",
                "url": config.KREFIA_SSO_FIBU,
            }
        ]
        self.assertEqual(content, content_expected)


class ClientTests2(FlaskTestCase):
    @classmethod
    def tearDownClass(self):
        with self.app.test_request_context():
            set_session_id(None)

    trigger_fibu = {
        "url": notification_urls[bedrijf.FIBU],
        "datePublished": "2021-11-03",
    }

    trigger_kredietbank = {
        "url": notification_urls[bedrijf.KREDIETBANK],
        "datePublished": "2021-11-03",
    }

    @freeze_time("2021-11-03")
    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client("BerichtenBoxService", ["GetBerichten"]),
    )
    def test_get_notification(self):
        relatiecode_fibu = "__123_fibu__"

        with self.app.test_request_context():
            content = get_notification(relatiecode_fibu, bedrijf.FIBU)

        self.assertEqual(content, self.trigger_fibu)

        relatiecode_kredietbank = "__123_kredietbank__"

        with self.app.test_request_context():
            content = get_notification(relatiecode_kredietbank, bedrijf.KREDIETBANK)

        self.assertEqual(content, self.trigger_kredietbank)

    @mock.patch(
        "app.allegro_client.allegro_client",
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
    @freeze_time("2021-11-03")
    def test_get_all1(self):

        self.maxDiff = None

        bsn = "_1_2_3_4_5_6_"
        with self.app.test_request_context():
            content = get_all(bsn)

        content_expected = {
            "deepLinks": {
                "budgetbeheer": {
                    "title": "Lopend",
                    "url": config.KREFIA_SSO_FIBU,
                },
                "lening": {
                    "title": "U hebt € 1.600,- geleend. Hierop moet u iedere maand € 46,92 aflossen.",
                    "url": config.KREFIA_SSO_KREDIETBANK,
                },
                "schuldhulp": {
                    "title": "Afkoopvoorstellen zijn verstuurd",
                    "url": config.KREFIA_SSO_KREDIETBANK,
                },
            },
            "notificationTriggers": {
                "fibu": {
                    "datePublished": "2021-11-03",
                    "url": config.KREFIA_SSO_FIBU,
                },
                "krediet": {
                    "datePublished": "2021-11-03",
                    "url": config.KREFIA_SSO_KREDIETBANK,
                },
            },
        }

        self.assertEqual(content, content_expected)

    mag_aanmelden_nee = mock.Mock(return_value={"body": {"Result": False}})

    def get_berichten(*args, **kwargs):
        return None

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_clients(
            [
                (
                    "LoginService",
                    [
                        "AllegroWebLoginTijdelijk",
                        "BSNNaarRelatieMetBedrijf",
                        ("AllegroWebMagAanmelden", mag_aanmelden_nee),
                    ],
                ),
                (
                    "BerichtenBoxService",
                    [
                        ("GetBerichten", get_berichten),
                    ],
                ),
            ],
        ),
    )
    def test_get_all_happy_no_items(self):
        bsn = "_1_2_3_4_5_6_"

        with self.app.test_request_context():
            content = get_all(bsn)

        expected_content = None

        self.assertEqual(content, expected_content)

    mag_aanmelden_ja = mock.Mock(return_value={"body": {"Result": True}})

    def mock_no_result(*args, **kwargs):
        return {"body": {"Result": None}}

    @mock.patch(
        "app.allegro_client.allegro_client",
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
                (
                    "SchuldHulpService",
                    [
                        ("GetSRVAanvraag", mock_no_result),
                        ("GetSRVOverzicht", mock_no_result),
                    ],
                ),
                (
                    "FinancieringService",
                    [("GetPLOverzicht", mock_no_result), ("GetPL", mock_no_result)],
                ),
                ("BBRService", ["GetBBROverzicht"]),
                ("BerichtenBoxService", [("GetBerichten", mock_no_result)]),
            ]
        ),
    )
    def test_get_all_happy_some_item(self):
        bsn = "_1_2_3_4_5_6_"
        with self.app.test_request_context():
            content = get_all(bsn)

        expected_content = {
            "deepLinks": {
                "schuldhulp": None,
                "lening": None,
                "budgetbeheer": {
                    "title": "Lopend",
                    "url": config.KREFIA_SSO_FIBU,
                },
            },
            "notificationTriggers": None,
        }

        self.assertEqual(content, expected_content)

    def mock_content(*args, **kwargs):
        return {"body": {"Result": {"FOo": "Barrr"}}}

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client(
            "LoginService",
            [
                "AllegroWebLoginTijdelijk",
                ("BSNNaarRelatieMetBedrijf", mock_content),
                "AllegroWebMagAanmelden",
            ],
        ),
    )
    def test_get_all_no_relaties(self):
        bsn = "_1_2_3_4_5_6_"
        with self.app.test_request_context():
            content = get_all(bsn)

        expected_content = None

        self.assertEqual(content, expected_content)
