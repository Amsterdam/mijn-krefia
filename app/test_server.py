from unittest import mock
from app.fixtures.mocks import mock_client, mock_clients
from unittest.mock import patch


from tma_saml import FlaskServerTMATestCase
from tma_saml.for_tests.cert_and_key import server_crt

from app import config

config.KREFIA_SSO_KREDIETBANK = "https://localhost/kredietbank/sso-login"
config.KREFIA_SSO_FIBU = "https://localhost/fibu/sso-login"
config.ALLEGRO_SOAP_ENDPOINT = "https://localhost/SOAP"

from app.server import app


@patch("app.helpers.get_tma_certificate", lambda: server_crt)
class ApiTests(FlaskServerTMATestCase):
    TEST_BSN = "111222333"

    def setUp(self):
        self.client = self.get_tma_test_app(app)
        self.maxDiff = None

    def get_secure(self, location):
        return self.client.get(location, headers=self.saml_headers())

    def saml_headers(self):
        return self.add_digi_d_headers(self.TEST_BSN)

    def test_status(self):
        response = self.client.get("/status/health")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "OK")
        self.assertEqual(data["content"], "OK")

    def mock_response(*args, **kwargs):
        return {"body": {"FOo": "Barrr"}}

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client(
            "LoginService",
            [
                "AllegroWebLoginTijdelijk",
                ("BSNNaarRelatieMetBedrijf", mock_response),
                "AllegroWebMagAanmelden",
            ],
        ),
    )
    def test_get_all_no_relaties(self):
        response = self.get_secure("/krefia/all")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        expected_content = None

        self.assertEqual(data["status"], "OK")
        self.assertEqual(data["content"], expected_content)

    def no_login(*args, **kwargs):
        return None

    @mock.patch(
        "app.allegro_client.allegro_client",
        mock_client(
            "LoginService",
            [
                ("AllegroWebLoginTijdelijk", no_login),
            ],
        ),
    )
    def test_get_all_no_login(self):
        response = self.get_secure("/krefia/all")
        self.assertEqual(response.status_code, 500)
        data = response.get_json()

        self.assertEqual(data["status"], "ERROR")
        self.assertFalse("content" in data)

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
                        "GetSRVAanvraag",
                        "GetSRVOverzicht",
                    ],
                ),
                (
                    "FinancieringService",
                    ["GetPLOverzicht", "GetPL"],
                ),
                ("BBRService", [("GetBBROverzicht", mock_no_result)]),
                ("BerichtenBoxService", [("GetBerichten", mock_no_result)]),
            ]
        ),
    )
    def test_get_all_response_variations(self):
        response = self.get_secure("/krefia/all")
        data = response.get_json()

        expected = {
            "content": {
                "deepLinks": {
                    "budgetbeheer": None,
                    "lening": {
                        "title": "U hebt € 1.600,- geleend. Hierop moet u iedere maand € 46,92 aflossen.",
                        "url": "https://localhost/kredietbank/sso-login",
                    },
                    "schuldhulp": {
                        "title": "Afkoopvoorstellen zijn verstuurd",
                        "url": "https://localhost/kredietbank/sso-login",
                    },
                },
                "notificationTriggers": None,
            },
            "status": "OK",
        }

        self.assertEqual(data, expected)

    def test_not_authenticated(self):
        response = self.client.get("/krefia/all")
        data = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "ERROR")
        self.assertEqual(data["message"], "TMA error occurred")
        self.assertEqual("content" not in data, True)
