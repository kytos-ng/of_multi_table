"""Test the Pipeline controllers"""
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from werkzeug.exceptions import NotFound

from controllers import PipelineController


class TestController():
    """Test the controller class"""

    def setup_method(self):
        """Execute steps before each test"""
        self.controller = PipelineController(MagicMock())
        self.pipeline = {
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
                }
            ]
        }

    def test_insert_pipeline(self):
        """Test insert_pipeline"""
        self.controller.insert_pipeline(self.pipeline)
        assert self.controller.db.pipelines.insert_one.call_count == 1

    def test_insert_pipeline_error(self):
        """Test insert_pipeline with ValidationError"""
        with pytest.raises(ValidationError):
            self.controller.insert_pipeline({})

    def test_get_pipelines(self):
        """Test get pipelines"""
        self.controller.get_pipelines()
        args = self.controller.db.pipelines.aggregate.call_args[0][0]
        assert "$project" in args[0]
        assert "status" not in args[1]["$match"]

        self.controller.get_pipelines("enabled")
        args = self.controller.db.pipelines.aggregate.call_args[0][0]
        assert "enabled" in args[1]["$match"]["status"]
        assert self.controller.db.pipelines.aggregate.call_count == 2

    def test_get_pipeline(self):
        """Test get pipeline"""
        self.controller.get_pipeline("pipeline_id")
        assert self.controller.db.pipelines.find_one.call_count == 1

    def test_delete_pipeline(self):
        """Test delete_pipeline"""
        self.controller.delete_pipeline("pipeline_id")
        assert self.controller.db.pipelines.delete_one.call_count == 1

    def test_update_status(self):
        """Test update_status"""
        self.controller.update_status("pipeline_id", "disabled")
        assert self.controller.db.pipelines.find_one_and_update.call_count == 1
        args = self.controller.db.pipelines.find_one_and_update.call_args[0]
        assert args[0] == {"id": "pipeline_id"}
        assert args[1]["$set"]["status"] == "disabled"

        self.controller.update_status("pipeline_id", "enabled")
        assert self.controller.db.pipelines.find_one_and_update.call_count == 2
        args = self.controller.db.pipelines.find_one_and_update.call_args[0]
        assert args[0] == {"id": "pipeline_id"}
        assert args[1]["$set"]["status"] == "enabled"

    def test_update_status_error(self):
        """Test update_status not found"""
        self.controller.db.pipelines.find_one_and_update.return_value = None
        assert not self.controller.update_status("pipeline_id", "disabled")
