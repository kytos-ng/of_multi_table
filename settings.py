"""Module with the Constants used in the kytos/of_multi_table."""

FLOW_MANAGER_URL = "http://localhost:8181/api/kytos/flow_manager"
COOKIE_PREFIX = 0xAD

# NApps that push flows and are subscribed to enable_table event
SUBSCRIBED_NAPPS = {"coloring", "of_lldp", "mef_eline", "telemetry_int"}

DEFAULT_PIPELINE = {
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
