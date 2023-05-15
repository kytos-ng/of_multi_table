"""Test the Main class"""
from unittest.mock import MagicMock, patch, call

from pydantic import BaseModel, ValidationError
from kytos.core.events import KytosEvent
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

    async def test_get_enabled_table(self):
        """Test get the enabled table"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipelines": ["test"]}
        assert self.napp.get_enabled_table() == "test"
        controller.get_pipelines.return_value = {"pipelines": []}
        assert self.napp.get_enabled_table() == self.napp.default_pipeline

    @patch("napps.kytos.of_multi_table.main.Main.start_enabling_pipeline")
    @patch("napps.kytos.of_multi_table.main.Main.get_enabled_napps")
    @patch("napps.kytos.of_multi_table.main.Main.build_content")
    async def test_load_enable_table(self, *args):
        """Test load an enabled table"""
        (mock_content, mock_napps, mock_enabling) = args
        # Default pipeline activation is not from here
        self.napp.load_enable_table({'id': 'mocked_defaul_pipeline'})
        assert mock_enabling.call_count == 0

        content = {
            'of_lldp': {'base': 0},
            'coloring': {'base': 0},
        }
        mock_content.return_value = content
        mock_napps.return_value = {'of_lldp'}
        self.napp.load_enable_table({
            'id': 'mocked_pipeline',
            'status': 'enabling'
        })
        assert self.napp.required_napps == {'of_lldp'}
        assert mock_enabling.call_count == 1
        assert mock_enabling.call_args[0][0] == content

    async def test_get_enabled_napps(self):
        """Test get the current enabled napps"""
        self.napp.subscribed_napps = {"mef_eline", "of_lldp"}
        self.napp.controller.napps = {('kytos', 'mef_eline')}
        assert self.napp.get_enabled_napps() == {'mef_eline'}

    async def test_start_enabling_pipeline(self):
        """Test start enabling pipeline"""
        self.napp.emit_event = MagicMock()
        content = {'of_lldp': {'base': 0}}
        self.napp.start_enabling_pipeline(content)
        args = self.napp.emit_event.call_args[0]
        assert args[0] == "enable_table"
        assert args[1] == content

    async def test_build_content(self):
        """Test build the content of enable_table event"""
        pipeline = {'multi_table': [
            {
                'table_id': 0,
                'napps_table_groups': {'coloring': ['base']}
            },
            {
                'table_id': 1,
                'napps_table_groups': {'of_lldp': ['base']}
            },
            {
                'table_id': 2,
                'napps_table_groups': {'mef_eline': ['epl']}
            },
            {
                'table_id': 3,
                'napps_table_groups': {'mef_eline': ['evpl']}
            }
        ]}
        expected_content = {
            'coloring': {'base': 0},
            'of_lldp': {'base': 1},
            'mef_eline': {'epl': 2, 'evpl': 3},
        }
        assert self.napp.build_content(pipeline) == expected_content

    async def test_emit_event(self):
        """Test emit event"""
        controller = self.napp.controller
        name = "enable_table"
        self.napp.emit_event(name)
        assert controller.buffers.app.put.call_count == 1

    @patch("napps.kytos.of_multi_table.main.Main.get_flows_to_be_installed")
    async def test_handle_enable_table(self, mock_flows_to_be_installed):
        """Test handle content of enable_table event"""
        self.napp.required_napps = {'mef_eline', 'of_lldp'}
        event = MagicMock()
        event.name = "kytos/mef_eline.enable_table"
        self.napp.handle_enable_table(event)
        assert mock_flows_to_be_installed.call_count == 0
        event.name = "kytos/of_lldp.enable_table"
        self.napp.handle_enable_table(event)
        assert mock_flows_to_be_installed.call_count == 1

    @patch("napps.kytos.of_multi_table.main.Main.send_flows")
    @patch("napps.kytos.of_multi_table.main.Main.install_miss_flows")
    @patch("napps.kytos.of_multi_table.main.Main.delete_miss_flows")
    @patch("napps.kytos.of_multi_table.main.Main.get_installed_flows")
    @patch("napps.kytos.of_multi_table.main.Main.get_enabled_table")
    async def test_get_flows_to_be_installed(self, *args):
        """Test get flows from flow manager to be installed"""
        (mock_table, mock_flows, mock_delete, mock_install, mock_send) = args

        # Default pipeline
        mock_table.return_value = self.napp.default_pipeline
        flow_of_lldp = {
            'flow': {
                'owner': 'of_lldp',
                'table_id': 2,
                'table_group': 'base',
                'cookie': 123,
                'match': {'dl_src': 'ee:ee:ee:ee:ee:01'}
            }
        }
        flow_unknown = {'flow': {'owner': 'of_core'}}
        mock_flows.return_value = {'00:00:00:00:00:00:00:01': [
            flow_of_lldp, flow_unknown
        ]}

        self.napp.get_flows_to_be_installed()
        assert mock_delete.call_count == 1
        assert mock_install.call_count == 0
        assert self.napp.pipeline_controller.enabled_pipeline.call_count == 0

        args = mock_send.call_args[0]
        flow_of_lldp["flow"]["table_id"] = 0
        assert mock_send.call_count == 2
        assert args[0]['00:00:00:00:00:00:00:01'][0] == flow_of_lldp['flow']
        assert args[1] == 'install'
        assert args[2] is True

        # Enabling pipeline
        mock_table.return_value = {
            'multi_table': [{
                    'table_id': 2,
                    'napps_table_groups': {'of_lldp': ['base']}
                }],

            'id': 'mocked_pipeline',
            'status': 'enabling'
        }
        mock_flows.return_value = {'00:00:00:00:00:00:00:01': [flow_of_lldp]}
        self.napp.get_flows_to_be_installed()
        assert mock_delete.call_count == 1
        assert mock_install.call_count == 1
        assert self.napp.pipeline_controller.enabled_pipeline.call_count == 1

        args = mock_send.call_args[0]
        flow_of_lldp["flow"]["table_id"] = 2
        assert mock_send.call_count == 4
        assert args[0]['00:00:00:00:00:00:00:01'][0] == flow_of_lldp['flow']
        assert args[1] == 'install'
        assert args[2] is True

        # Enabled pipeline
        mock_table.return_value = {'status': 'enabled'}
        self.napp.get_flows_to_be_installed()
        assert mock_delete.call_count == 1
        assert mock_install.call_count == 1
        assert self.napp.pipeline_controller.enabled_pipeline.call_count == 1
        assert mock_send.call_count == 4

    @patch("napps.kytos.of_multi_table.main.Main.get_cookie")
    @patch("napps.kytos.of_multi_table.main.Main.send_flows")
    async def test_install_miss_flows(self, mock_send, mock_cookie):
        """Test install miss flows"""
        pipeline = {
            'multi_table': [{
                    'table_id': 2,
                    'napps_table_groups': {'of_lldp': ['base']},
                    'table_miss_flow':{
                        'priority': 10,
                        'instructions': [{
                            "instruction_type": "goto_table",
                            "table_id": 3
                        }],
                        'match': {'in_port': 1}
                    }
                }],
            'id': 'mocked_pipeline',
            'status': 'enabling'
        }
        mock_cookie.return_value = 999
        self.napp.controller.switches = {'00:00:00:00:00:00:00:01'}
        self.napp.install_miss_flows(pipeline)
        args = mock_send.call_args[0]
        expected_arg = {
            '00:00:00:00:00:00:00:01': [{
                'priority': 10,
                'cookie': 999,
                'owner': 'of_multi_table',
                'table_group': 'base',
                'table_id': 2,
                'match': {'in_port': 1},
                'instructions': [{
                    "instruction_type": "goto_table",
                    "table_id": 3
                }]
            }]
        }
        assert args[0] == expected_arg
        assert args[1] == 'install'
        assert args[2] is True

    @patch("napps.kytos.of_multi_table.main.Main.send_flows")
    async def test_delete_miss_flows(self, mock_send):
        """Test delete miss flows"""
        self.napp.controller.switches = {'00:00:00:00:00:00:00:01'}
        self.napp.delete_miss_flows()
        expected_arg = {
            '00:00:00:00:00:00:00:01': [{
                "cookie": int(0xad << 56),
                "cookie_mask": int(0xFF00000000000000)
            }]
        }
        assert mock_send.call_count == 1
        args = mock_send.call_args[0]
        assert args[0] == expected_arg

    @patch("time.sleep", return_value=None)
    @patch("napps.kytos.of_multi_table.main.BATCH_SIZE", 2)
    async def test_send_flows(self, _):
        """Test send flows"""
        self.napp.controller.buffers.app.put = MagicMock()
        flows = {'01': ['flow1', 'flow2', 'flow3']}
        self.napp.send_flows(flows, 'install', True)
        assert self.napp.controller.buffers.app.put.call_count == 2

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

    @patch("napps.kytos.of_multi_table.main.Main.load_enable_table")
    async def test_enable_pipeline(self, mock_load):
        """Test enable a pipeline"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipelines": []}
        controller.enabling_pipeline.return_value = {"id": "pipeline_id"}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/enable"
        response = await api.post(url)
        assert response.status_code == 200
        assert mock_load.call_count == 1
        assert mock_load.call_args[0][0] == {"id": "pipeline_id"}

    async def test_enable_pipeline_not_found(self):
        """Test enable a pipeline not found"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipelines": []}
        controller.enabling_pipeline.return_value = {}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/enable"
        response = await api.post(url)
        assert response.status_code == 404

    async def test_enable_pipeline_conflict(self):
        """Test enable a pipeline conflict"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipelines": [{
            "id": "pipeline_enabling"
        }]}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/enable"
        response = await api.post(url)
        assert response.status_code == 409

    @patch("napps.kytos.of_multi_table.main.Main.enable_default_pipeline")
    async def test_disable_pipeline(self, mock_enable_default):
        """Test disable a pipeline"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipelines": []}
        controller.disabled_pipeline.return_value = {"status": "enabled"}
        pipeline_id = "test_id"
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/disable"
        response = await api.post(url)
        assert response.status_code == 200
        assert mock_enable_default.call_count == 1

        # Disable the enabling pipeline
        controller.get_pipelines.return_value = {"pipelines": [{
            "id": "test_id"
        }]}
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/disable"
        response = await api.post(url)
        assert response.status_code == 200
        assert mock_enable_default.call_count == 2

    async def test_disable_pipeline_not_found(self):
        """Test disable a pipeline not found"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipelines": []}
        controller.disabled_pipeline.return_value = {}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/disable"
        response = await api.post(url)
        assert response.status_code == 404

    async def test_disable_pipeline_conflict(self):
        """Test disable a pipeline conflict"""
        controller = self.napp.pipeline_controller
        controller.get_pipelines.return_value = {"pipelines": [{
            "id": "enabling"
        }]}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/disable"
        response = await api.post(url)
        assert response.status_code == 409

    @patch("napps.kytos.of_multi_table.main.Main.get_enabled_napps")
    @patch("napps.kytos.of_multi_table.main.Main.build_content")
    async def test_enable_default_pipeline(self, mock_content, mock_napps):
        """Test test enable default pipeline"""
        content = {
            "mef_eline": {"epl": 0, "evpl": 0},
            "of_lldp": {"base": 0},
            "coloring": {"base": 0}
        }
        mock_content.return_value = content
        mock_napps.return_value = {"mef_eline", "of_lldp", "of_core"}
        self.napp.emit_event = MagicMock()
        self.napp.enable_default_pipeline()
        assert self.napp.required_napps == {"mef_eline", "of_lldp"}
        assert self.napp.emit_event.call_count == 1
        assert self.napp.emit_event.call_args[1] == {"content": content}

    async def test_get_cookie(self):
        """Test get cookie"""
        switch = '00:00:00:00:00:00:00:01'
        assert self.napp.get_cookie(switch) == 12465963768561532929

    async def test_error_msg(self):
        """Test error message"""
        # ValidationErro mocked response
        error_list = [{'loc': ('table_id', ), 'msg': 'mock_msg_1'}]
        actual_msg = self.napp.error_msg(error_list)
        expected_msg = 'table_id: mock_msg_1'
        assert actual_msg == expected_msg
