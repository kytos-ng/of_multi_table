"""Module with the Constants used in the kytos/of_multi_table."""
FLOW_MANAGER_URL = "http://localhost:8181/api/kytos/flow_manager"
COOKIE_PREFIX = 0xad

# NApps that push flows and are subscribed to enable_table event
SUBSCRIBED_NAPPS = {"coloring", "of_lldp", "mef_eline"}

BASIC_PIPELINE = {"multi_table": [{
    "table_id": 0,
    "napps_table_groups": {
        "coloring": ["base"],
        "of_lldp": ["base"],
        "mef_eline": ["evpl", "epl"]
        }
    }]}
