"""Test the Main class"""

import asyncio
from unittest.mock import call, MagicMock, patch

from napps.kytos.of_multi_table.main import Main
from pydantic import ValidationError

from kytos.lib.helpers import get_controller_mock, get_test_client

from kytos.core.events import KytosEvent


class TestMain:
    """Test the Main class"""

    def setup_method(self):
        """Execute steps before each test"""
        Main.get_pipeline_controller = MagicMock()
        controller = get_controller_mock()
        self.napp = Main(controller)
        self.napp.controller.switches = {"00:00:00:00:00:00:00:01"}
        self.base_endpoint = "kytos/of_multi_table/v1"

    def test_default_pipeline(self) -> None:
        """Test default pipeline value.

        This is to ensure that if settings.DEFAULT_PIPELINE changes
        then it needs to be updated accordingly.
        """
        assert self.napp.default_pipeline == {
            "multi_table": [
                {
                    "table_id": 0,
                    "napps_table_groups": {
                        "coloring": ["base"],
                        "of_lldp": ["base"],
                        "mef_eline": ["evpl", "epl"],
                    },
                },
                {
                    "table_id": 2,
                    "napps_table_groups": {
                        "telemetry_int": ["evpl"],
                    },
                },
                {
                    "table_id": 3,
                    "napps_table_groups": {
                        "telemetry_int": ["epl"],
                    },
                },
            ]
        }

    async def test_get_enabled_table(self):
        """Test get the enabled table"""
        controller = self.napp.pipeline_controller
        controller.get_active_pipeline.return_value = {"status": "enabling"}
        assert self.napp.get_enabled_table() == {"status": "enabling"}
        controller.get_active_pipeline.return_value = {"status": "disabling"}
        assert self.napp.get_enabled_table() == self.napp.default_pipeline
        controller.get_active_pipeline.return_value = {}
        assert self.napp.get_enabled_table() == self.napp.default_pipeline

    @patch("napps.kytos.of_multi_table.main.Main.start_enabling_pipeline")
    @patch("napps.kytos.of_multi_table.main.Main.get_enabled_napps")
    @patch("napps.kytos.of_multi_table.main.Main.build_content")
    async def test_load_pipeline(self, *args):
        """Test load an enabled table"""
        (mock_content, mock_napps, mock_enabling) = args
        content = {
            "of_lldp": {"base": 0},
            "coloring": {"base": 0},
            "mef_eline": {"epl": 0, "evpl": 0},
        }
        mock_content.return_value = content
        mock_napps.return_value = {"of_lldp"}
        self.napp.load_pipeline(self.napp.default_pipeline, 1)

        assert mock_content.call_count == 1
        assert mock_napps.call_count == 1
        assert self.napp.required_napps == {"of_lldp"}
        assert mock_enabling.call_count == 1
        assert mock_enabling.call_args[0][0] == content
        assert mock_enabling.call_args[0][1] == 1
        assert self.napp.controller.buffers.app.put.call_count == 1

    async def test_get_enabled_napps(self):
        """Test get the current enabled napps"""
        self.napp.subscribed_napps = {"mef_eline", "of_lldp"}
        self.napp.controller.napps = {("kytos", "mef_eline")}
        assert self.napp.get_enabled_napps() == {"mef_eline"}

    async def test_start_enabling_pipeline(self):
        """Test start enabling pipeline"""
        self.napp.emit_event = MagicMock()
        content = {"of_lldp": {"base": 0}}
        self.napp.start_enabling_pipeline(content)
        args = self.napp.emit_event.call_args[0]
        assert args[0] == "enable_table"
        assert args[1] == content

    async def test_build_content(self):
        """Test build the content of enable_table event"""
        pipeline = {
            "multi_table": [
                {"table_id": 0, "napps_table_groups": {"coloring": ["base"]}},
                {"table_id": 1, "napps_table_groups": {"of_lldp": ["base"]}},
                {"table_id": 2, "napps_table_groups": {"mef_eline": ["epl"]}},
                {"table_id": 3, "napps_table_groups": {"mef_eline": ["evpl"]}},
            ]
        }
        expected_content = {
            "coloring": {"base": 0},
            "of_lldp": {"base": 1},
            "mef_eline": {"epl": 2, "evpl": 3},
        }
        assert self.napp.build_content(pipeline) == expected_content

    async def test_emit_event(self):
        """Test emit event"""
        self.napp.controller = MagicMock()
        controller = self.napp.controller
        name = "enable_table"
        self.napp.emit_event(name, event_timeout=2)
        assert controller.buffers.app.put.call_count == 1
        assert controller.buffers.app.put.call_args[1] == {"timeout": 2}

    @patch("napps.kytos.of_multi_table.main.Main.get_flows_to_be_installed")
    async def test_handle_enable_table(self, mock_flows_to_be_installed):
        """Test handle content of enable_table event"""
        self.napp.required_napps = {"mef_eline", "of_lldp"}
        event = MagicMock()
        event.name = "kytos/mef_eline.enable_table"
        self.napp.handle_enable_table(event)
        assert mock_flows_to_be_installed.call_count == 0
        event.name = "kytos/of_lldp.enable_table"
        self.napp.handle_enable_table(event)
        assert mock_flows_to_be_installed.call_count == 1

    @patch("napps.kytos.of_multi_table.main.Main.send_flows")
    @patch("napps.kytos.of_multi_table.main.Main.manage_miss_flows")
    @patch("napps.kytos.of_multi_table.main.Main.get_installed_flows")
    async def test_get_flows_to_be_installed(self, *args):
        """Test get flows from flow manager to be installed"""
        (mock_flows, mock_manage_miss, mock_send) = args
        controller = self.napp.pipeline_controller

        # Disabling pipeline
        controller.get_active_pipeline.return_value = {
            "id": "mock_pipeline",
            "status": "disabling",
        }
        flow_of_lldp = {
            "flow": {
                "owner": "of_lldp",
                "table_id": 2,
                "table_group": "base",
                "cookie": 123,
                "match": {"dl_src": "ee:ee:ee:ee:ee:01"},
            }
        }
        flow_unknown = {"flow": {"owner": "of_core"}}
        flow_of_multi_table = {
            "flow": {
                "owner": "of_multi_table",
                "table_id": 1,
            }
        }
        mock_flows.return_value = {
            "00:00:00:00:00:00:00:01": [flow_of_lldp, flow_unknown, flow_of_multi_table]
        }

        self.napp.get_flows_to_be_installed()
        assert mock_manage_miss.call_count == 1
        assert controller.enabled_pipeline.call_count == 0

        args = mock_send.call_args[0]
        flow_of_lldp["flow"]["table_id"] = 0
        assert mock_send.call_count == 2
        assert args[0]["00:00:00:00:00:00:00:01"][0] == flow_of_lldp["flow"]
        assert args[1] == "install"
        assert controller.disabled_pipeline.call_args[0][0] == "mock_pipeline"

        # Enabling pipeline
        controller.get_active_pipeline.return_value = {
            "multi_table": [
                {"table_id": 2, "napps_table_groups": {"of_lldp": ["base"]}}
            ],
            "id": "mocked_pipeline",
            "status": "enabling",
        }
        mock_flows.return_value = {"00:00:00:00:00:00:00:01": [flow_of_lldp]}
        self.napp.get_flows_to_be_installed()
        assert mock_manage_miss.call_count == 2
        assert controller.enabled_pipeline.call_count == 1

        args = mock_send.call_args[0]
        flow_of_lldp["flow"]["table_id"] = 2
        assert mock_send.call_count == 4
        assert args[0]["00:00:00:00:00:00:00:01"][0] == flow_of_lldp["flow"]
        assert args[1] == "install"

        # Enabled pipeline
        controller.get_active_pipeline.return_value = {"status": "enabled"}
        self.napp.get_flows_to_be_installed()
        assert mock_manage_miss.call_count == 2
        assert controller.enabled_pipeline.call_count == 1
        assert mock_send.call_count == 4

    @patch("napps.kytos.of_multi_table.main.Main.delete_miss_flows")
    @patch("napps.kytos.of_multi_table.main.Main.install_miss_flows")
    async def test_manage_miss_flows_no_miss_installed(self, mock_install, mock_delete):
        """Test manage miss flows with no miss flows installed"""
        pipeline = {
            "multi_table": [
                {
                    "table_id": 1,
                    "table_miss_flow": {
                        "priority": 0,
                        "instructions": [
                            {"instruction_type": "goto_table", "table_id": 2}
                        ],
                    },
                }
            ],
        }
        flows_by_switch = {"00:00:00:00:00:00:00:01": [{"flow": {"owner": "of_lldp"}}]}
        self.napp.get_miss_flows_installed = MagicMock()
        self.napp.get_miss_flows_installed.return_value = ({}, set())
        self.napp.manage_miss_flows(pipeline, flows_by_switch)
        expected_arg = {
            1: {
                "priority": 0,
                "instructions": [{"instruction_type": "goto_table", "table_id": 2}],
            }
        }
        assert mock_install.call_count == 1
        args = mock_install.call_args[0]
        assert args[0] == expected_arg
        assert args[1] == expected_arg.keys()
        assert mock_delete.call_count == 0
        assert self.napp.get_miss_flows_installed.call_count == 1

    @patch("napps.kytos.of_multi_table.main.Main.delete_miss_flows")
    @patch("napps.kytos.of_multi_table.main.Main.install_miss_flows")
    async def test_manage_miss_flows_no_miss_pipeline(self, mock_install, mock_delete):
        """Test manage miss flows with no miss flows in pipeline"""
        pipeline = {"multi_table": [{"table_id": 1}]}
        flows_by_switch = {
            "00:00:00:00:00:00:00:01": [{"flow": {"owner": "of_multi_table"}}]
        }

        flows_by_switch = {
            "00:00:00:00:00:00:00:01": [
                {"flow": {"owner": "of_multi_table", "table_id": 0, "priority": 100}}
            ]
        }
        miss_flows = {0: {"priority": 100}}
        self.napp.get_miss_flows_installed = MagicMock()
        self.napp.get_miss_flows_installed.return_value = (miss_flows, {0})
        self.napp.manage_miss_flows(pipeline, flows_by_switch)
        assert mock_install.call_count == 0
        assert mock_delete.call_count == 1
        args = mock_delete.call_args[0]
        assert args[0] == {0}
        assert self.napp.get_miss_flows_installed.call_count == 1

    @patch("napps.kytos.of_multi_table.main.Main.delete_miss_flows")
    @patch("napps.kytos.of_multi_table.main.Main.install_miss_flows")
    async def test_manage_miss_flows(self, mock_install, mock_delete):
        """Test manage miss flows"""
        pipeline = {
            "multi_table": [
                {
                    "table_id": 1,
                    "table_miss_flow": {
                        "priority": 0,
                        "instructions": [
                            {"instruction_type": "goto_table", "table_id": 2}
                        ],
                    },
                },
                {
                    "table_id": 2,
                    "table_miss_flow": {
                        "priority": 0,
                        "instructions": [
                            {"instruction_type": "goto_table", "table_id": 5}
                        ],
                    },
                },
                {
                    "table_id": 5,
                    "table_miss_flow": {"priority": 99, "instructions": [{}]},
                },
            ]
        }
        dpid = "00:00:00:00:00:00:00:01"
        flows_by_switch = {dpid: []}
        for table_id in range(4):
            flow = {
                "flow": {
                    "owner": "of_multi_table",
                    "priority": 0,
                    "instructions": [
                        {"instruction_type": "goto_table", "table_id": table_id + 1}
                    ],
                    "table_id": table_id,
                }
            }
            flows_by_switch[dpid].append(flow)
        self.napp.get_miss_flows_installed = MagicMock()
        miss_flows, stored_tables = Main.get_miss_flows_installed(flows_by_switch)
        self.napp.get_miss_flows_installed.return_value = (miss_flows, stored_tables)
        self.napp.manage_miss_flows(pipeline, flows_by_switch)
        assert mock_install.call_count == 1
        args = mock_install.call_args[0]
        assert args[1] == {2, 5}
        assert mock_delete.call_count == 1
        args = mock_delete.call_args[0]
        assert args[0] == {0, 2, 3}
        assert self.napp.get_miss_flows_installed.call_count == 1

    @patch("napps.kytos.of_multi_table.main.Main.delete_miss_flows")
    @patch("napps.kytos.of_multi_table.main.Main.install_miss_flows")
    async def test_manage_miss_flows_no_changes(self, mock_install, mock_delete):
        """Test manage miss flows where no changes were made"""
        pipeline = {
            "multi_table": [
                {
                    "table_id": 0,
                    "table_miss_flow": {
                        "priority": 200,
                        "instructions": [
                            {"instruction_type": "goto_table", "table_id": 1}
                        ],
                    },
                },
                {
                    "table_id": 1,
                    "table_miss_flow": {
                        "priority": 0,
                        "instructions": [
                            {"instruction_type": "goto_table", "table_id": 2}
                        ],
                        "match": {"in_port": 1, "dl_vlan": 0},
                    },
                },
                {"table_id": 2},
            ]
        }
        flows_by_switch = {
            "00:00:00:00:00:00:00:01": [
                {
                    "flow": {
                        "owner": "of_multi_table",
                        "table_id": 0,
                        "priority": 200,
                        "instructions": [
                            {"instruction_type": "goto_table", "table_id": 1}
                        ],
                    }
                },
                {
                    "flow": {
                        "owner": "of_multi_table",
                        "table_id": 1,
                        "priority": 0,
                        "instructions": [
                            {"instruction_type": "goto_table", "table_id": 2}
                        ],
                        "match": {"in_port": 1, "dl_vlan": 0},
                    }
                },
            ]
        }
        miss_flows, stored_tables = Main.get_miss_flows_installed(flows_by_switch)
        self.napp.get_miss_flows_installed = MagicMock()
        self.napp.get_miss_flows_installed.return_value = (miss_flows, stored_tables)
        self.napp.manage_miss_flows(pipeline, flows_by_switch)
        assert mock_install.call_count == 1
        args = mock_install.call_args[0]
        assert args[1] == set()
        assert mock_delete.call_count == 1
        args = mock_delete.call_args[0]
        assert args[0] == set()
        assert self.napp.get_miss_flows_installed.call_count == 1

    async def test_get_miss_flows_installed(self):
        """Test get miss flows"""
        dpid = "00:00:00:00:00:00:00:01"
        flows_by_switch = {dpid: []}
        expected_flows = {}
        for table_id in range(4):
            flow = {
                "flow": {
                    "owner": "of_multi_table",
                    "priority": 0,
                    "instructions": [
                        {"instruction_type": "goto_table", "table_id": table_id + 1}
                    ],
                    "table_id": table_id,
                    "match": {"in_port": 1, "dl_vlan": 0},
                }
            }
            flows_by_switch[dpid].append(flow)
            expected_flows[table_id] = {
                "priority": 0,
                "instructions": [
                    {"instruction_type": "goto_table", "table_id": table_id + 1}
                ],
                "match": {"in_port": 1, "dl_vlan": 0},
            }
        miss_flows, flow_ids = Main.get_miss_flows_installed(flows_by_switch)
        assert miss_flows == expected_flows
        assert flow_ids == {0, 1, 2, 3}

    @patch("napps.kytos.of_multi_table.main.Main.get_cookie")
    @patch("napps.kytos.of_multi_table.main.Main.send_flows")
    async def test_delete_miss_flows(self, mock_send, mock_cookie):
        """Test delete miss flows"""
        mock_cookie.return_value = 999
        expected_flows = {
            "00:00:00:00:00:00:00:01": [
                {
                    "cookie": 999,
                    "cookie_mask": int(0xFFFFFFFFFFFFFFFF),
                    "table_id": 0,
                    "owner": "of_multi_table",
                },
                {
                    "cookie": 999,
                    "cookie_mask": int(0xFFFFFFFFFFFFFFFF),
                    "table_id": 2,
                    "owner": "of_multi_table",
                },
            ]
        }
        self.napp.delete_miss_flows({0, 2})
        assert mock_send.call_count == 1
        assert mock_send.call_args[0][0] == expected_flows

    @patch("napps.kytos.of_multi_table.main.Main.get_cookie")
    @patch("napps.kytos.of_multi_table.main.Main.send_flows")
    async def test_install_miss_flows(self, mock_send, mock_cookie):
        """Test install miss flows"""
        pipeline = {
            2: {
                "priority": 10,
                "instructions": [{"instruction_type": "goto_table", "table_id": 3}],
                "match": {"in_port": 1},
            }
        }
        mock_cookie.return_value = 999
        self.napp.install_miss_flows(pipeline, {2})
        args = mock_send.call_args[0]
        expected_arg = {
            "00:00:00:00:00:00:00:01": [
                {
                    "priority": 10,
                    "cookie": 999,
                    "owner": "of_multi_table",
                    "table_group": "base",
                    "table_id": 2,
                    "match": {"in_port": 1},
                    "instructions": [{"instruction_type": "goto_table", "table_id": 3}],
                }
            ]
        }
        assert args[0] == expected_arg
        assert args[1] == "install"

    @patch("time.sleep", return_value=None)
    async def test_send_flows(self, _):
        """Test send flows"""
        self.napp.controller.buffers.app.put = MagicMock()
        flows = {"01": ["flow1", "flow2", "flow3"]}
        self.napp.send_flows(flows, "install", True)
        last_call = self.napp.controller.buffers.app.put.call_args
        event = last_call.args[0]

        assert event.name == "kytos.flow_manager.flows.install"
        assert event.content["dpid"] == "01"
        assert event.content["flow_dict"]["flows"] == ["flow1", "flow2", "flow3"]

    async def test_add_pipeline(self):
        """Test adding a pipeline"""
        self.napp.controller.loop = asyncio.get_running_loop()
        payload = {
            "status": "disabled",
            "multi_table": [
                {
                    "table_id": 0,
                    "description": "Table for testing",
                    "table_miss_flow": {
                        "priority": 0,
                        "match": {},
                        "instructions": [
                            {"instruction_type": "goto_table", "table_id": 1}
                        ],
                    },
                    "napps_table_groups": {
                        "of_lldp": ["base"],
                        "mef_eline": ["epl", "evpl"],
                        "coloring": ["base"],
                        "telemetry_int": ["epl", "evpl"],
                    },
                },
            ],
        }
        self.napp.pipeline_controller.insert_pipeline.return_value = "mock_id"
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.base_endpoint}/pipeline"
        response = await api.post(url, json=payload)
        assert response.status_code == 201

    async def test_add_pipeline_error_empty_json(self):
        """Test adding pipeline with an empty JSON"""
        self.napp.controller.loop = asyncio.get_running_loop()
        payload = {"multi_table": [{"table_id": 299}]}
        controller = self.napp.pipeline_controller
        controller.insert_pipeline.side_effect = ValidationError.from_exception_data(
            "", []
        )
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.base_endpoint}/pipeline"
        response = await api.post(url, json=payload)
        assert response.status_code == 400

    async def test_add_pipeline_error_empty_content(self):
        """Test adding pipeline with no content"""
        self.napp.controller.loop = asyncio.get_running_loop()
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
        self.napp.pipeline_controller.get_pipeline.return_value = {"test": "pipeline"}
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
        self.napp.pipeline_controller.get_pipeline.return_value = {"status": "disabled"}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}"
        response = await api.delete(url)
        assert response.status_code == 200

    async def test_delete_pipeline_conflict(self):
        """Test delete a pipeline Conflict"""
        self.napp.pipeline_controller.get_pipeline.return_value = {"status": "enabling"}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}"
        response = await api.delete(url)
        assert response.status_code == 409

    async def test_delete_pipeline_not_found(self):
        """Test delete a pipeline with NotFound error"""
        self.napp.pipeline_controller.get_pipeline.return_value = None
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}"
        response = await api.delete(url)
        assert response.status_code == 404

    @patch("napps.kytos.of_multi_table.main.Main.load_pipeline")
    async def test_enable_pipeline(self, mock_load):
        """Test enable a pipeline"""
        controller = self.napp.pipeline_controller
        # All pipelines are disabled
        controller.enabling_pipeline.return_value = {"id": "pipeline_id"}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "pipeline_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/enable"
        response = await api.post(url)
        assert response.status_code == 200
        assert mock_load.call_count == 1
        assert mock_load.call_args[0][0] == {"id": "pipeline_id"}

    async def test_enable_pipeline_not_found(self):
        """Test enable a pipeline not found"""
        controller = self.napp.pipeline_controller
        controller.get_active_pipeline.return_value = {}
        controller.enabling_pipeline.return_value = {}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/enable"
        response = await api.post(url)
        assert response.status_code == 404

    @patch("napps.kytos.of_multi_table.main.Main.load_pipeline")
    async def test_disable_pipeline(self, mock_load):
        """Test disable a pipeline"""
        controller = self.napp.pipeline_controller
        controller.get_pipeline.return_value = {"id": "mocked_id"}
        # Disable an enabled pipeline
        controller.get_active_pipeline.return_value = {}
        pipeline_id = "mocked_id"
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/disable"
        response = await api.post(url)
        assert response.status_code == 200
        assert mock_load.call_count == 1

        # Retry a disabling pipeline
        controller.get_active_pipeline.return_value = {
            "id": "mocked_id",
            "status": "disabling",
        }
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/disable"
        response = await api.post(url)
        assert response.status_code == 200
        assert mock_load.call_count == 2

    async def test_disable_pipeline_not_found(self):
        """Test disable a pipeline not found"""
        controller = self.napp.pipeline_controller
        controller.get_pipeline.return_value = {}
        api = get_test_client(self.napp.controller, self.napp)
        pipeline_id = "test_id"
        url = f"{self.base_endpoint}/pipeline/{pipeline_id}/disable"
        response = await api.post(url)
        assert response.status_code == 404

    async def test_check_ownership(self):
        """Test check of_multi_table ownership"""
        result = self.napp.check_ownership(int(0xAD00000000000001))
        assert result is True

        result = self.napp.check_ownership(int(0xAC00000000000001))
        assert result is False

    async def test_handle_flow_mod_error(self):
        """Test handle flow_mod error"""
        controller = self.napp.pipeline_controller
        controller.reset_mock()
        flow = MagicMock()
        event = MagicMock()

        # Event with error_exception
        event.content = {"error_exception": "exception_mock"}
        self.napp.handle_flow_mod_error(event)
        assert controller.get_active_pipeline.call_count == 0
        assert controller.error_pipeline.call_count == 0

        # Event with flow from another napp
        flow.cookie = int(0xAC00000000000001)
        event.content = {"flow": flow}
        self.napp.handle_flow_mod_error(event)
        assert controller.get_active_pipeline.call_count == 0
        assert controller.error_pipeline.call_count == 0

        # Event with flow from this napp
        flow.cookie = int(0xAD00000000000001)
        event.content = {"flow": flow}
        self.napp.handle_flow_mod_error(event)
        assert controller.get_active_pipeline.call_count == 1
        assert controller.error_pipeline.call_count == 1

    async def test_get_cookie(self):
        """Test get cookie"""
        switch = "00:00:00:00:00:00:00:01"
        assert self.napp.get_cookie(switch) == 12465963768561532929
