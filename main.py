"""Main module of kytos/of_multi_table Kytos Network Application.

This NApp implements Oplenflow multi tables
"""
# pylint: disable=unused-argument, too-many-arguments, too-many-public-methods
# pylint: disable=attribute-defined-outside-init
import pathlib
from threading import Lock

from flask import jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest, NotFound

from kytos.core import KytosNApp, log, rest
from kytos.core.events import KytosEvent
from kytos.core.helpers import listen_to, load_spec, validate_openapi

from .controllers import PipelineController
from .settings import SUBSCRIBED_NAPPS


class Main(KytosNApp):
    """Main class of kytos/of_multi_table NApp.

    This class is the entry point for this NApp.
    """

    spec = load_spec(pathlib.Path(__file__).parent / "openapi.yml")

    def setup(self):
        """
        The setup method is automatically called by the controller when the
        application is loaded.
        """
        self.subscribed_napps = SUBSCRIBED_NAPPS
        self.pipeline_controller = self.get_pipeline_controller()
        self._pipeline_lock = Lock()
        self.required_napps = set()
        self.load_enable_table(self.get_enabled_table())

    def execute(self):
        """Execute once when the napp is running."""

    def get_enabled_table(self):
        """Get the only enabled table, if exists"""
        pipelines = self.pipeline_controller.get_pipelines("enabled")
        try:
            return pipelines["pipelines"][0]
        except IndexError:
            return None

    def load_enable_table(self, pipeline: dict):
        """If a pipeline was received, set 'self' variables"""
        if not pipeline:
            # There is not pipeline with {"status": "enabled"}
            return

        found_napps = set()
        enable_napps = self.get_enabled_napps()
        # Find NApps in the pipeline to notify them
        for table in pipeline["multi_table"]:
            for napp in table["napps_table_groups"]:
                if napp in enable_napps:
                    found_napps.add(napp)
        self.required_napps = found_napps
        self.start_enabling_pipeline(pipeline)

    def get_enabled_napps(self):
        """Get the NApps that are enabled and subscribed"""
        enable_napps = set()
        for key in self.controller.napps:
            # Keys look like this: ('kytos', 'of_lldp')
            if key[1] in self.subscribed_napps:
                enable_napps.add(key[1])
        return enable_napps

    def start_enabling_pipeline(self, pipeline: dict):
        """Method to start the process to enable table
        First, build content to be sent through an event
        notifying NApps about their new table set up.
        """
        content = {}
        with self._pipeline_lock:
            for table in pipeline["multi_table"]:
                table_id = table["table_id"]
                for napp in table["napps_table_groups"]:
                    content[napp] = {}
                    for flow_type in table["napps_table_groups"][napp]:
                        content[napp][flow_type] = table_id
        name = "enable_table"
        self.emit_event(name, content)

    @staticmethod
    def get_pipeline_controller():
        """Get PipelineController"""
        return PipelineController()

    @rest("/v1/pipeline", methods=["POST"])
    @validate_openapi(spec)
    def add_pipeline(self, data):
        """Add pipeline"""
        log.debug(f"add_pipeline /v1/pipeline content: {data}")
        try:
            _id = self.pipeline_controller.insert_pipeline(data)
        except ValidationError as err:
            msg = self.error_msg(err.errors())
            log.debug(f"add_pipeline result {msg} 400")
            raise BadRequest(msg) from err
        msg = {"id": _id}
        log.debug(f"add_pipeline result {msg} 201")
        return jsonify({"id": _id}), 201

    @rest("/v1/pipeline", methods=["GET"])
    def list_pipelines(self):
        """List pipelines"""
        log.debug("list_pipelines /v1/pipeline")
        args = request.args.to_dict()
        status = args.get("status", None)
        pipelines = self.pipeline_controller.get_pipelines(status)
        return jsonify(pipelines), 200

    @rest("/v1/pipeline/<pipeline_id>", methods=["GET"])
    def get_pipeline(self, pipeline_id):
        """Get pipeline by pipeline_id"""
        log.debug(f"get_pipeline /v1/pipeline/{pipeline_id}")
        pipeline = self.pipeline_controller.get_pipeline(pipeline_id)
        if not pipeline:
            msg = f"pipeline_id {pipeline_id} not found"
            log.debug(f"get_pipeline result {msg} 404")
            raise NotFound(msg)
        return jsonify(pipeline), 200

    @rest("/v1/pipeline/<pipeline_id>", methods=["DELETE"])
    def delete_pipeline(self, pipeline_id):
        """Delete pipeline by pipeline_id"""
        log.debug(f"delete_pipeline /v1/pipeline/{pipeline_id}")
        result = self.pipeline_controller.delete_pipeline(pipeline_id)
        if result == 0:
            msg = f"pipeline_id {pipeline_id} not found"
            log.debug(f"delete_pipeline result {msg} 404")
            raise NotFound(msg)
        msg = f"Pipeline {pipeline_id} deleted successfully"
        log.debug(f"delete_pipeline result {msg} 201")
        return jsonify(msg), 200

    @rest("/v1/pipeline/<pipeline_id>/enable", methods=["POST"])
    def enable_pipeline(self, pipeline_id):
        """Enable pipeline"""
        log.debug(f"enable_pipeline /v1/pipeline/{pipeline_id}/enable")
        try:
            pipeline = self.pipeline_controller.update_status(pipeline_id,
                                                              "enabled")
        except NotFound as err:
            msg = f"Pipeline {pipeline_id} not found"
            log.debug(f"enable_pipeline result {msg} 404")
            raise err
        self.load_enable_table(pipeline)
        msg = f"Pipeline {pipeline_id} enabled"
        log.debug(f"enable_pipeline result {msg} 201")
        return jsonify(msg), 200

    def emit_event(self, name, content=None):
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
        """Handle NApps responses from enable_table"""
        napp = event.name.split('/')[1].split('.')[0]
        # Check against the last current table
        self.required_napps.remove(napp)
        if self.required_napps:
            # There are more required napps, 'waiting' responses
            return
        self.get_flows_to_be_installed()

    @rest("/v1/pipeline/<pipeline_id>/disable", methods=["POST"])
    def disable_pipeline(self, pipeline_id):
        """Disable pipeline"""
        log.debug(f"disable_pipeline /v1/pipeline/{pipeline_id}/disable")
        try:
            self.pipeline_controller.update_status(pipeline_id, "disabled")
        except NotFound as err:
            msg = f"Pipeline {pipeline_id} not found"
            log.debug(f"disable_pipeline result {msg} 404")
            raise err
        msg = f"Pipeline {pipeline_id} disabled"
        log.debug(f"disable_pipeline result {msg} 201")
        return jsonify(msg), 200

    def get_flows_to_be_installed(self):
        """Get flows from flow manager so this NApp can modify them"""
        # ---------------------\
        # \|/ To be continued | >
        # ---------------------/

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

    @listen_to("kytos/flow_manager.flow.error")
    def on_flow_mod_error(self, event):
        """Handle flow mod errors"""
        self.handle_flow_mod_error(event)

    def handle_flow_mod_error(self, event):
        """Handle flow mod errors"""

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
