"""Tests for DB models"""
from db.models import PipelineBaseDoc


class TestDBModels():
    """Test the DB models"""

    def setup_method(self):
        """Execute steps before each test"""
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
