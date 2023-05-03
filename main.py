"""Main module of kytos/of_multi_table Kytos Network Application.

This NApp implements Oplenflow multi tables
"""
# pylint: disable=unused-argument
import pathlib

from pydantic import ValidationError

from kytos.core import KytosNApp, log, rest
from kytos.core.helpers import load_spec, validate_openapi
from kytos.core.rest_api import (HTTPException, JSONResponse, Request,
                                 get_json_or_400)

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
                                                          "enabled")
        if not pipeline:
            msg = f"Pipeline {pipeline_id} not found"
            log.debug(f"enable_pipeline result {msg} 404")
            raise HTTPException(404, detail=msg)
        msg = f"Pipeline {pipeline_id} enabled"
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
        log.debug(f"disable_pipeline result {msg} 200")
        return JSONResponse(msg)

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
