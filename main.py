"""Main module of kytos/of_multi_table Kytos Network Application.

This NApp implements Oplenflow multi tables
"""
# pylint: disable=unused-argument
import pathlib

from flask import jsonify, request
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest, NotFound

from kytos.core import KytosNApp, log, rest
from kytos.core.helpers import load_spec, validate_openapi

from .controllers import PipelineController


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
        self.pipeline_controller = self.get_pipeline_controller()

    def execute(self):
        """Execute once when the napp is running."""
        log.info("Executing of_multi_table")

    @staticmethod
    def get_pipeline_controller():
        """Get PipelineController"""
        return PipelineController()

    @rest("/v1/pipeline", methods=["POST"])
    @validate_openapi(spec)
    def add_pipeline(self, data):
        """Add pipeline"""
        log.debug("add_pipeline /v1/pipeline")
        try:
            _id = self.pipeline_controller.insert_pipeline(data)
        except ValidationError as err:
            msg = self.error_msg(err.errors())
            log.debug("add_pipeline result %s %s", msg, 400)
            raise BadRequest(msg) from err
        msg = f"Pipeline {_id} created"
        log.debug("add_pipeline result %s %s", _id, 201)
        return jsonify(msg), 201

    @rest("/v1/pipeline", methods=["GET"])
    def list_pipelines(self):
        """List pipelines"""
        log.debug("list_pipelines /v1/pipeline")
        args = request.args.to_dict()
        status = args.get("status", None)
        pipelines = self.pipeline_controller.get_pipelines(status)
        log.debug("list_pipelines result %s %s", pipelines, 201)
        return jsonify(pipelines), 201

    @rest("/v1/pipeline/<pipeline_id>", methods=["GET"])
    def get_pipeline(self, pipeline_id):
        """Get pipeline by pipeline_id"""
        log.debug("get_pipeline /v1/pipeline/%s", pipeline_id)
        pipeline = self.pipeline_controller.get_pipeline(pipeline_id)
        if not pipeline:
            msg = f"pipeline_id {pipeline_id} not found"
            log.debug("get_pipeline result %s %s", msg, 404)
            raise NotFound(msg)
        log.debug("get_pipeline result %s %s", pipeline, 201)
        return jsonify(pipeline), 201

    @rest("/v1/pipeline/<pipeline_id>", methods=["DELETE"])
    def delete_pipeline(self, pipeline_id):
        """Delete pipeline by pipeline_id"""
        log.debug("delete_pipeline /v1/pipeline/%s", pipeline_id)
        result = self.pipeline_controller.delete_pipeline(pipeline_id)
        if result == 0:
            msg = f"pipeline_id {pipeline_id} not found"
            log.debug("delete_pipeline result %s %s", msg, 404)
            raise NotFound(msg)
        msg = f"Pipeline {pipeline_id} deleted successfully"
        log.debug("delete_pipeline result %s %s", msg, 201)
        return jsonify(msg), 201

    @rest("/v1/pipeline/<pipeline_id>/enable", methods=["POST"])
    def enable_pipeline(self, pipeline_id):
        """Enable pipeline"""
        log.debug("enable_pipeline /v1/pipeline/%s/enable", pipeline_id)
        try:
            self.pipeline_controller.update_status(pipeline_id, "enabled")
        except NotFound as err:
            msg = f"Pipeline {pipeline_id} not found"
            log.debug("enable_pipeline result %s %s", msg, 404)
            raise err
        msg = f"Pipeline {pipeline_id} enabled"
        log.debug("enable_pipeline result %s %s", msg, 201)
        return jsonify(msg), 201

    @rest("/v1/pipeline/<pipeline_id>/disable", methods=["POST"])
    def disable_pipeline(self, pipeline_id):
        """Disable pipeline"""
        log.debug("disable_pipeline /v1/pipeline/%s/disable", pipeline_id)
        try:
            self.pipeline_controller.update_status(pipeline_id, "disabled")
        except NotFound as err:
            msg = f"Pipeline {pipeline_id} not found"
            log.debug("disable_pipeline result %s %s", msg, 404)
            raise err
        msg = f"Pipeline {pipeline_id} disabled"
        log.debug("disable_pipeline result %s %s", msg, 201)
        return jsonify(msg), 201

    @staticmethod
    def error_msg(error_list: list) -> str:
        """Return a more request friendly error message from ValidationError"""
        msg = ""
        for err in error_list:
            for value in err['loc']:
                msg += value + ", "
            msg = msg[:-2]
            msg += ": " + err["msg"] + "; "
        return msg[:-2]

    def shutdown(self):
        """Run when your NApp is unloaded.

        If you have some cleanup procedure, insert it here.
        """
        log.info("Shutting down of_multi_table")
