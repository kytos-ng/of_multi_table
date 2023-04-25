"""Test the Main class"""
from unittest.mock import MagicMock

from pydantic import BaseModel, ValidationError
from werkzeug.exceptions import NotFound
from kytos.lib.helpers import get_controller_mock, get_test_client
from napps.kytos.of_multi_table.main import Main


class TestMain():
    """Test the Main class"""

    API_URL = "http://localhost:8181/api/kytos/of_multi_table"

    def setup_method(self):
        """Execute steps before each test"""
        Main.get_pipeline_controller = MagicMock()
        self.napp = Main(get_controller_mock())

    def test_add_pipeline(self):
        """Test adding a pipeline"""
        payload = {
            "status": "disabled",
            "multi_table": [{
                    "table_id": 0,
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
        self.napp.pipeline_controller.insert_pipeline.return_value = "mock_id"
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v1/pipeline"
        response = api.post(url, json=payload)
        assert response.status_code == 201

    def test_add_pipeline_error_empty_json(self):
        """Test adding pipeline with an empty JSON"""
        payload = {
            "multi_table": [{"table_id": 299}]
        }
        controller = self.napp.pipeline_controller
        controller.insert_pipeline.side_effect = ValidationError('', BaseModel)
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v1/pipeline"
        response = api.post(url, json=payload)
        assert response.status_code == 400

    def test_add_pipeline_error_empty_content(self):
        """Test adding pipeline with no content"""
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v1/pipeline"
        response = api.post(url)
        assert response.status_code == 415

    def test_list_pipelines(self):
        """Test list pipelines"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipeline": []}
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v1/pipeline"
        response = api.get(url)
        assert response.status_code == 200

    def test_get_pipeline(self):
        """Test get a pipeline"""
        self.napp.pipeline_controller.get_pipeline.return_value = {
            "test": "pipeline"
        }
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}"
        response = api.get(url)
        assert response.status_code == 200

    def test_get_pipeline_not_found(self):
        """Test get a pipeline with Not found error"""
        self.napp.pipeline_controller.get_pipeline.return_value = None
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}"
        response = api.get(url)
        assert response.status_code == 404

    def test_delete_pipeline(self):
        """Test delete a pipeline"""
        self.napp.pipeline_controller.delete_pipeline.return_value = 1
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}"
        response = api.delete(url)
        assert response.status_code == 200

    def test_delete_pipeline_not_found(self):
        """Test delete a pipeline with NotFound error"""
        self.napp.pipeline_controller.delete_pipeline.return_value = 0
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}"
        response = api.delete(url)
        assert response.status_code == 404

    def test_enable_pipeline(self):
        """Test enable a pipeline"""
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}/enable"
        response = api.post(url)
        assert response.status_code == 200

    def test_enable_pipeline(self):
        """Test enable a pipeline with NotFound error"""
        self.napp.pipeline_controller.update_status.side_effect = NotFound
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}/enable"
        response = api.post(url)
        assert response.status_code == 404

    def test_disable_pipeline(self):
        """Test disable a pipeline"""
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}/disable"
        response = api.post(url)
        assert response.status_code == 200

    def test_disable_pipeline(self):
        """Test disable a pipeline with NotFound error"""
        self.napp.pipeline_controller.update_status.side_effect = NotFound
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}/disable"
        response = api.post(url)
        assert response.status_code == 404
