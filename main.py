"""Main module of kytos/of_multi_table Kytos Network Application.

This NApp implements Oplenflow multi tables
"""
# pylint: disable=unused-argument, too-many-arguments, too-many-public-methods
# pylint: disable=attribute-defined-outside-init
import pathlib
from threading import Lock
from typing import Dict

import requests
from pydantic import ValidationError

from kytos.core import KytosNApp, log, rest
from kytos.core.events import KytosEvent
from kytos.core.helpers import listen_to, load_spec, validate_openapi
from kytos.core.rest_api import (HTTPException, JSONResponse, Request,
                                 get_json_or_400)

from .controllers import PipelineController
from .settings import (BASIC_PIPELINE, COOKIE_PREFIX, FLOW_MANAGER_URL,
                       SUBSCRIBED_NAPPS)


class Main(KytosNApp):
    """Main class of kytos/of_multi_table NApp.

    This class is the entry point for this NApp.
    """

    spec = load_spec(pathlib.Path(__file__).parent / "openapi.yml")

    def setup(self):
        """Replace the '__init__' method for the KytosNApp subclass.

        The setup method is automatically called by the controller when your
        application is loaded.

        So, if you have any setup routine, insert it here.
        """
        self.basic_pipeline = BASIC_PIPELINE
        self.subscribed_napps = SUBSCRIBED_NAPPS
        self.pipeline_controller = self.get_pipeline_controller()
        self._pipeline_lock = Lock()
        self.required_napps = set()
        self.load_enable_table(self.get_enabled_table())

    def execute(self):
        """Execute once when the napp is running."""

    def get_enabled_table(self):
        """Get the only enabled table, if exists"""
        pipelines = self.pipeline_controller.get_pipelines("enabling")
        if pipelines["pipelines"]:
            return pipelines["pipelines"][0]
        pipelines = self.pipeline_controller.get_pipelines("enabled")
        if pipelines["pipelines"]:
            return pipelines["pipelines"][0]
        return self.basic_pipeline

    def load_enable_table(self, pipeline: dict):
        """If a pipeline was received, set 'self' variables"""
        if not (pipeline.get('status') in {'enabled', 'enabling'}):
            return

        found_napps = set()
        content = self.build_content(pipeline)
        enable_napps = self.get_enabled_napps()
        # Find NApps in the pipeline to notify them
        for napp in content:
            if napp in enable_napps:
                found_napps.add(napp)
        self.required_napps = found_napps
        self.start_enabling_pipeline(content)

    def get_enabled_napps(self):
        """Get the NApps that are enabled and subscribed"""
        enable_napps = set()
        for key in self.controller.napps:
            # Keys look like this: ('kytos', 'of_lldp')
            if key[1] in self.subscribed_napps:
                enable_napps.add(key[1])
        return enable_napps

    def start_enabling_pipeline(self, content: dict):
        """Method to start the process to enable table
        First, send event notifying NApps about their
        new table set up.
        """
        name = "enable_table"
        self.emit_event(name, content)

    def build_content(self, pipeline: dict):
        """Build content to be sent through an event"""
        content = {}
        with self._pipeline_lock:
            for table in pipeline["multi_table"]:
                table_id = table["table_id"]
                for napp in table["napps_table_groups"]:
                    if napp not in content:
                        content[napp] = {}
                    for flow_type in table["napps_table_groups"][napp]:
                        content[napp][flow_type] = table_id
        return content

    def emit_event(self, name: str, content: dict = None):
        """Send event"""
        context = "kytos/of_multi_table"
        event_name = f"{context}.{name}"
        event = KytosEvent(name=event_name, content=content)
        self.controller.buffers.app.put(event)

    @listen_to("kytos/(mef_eline|coloring|of_lldp).enable_table")
    def on_enable_table(self, event):
        """Listen for NApps responses"""
        self.handle_enable_table(event)

    def handle_enable_table(self, event):
        """Handle NApps responses from enable_table
        Second, wait for all the napps to respond"""
        napp = event.name.split('/')[1].split('.')[0]
        # Check against the last current table
        self.required_napps.remove(napp)
        if self.required_napps:
            # There are more required napps, 'waiting' responses
            return
        self.get_flows_to_be_installed()

    def get_flows_to_be_installed(self):
        """Get flows from flow manager so this NApp can modify them
        Third, install the flows with different table_id"""
        pipeline = self.get_enabled_table()
        if pipeline.get("status") == "enabled":
            # Pipeline enabling has finnished already
            return
        # Keys necessary to delete a flow, 'cookie_mask' is added later
        keys = {'idle_timeout', 'hard_timeout', 'cookie', 'priority',
                'match', 'actions'}
        command = "v2/stored_flows?state=installed"
        response = requests.get(f"{FLOW_MANAGER_URL}/{command}")

        if response.status_code // 100 != 2:
            log.error(f"Could not get the flows from flow_mager. Status "
                      f"code {response.status_code}.")
            # Problem here: pipeline stays as 'enabling', error needs
            # to be handled. Events have been sent and NApps are probably
            # working in a different pipeline setup
            return
        if pipeline.get("status") is None:
            # Changing to default pipeline. Miss flow entries are not needed
            self.delete_miss_flows()
        flows_by_swich = response.json()
        set_up = self.build_content(pipeline)

        for switch in flows_by_swich:
            delete_flows = {"flows": []}
            install_flows = {"flows": []}
            for flow in flows_by_swich[switch]:
                owner = flow["flow"]["owner"]
                if owner not in set_up:
                    continue
                expected_table_id = set_up[owner][flow["flow"]["table_group"]]
                # if table_id needs to change
                if expected_table_id != flow["flow"]["table_id"]:
                    # Get key-value from flow to be sent to flow_manager
                    delete = {key: flow["flow"].get(key) for key in keys}
                    delete["cookie_mask"] = flow["flow"]["cookie"]
                    delete_flows["flows"].append(delete.copy())

                    # Change table_id before being added
                    flow["flow"].update({"table_id": expected_table_id})
                    install_flows["flows"].append(flow["flow"].copy())

            if delete_flows["flows"]:
                self.send_flows(delete_flows, switch, "delete")
            if install_flows["flows"]:
                self.send_flows(install_flows, switch, "add")
            self.install_miss_flows(pipeline, switch)
        if pipeline.get('id'):
            self.pipeline_controller.update_status(pipeline["id"], "enabled")

    def install_miss_flows(self, pipeline: dict, switch: str):
        """Install miss flow entry to a switch"""
        install_flows = {"flows": []}
        cookie = self.get_cookie(switch)
        for table in pipeline["multi_table"][:-1]:
            instruction = [{"instruction_type": "goto_table",
                            "table_id": table['table_id'] + 1}]
            flow = {
                'priority': table.get('priority', 0),
                'cookie': cookie,
                'instructions': table.get('instructions', instruction),
                'owner': 'of_multi_table',
                'table_group': 'base',
                'table_id': table['table_id'],
            }
            if table.get('match'):
                flow['match'] = table.get('match')
            install_flows["flows"].append(flow)

        if install_flows["flows"]:
            self.send_flows(install_flows, switch, "add")

    def delete_miss_flows(self):
        """Delete miss flows, aka. of_multi_table flows.
        This method is called when returning to default pipeline."""
        flows = {
          "flows": [
            {
              "cookie": 12465963768561532928,
              "cookie_mask": 18374686479671623680
            }
          ]
        }
        self.send_flows(flows, '', 'delete')

    def send_flows(self, flows: Dict[str, list], switch: str, action: str):
        """Send flows to flow manager to be added or deleted"""
        url = f"{FLOW_MANAGER_URL}/v2/flows/{switch}"
        if action == 'delete':
            response = requests.delete(url, json=flows)
        elif action == 'add':
            response = requests.post(url, json=flows)
        if response.status_code // 100 != 2:
            log.error(f'Flow manager returned an error trying to {action}: '
                      f'{flows}. Status code {response.status_code}'
                      f'on switch {switch}')

    @staticmethod
    def get_pipeline_controller():
        """Get PipelineController"""
        return PipelineController()

    @rest("/v1/pipeline", methods=["POST"])
    @validate_openapi(spec)
    def add_pipeline(self, request: Request) -> JSONResponse:
        """Add pipeline"""
        data = get_json_or_400(request, self.controller.loop)
        log.debug(f"add_pipeline /v1/pipeline content: {data}")
        try:
            _id = self.pipeline_controller.insert_pipeline(data)
        except ValidationError as err:
            msg = self.error_msg(err.errors())
            log.debug(f"add_pipeline result {msg} 400")
            raise HTTPException(400, detail=msg) from err
        msg = {"id": _id}
        log.debug(f"add_pipeline result {msg} 201")
        return JSONResponse({"id": _id}, status_code=201)

    @rest("/v1/pipeline", methods=["GET"])
    def list_pipelines(self, request: Request) -> JSONResponse:
        """List pipelines"""
        log.debug("list_pipelines /v1/pipeline")
        status = request.query_params.get("status", None)
        pipelines = self.pipeline_controller.get_pipelines(status)
        return JSONResponse(pipelines)

    @rest("/v1/pipeline/{pipeline_id}", methods=["GET"])
    def get_pipeline(self, request: Request) -> JSONResponse:
        """Get pipeline by pipeline_id"""
        pipeline_id = request.path_params["pipeline_id"]
        log.debug(f"get_pipeline /v1/pipeline/{pipeline_id}")
        pipeline = self.pipeline_controller.get_pipeline(pipeline_id)
        if not pipeline:
            msg = f"pipeline_id {pipeline_id} not found"
            log.debug(f"get_pipeline result {msg} 404")
            raise HTTPException(404, detail=msg)
        return JSONResponse(pipeline)

    @rest("/v1/pipeline/{pipeline_id}", methods=["DELETE"])
    def delete_pipeline(self, request: Request) -> JSONResponse:
        """Delete pipeline by pipeline_id"""
        pipeline_id = request.path_params["pipeline_id"]
        log.debug(f"delete_pipeline /v1/pipeline/{pipeline_id}")
        result = self.pipeline_controller.delete_pipeline(pipeline_id)
        if result == 0:
            msg = f"pipeline_id {pipeline_id} not found"
            log.debug(f"delete_pipeline result {msg} 404")
            raise HTTPException(404, detail=msg)
        msg = f"Pipeline {pipeline_id} deleted successfully"
        log.debug(f"delete_pipeline result {msg} 200")
        return JSONResponse(msg)

    @rest("/v1/pipeline/{pipeline_id}/enable", methods=["POST"])
    def enable_pipeline(self, request: Request) -> JSONResponse:
        """Enable pipeline"""
        pipeline_id = request.path_params["pipeline_id"]
        log.debug(f"enable_pipeline /v1/pipeline/{pipeline_id}/enable")
        pipeline = self.pipeline_controller.update_status(pipeline_id,
                                                          "enabling")
        if not pipeline:
            msg = f"Pipeline {pipeline_id} not found"
            log.debug(f"enable_pipeline result {msg} 404")
            raise HTTPException(404, detail=msg)
        if pipeline.get("error") == "Conflict":
            msg = "There is another pipeline enabling already"
            log.debug(f"enable_pipeline result {msg} 409")
            raise HTTPException(409, detail=msg)
        self.load_enable_table(pipeline)
        msg = f"Pipeline {pipeline_id} enabling"
        log.debug(f"enable_pipeline result {msg} 200")
        return JSONResponse(msg)

    @rest("/v1/pipeline/{pipeline_id}/disable", methods=["POST"])
    def disable_pipeline(self, request: Request) -> JSONResponse:
        """Disable pipeline"""
        pipeline_id = request.path_params["pipeline_id"]
        log.debug(f"disable_pipeline /v1/pipeline/{pipeline_id}/disable")
        pipeline = self.pipeline_controller.update_status(pipeline_id,
                                                          "disabled")
        if not pipeline:
            msg = f"Pipeline {pipeline_id} not found"
            log.debug(f"disable_pipeline result {msg} 404")
            raise HTTPException(404, detail=msg)
        msg = f"Pipeline {pipeline_id} disabled"
        self.enable_basic_pipeline()
        log.debug(f"disable_pipeline result {msg} 200")
        return JSONResponse(msg)

    def enable_basic_pipeline(self):
        """Return to basic pipeline
        After disabling a pipeline"""
        content = {
            'of_lldp': {'base': 0},
            'coloring': {'base': 0},
            'mef_eline': {'epl': 0, 'evpl': 0},
        }
        enabled_napps = self.get_enabled_napps()
        self.required_napps = enabled_napps.intersection(self.subscribed_napps)
        self.emit_event('enable_table', content=content)

    @listen_to("kytos/flow_manager.flow.added")
    def on_flow_mod_added(self, event):
        """Looking for recently added flows"""
        self.handle_flow_mod_added(event)

    def handle_flow_mod_added(self, event):
        """Handle recently added flows"""

    @listen_to("kytos/of_core.handshake.completed")
    def on_handshake_completed(self, event):
        """Listen to new switches added"""
        self.handle_handshake_completed(event)

    def handle_handshake_completed(self, event):
        """Handle new added switches"""
        switch_id = event.content['switch'].dpid
        pipeline = self.get_enabled_table()
        if pipeline.get('status') is not None:
            self.install_miss_flows(pipeline, switch_id)

    @listen_to("kytos/flow_manager.flow.error")
    def on_flow_mod_error(self, event):
        """Handle flow mod errors"""
        self.handle_flow_mod_error(event)

    def handle_flow_mod_error(self, event):
        """Handle flow mod errors"""

    @staticmethod
    def get_cookie(switch_dpid):
        """Return the cookie integer given a dpid."""
        dpid = int(switch_dpid.replace(":", ""), 16)
        return (0x000FFFFFFFFFFFFF & dpid) | (COOKIE_PREFIX << 56)

    @staticmethod
    def error_msg(error_list: list) -> str:
        """Return a more request friendly error message from ValidationError"""
        msg = ""
        for err in error_list:
            for value in err['loc']:
                msg += str(value) + ", "
            msg = msg[:-2]
            msg += ": " + err["msg"] + "; "
        return msg[:-2]

    def shutdown(self):
        """Run when your NApp is unloaded.

        If you have some cleanup procedure, insert it here.
        """
