"""Test the Pipeline controllers"""
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

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

    def test_get_active_pipeline(self):
        """Test get_active_pipeline"""
        self.controller.get_active_pipeline()
        args = self.controller.db.pipelines.find_one.call_args[0]
        assert args[0]['status']['$ne'] == "disabled"

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
        args = self.controller.db.pipelines.delete_one.call_args[0]
        assert args[0] == {"id": "pipeline_id"}

    def test_enabling_pipeline(self):
        """Test enabling_pipeline"""
        self.controller.enabling_pipeline("pipeline_id")
        assert self.controller.db.pipelines.find_one_and_update.call_count == 2
        args = self.controller.db.pipelines.find_one_and_update.call_args[0]
        # Only registers second call which disables previous enabled pipeline
        assert args[1]["$set"]["status"] == "disabled"

    def test_enabled_pipeline(self):
        """Test enabled_pipeline"""
        self.controller.enabled_pipeline("pipeline_id")
        assert self.controller.db.pipelines.find_one_and_update.call_count == 1
        args = self.controller.db.pipelines.find_one_and_update.call_args[0]
        assert args[0] == {"id": "pipeline_id"}
        assert args[1]["$set"]["status"] == "enabled"

    def test_disabling_pipeline(self):
        """Test disabling_pipeline"""
        self.controller.disabling_pipeline("pipeline_id")
        assert self.controller.db.pipelines.find_one_and_update.call_count == 1
        args = self.controller.db.pipelines.find_one_and_update.call_args[0]
        assert args[0] == {"id": "pipeline_id"}
        assert args[1]["$set"]["status"] == "disabling"

    def test_disabled_pipeline(self):
        """Test disabled_pipeline"""
        self.controller.disabled_pipeline("pipeline_id")
        assert self.controller.db.pipelines.find_one_and_update.call_count == 1
        args = self.controller.db.pipelines.find_one_and_update.call_args[0]
        assert args[0] == {"id": "pipeline_id"}
        assert args[1]["$set"]["status"] == "disabled"
