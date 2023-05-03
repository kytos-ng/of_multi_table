"""Test the Main class"""
from unittest.mock import MagicMock

from pydantic import BaseModel, ValidationError
from kytos.lib.helpers import get_controller_mock, get_test_client
from napps.kytos.of_multi_table.main import Main


class TestMain:
    """Test the Main class"""

    def setup_method(self):
        """Execute steps before each test"""
        Main.get_pipeline_controller = MagicMock()
        controller = get_controller_mock()
        self.napp = Main(controller)
        self.api_client = get_test_client(controller, self.napp)
        self.base_endpoint = "kytos/of_multi_table/v1"

    async def test_add_pipeline(self, event_loop):
        """Test adding a pipeline"""
        self.napp.controller.loop = event_loop
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
        url = f"{self.base_endpoint}/pipeline"
        response = await api.post(url, json=payload)
        assert response.status_code == 201

    async def test_add_pipeline_error_empty_json(self, event_loop):
        """Test adding pipeline with an empty JSON"""
        self.napp.controller.loop = event_loop
        payload = {
            "multi_table": [{"table_id": 299}]
        }
        controller = self.napp.pipeline_controller
        controller.insert_pipeline.side_effect = ValidationError('', BaseModel)
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.base_endpoint}/pipeline"
        response = await api.post(url, json=payload)
        assert response.status_code == 400

    async def test_add_pipeline_error_empty_content(self, event_loop):
        """Test adding pipeline with no content"""
        self.napp.controller.loop = event_loop
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.base_endpoint}/pipeline"
        response = await api.post(url)
        assert response.status_code == 400
        assert "required request body" in response.json()["description"]

    async def test_list_pipelines(self):
        """Test list pipelines"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipeline": []}
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.base_endpoint}/pipeline"
        response = await api.get(url)
        assert response.status_code == 200

    async def test_get_pipeline(self):
        """Test get a pipeline"""
        self.napp.pipeline_controller.get_pipeline.return_value = {
            "test": "pipeline"
        }
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}"
        response = await api.get(url)
        assert response.status_code == 200

    async def test_get_pipeline_not_found(self):
        """Test get a pipeline with Not found error"""
        self.napp.pipeline_controller.get_pipeline.return_value = None
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}"
        response = await api.get(url)
        assert response.status_code == 404

    async def test_delete_pipeline(self):
        """Test delete a pipeline"""
        self.napp.pipeline_controller.delete_pipeline.return_value = 1
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}"
        response = await api.delete(url)
        assert response.status_code == 200

    async def test_delete_pipeline_not_found(self):
        """Test delete a pipeline with NotFound error"""
        self.napp.pipeline_controller.delete_pipeline.return_value = 0
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}"
        response = await api.delete(url)
        assert response.status_code == 404

    async def test_enable_pipeline(self):
        """Test enable a pipeline"""
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/enable"
        response = await api.post(url)
        assert response.status_code == 200

    async def test_enable_pipeline_not_found(self):
        """Test enable a pipeline not found"""
        self.napp.pipeline_controller.update_status.return_value = {}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/enable"
        response = await api.post(url)
        assert response.status_code == 404

    async def test_disable_pipeline(self):
        """Test disable a pipeline"""
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/disable"
        response = await api.post(url)
        assert response.status_code == 200

    async def test_disable_pipeline_not_found(self):
        """Test disable a pipeline not found"""
        self.napp.pipeline_controller.update_status.return_value = {}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/disable"
        response = await api.post(url)
        assert response.status_code == 404
