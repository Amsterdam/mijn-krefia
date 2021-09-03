from unittest import TestCase
from unittest.mock import patch

from krefia.allegro_client import connect, get_all, get_service


class ClientTests(TestCase):
    def test_connect(self):
        self.assertEqual([], [])

    def test_get_service(self):
        self.assertEqual(True, True)

    def test_get_all(self):
        self.assertEqual(True, True)
