"""Test the Main class"""
from unittest import TestCase

from kytos.lib.helpers import get_controller_mock, get_test_client
from napps.kytos.of_multi_table.main import Main


class TestMain(TestCase):
    """Test the Main class"""

    API_URL = "http://localhost:8181/api/kytos/of_multi_table"

    def setUp(self):
        """Execute steps before each test"""
        self.napp = Main(get_controller_mock())

    def test_add_pipeline(self):
        """Test adding a pipeline"""
        payload = {
            "status": "disabled",
            "multi_table": [{
                    "description": "Table for testing",
                    "table_miss_flow": {
                        "priority": 0,
                        "match": {},
                        "instructions": [{
                            "instruction_type": "goto_table",
                            "table_id": 1
                        }]
                    },
                    "napps_table_groups": {
                        "of_lldp": ["base"]
                    }
                },
            ]
        }
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v1/pipeline"
        response = api.post(url, json=payload)
        self.assertEqual(response.status_code, 200)

    def test_add_pipeline_error_empty_json(self):
        """Test adding pipeline with an empty JSON"""
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v1/pipeline"
        response = api.post(url, json={})
        self.assertEqual(response.status_code, 400)

    def test_add_pipeline_error_empty_content(self):
        """Test adding pipeline with no content"""
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v1/pipeline"
        response = api.post(url)
        self.assertEqual(response.status_code, 415)

    def test_list_pipelines(self):
        """Test list pipelines"""
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v1/pipeline"
        response = api.get(url)
        self.assertEqual(response.status_code, 200)

    def test_get_pipeline(self):
        """Test get a pipeline"""
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}"
        response = api.get(url)
        self.assertEqual(response.status_code, 200)

    def test_delete_pipeline(self):
        """Test delete a pipeline"""
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}"
        response = api.delete(url)
        self.assertEqual(response.status_code, 200)

    def test_enable_pipeline(self):
        """Test enable a pipeline"""
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}/enable"
        response = api.post(url)
        self.assertEqual(response.status_code, 201)

    def test_disable_pipeline(self):
        """Test disable a pipeline"""
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}/disable"
        response = api.post(url)
        self.assertEqual(response.status_code, 201)
