"""Main module of kytos/of_multi_table Kytos Network Application.

This NApp implements Oplenflow multi tables
"""
# pylint: disable=unused-argument
import pathlib

from flask import jsonify

from kytos.core import KytosNApp, log, rest
from kytos.core.helpers import load_spec, validate_openapi


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
        log.info("Setup from of_multi_table")

    def execute(self):
        """Execute once when the napp is running."""
        log.info("Executing of_multi_table")

    @rest("/v1/pipeline", methods=["POST"])
    @validate_openapi(spec)
    def add_pipeline(self, data):
        """Add pipeline"""
        return jsonify("Operation successful"), 200

    @rest("/v1/pipeline", methods=["GET"])
    def list_pipelines(self):
        """List pipelines"""
        return jsonify("Operation successful"), 200

    @rest("/v1/pipeline/<pipeline_id>", methods=["GET"])
    def get_pipeline(self, pipeline_id):
        """Get pipeline by pipeline_id"""
        return jsonify("Operation successful"), 200

    @rest("/v1/pipeline/<pipeline_id>", methods=["DELETE"])
    def delete_pipeline(self, pipeline_id):
        """Delete pipeline by pipeline_id"""
        return jsonify("Operation successful"), 200

    @rest("/v1/pipeline/<pipeline_id>/enable", methods=["POST"])
    def enable_pipeline(self, pipeline_id):
        """Enable pipeline"""
        return jsonify("Operation successful"), 201

    @rest("/v1/pipeline/<pipeline_id>/disable", methods=["POST"])
    def disable_pipeline(self, pipeline_id):
        """Disable pipeline"""
        return jsonify("Operation successful"), 201

    def shutdown(self):
        """Run when your NApp is unloaded.

        If you have some cleanup procedure, insert it here.
        """
        log.info("Shutting down of_multi_table")
