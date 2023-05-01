"""Test the Main class"""
from unittest.mock import MagicMock, patch

from kytos.lib.helpers import (get_controller_mock, get_kytos_event_mock,
                               get_test_client)
from pydantic import BaseModel, ValidationError
from werkzeug.exceptions import NotFound

from napps.kytos.of_multi_table.main import Main


class TestMain():
    """Test the Main class"""

    API_URL = "http://localhost:8181/api/kytos/of_multi_table"

    def setup_method(self):
        """Execute steps before each test"""
        Main.get_pipeline_controller = MagicMock()
        self.pipeline = {
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
        self.napp = Main(get_controller_mock())

    def test_add_pipeline(self):
        """Test adding a pipeline"""
        self.napp.pipeline_controller.insert_pipeline.return_value = "mock_id"
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v1/pipeline"
        response = api.post(url, json=self.pipeline)
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

    def test_enable_pipeline_error(self):
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

    def test_disable_pipeline_error(self):
        """Test disable a pipeline with NotFound error"""
        self.napp.pipeline_controller.update_status.side_effect = NotFound
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.API_URL}/v1/pipeline/{pipeline_id}/disable"
        response = api.post(url)
        assert response.status_code == 404

    def test_get_enabled_table(self):
        """Test get a enabled table"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipelines": [self.pipeline]}
        pipeline = self.napp.get_enabled_table()
        assert pipeline == self.pipeline

        controller.get_pipelines.return_value = {"pipelines": []}
        pipeline = self.napp.get_enabled_table()
        assert pipeline is None

    @patch("napps.kytos.of_multi_table.main.Main.get_enabled_napps")
    @patch("napps.kytos.of_multi_table.main.Main.start_enabling_pipeline")
    def test_load_enable_table(self, *args):
        """Test load an enabled table"""
        (mock_start_enabling_pipeline, mock_get_enabled_napps) = args
        # self.napp.required_napps = set()
        mock_get_enabled_napps.return_value = {"coloring", "of_lldp"}
        self.napp.load_enable_table(self.pipeline)
        assert self.napp.required_napps == {"of_lldp"}
        assert mock_start_enabling_pipeline.call_count == 1

        self.napp.load_enable_table({})
        assert mock_start_enabling_pipeline.call_count == 1

    def test_get_enabled_napps(self):
        """Test get enabled napps from controller"""
        self.napp.controller.napps = {
            ('kytos', 'of_lldp'): "mock",
            ('kytos', 'mef_eline'): "mock",
        }
        self.napp.subscribed_napps = {"coloring", "of_lldp", "mef_eline"}
        napps = self.napp.get_enabled_napps()
        assert napps == {'of_lldp', 'mef_eline'}

    @patch("napps.kytos.of_multi_table.main.Main.emit_event")
    def test_start_enabling_pipeline(self, mock_emit_event):
        """Test beginning of enabling a pipeline"""
        self.napp.start_enabling_pipeline(self.pipeline)
        args = mock_emit_event.call_args[0]
        assert mock_emit_event.call_count == 1
        assert args[0] == "enable_table"
        assert args[1] == {"of_lldp": {'base': 0}}

    @patch("napps.kytos.of_multi_table.main.Main.get_flows_to_be_installed")
    def test_handle_enable_table(self, mock_get_flows_to_be_installed):
        """Test handle enable_table event received"""
        self.napp.required_napps = {'of_lldp', 'mef_eline'}
        event = get_kytos_event_mock("kytos/of_lldp.enable_table", {})
        self.napp.handle_enable_table(event)
        assert mock_get_flows_to_be_installed.call_count == 0

        event = get_kytos_event_mock("kytos/mef_eline.enable_table", {})
        self.napp.handle_enable_table(event)
        assert mock_get_flows_to_be_installed.call_count == 1
