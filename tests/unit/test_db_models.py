"""Tests for DB models"""
import pytest
from db.models import PipelineBaseDoc
from pydantic import ValidationError


class TestDBModels:
    """Test the DB models"""

    def setup_method(self):
        """Execute steps before each test"""
        self.pipeline = {
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
                    "napps_table_groups": {"of_lldp": ["base"]},
                }
            ]
        }

    def test_pipelinebasedoc(self):
        """Test PipelineBaseDoc"""
        pipeline = PipelineBaseDoc(**self.pipeline)
        multi_table = pipeline.multi_table[0]
        table_miss_flow = multi_table.table_miss_flow
        assert pipeline.status == "disabled"
        assert multi_table.table_id == 0
        assert multi_table.description == "Table for testing"
        assert multi_table.napps_table_groups["of_lldp"] == ["base"]
        assert table_miss_flow.priority == 0
        assert len(table_miss_flow.instructions) == 1

    def test_validate_table_group(self):
        """Test validate table group"""
        pipeline = {
            "multi_table": [
                {
                    "table_id": 0,
                    "table_miss_flow": {
                        "priority": 0,
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
                            {"instruction_type": "goto_table", "table_id": 1}
                        ],
                    },
                },
            ]
        }
        with pytest.raises(ValidationError):
            PipelineBaseDoc(**pipeline)

    def test_validate_intructions(self):
        """Test validate instructions"""
        pipeline = {
            "multi_table": [
                {"table_id": 0, "napps_table_groups": {"mef_eline": ["epl"]}},
                {"table_id": 1, "napps_table_groups": {"mef_eline": ["evpl", "epl"]}},
            ]
        }
        with pytest.raises(ValidationError):
            PipelineBaseDoc(**pipeline)

    def test_validate_table_id(self):
        """Test validate table id"""
        pipeline = {"multi_table": [{"table_id": 1}, {"table_id": 1}]}
        with pytest.raises(ValidationError):
            PipelineBaseDoc(**pipeline)
