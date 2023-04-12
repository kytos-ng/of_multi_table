"""Test the Main class"""
from unittest import TestCase

from kytos.lib.helpers import get_controller_mock


class TestMain(TestCase):
    """Test the Main class"""

    def setUp(self):
        """Execute steps before each test"""
        from napps.kytos.of_multi_table.main import Main
        self.napp = Main(get_controller_mock)

    def test_temporal(self):
        """Temporal test to be removed later"""
        name = "Kytos"
        self.assertEqual("Kytos", name)
