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
                "telemetry_int": ["base"],
            },
        }
    ]
}

# BATCH_INTERVAL: time interval between batch requests that will be sent to
# flow_manager (in seconds) - zero enable sending all the requests in a row
BATCH_INTERVAL = 0.5

# BATCH_SIZE: size of a batch request that will be sent to flow_manager, in
# number of FlowMod requests. Use 0 (zero) to disable BATCH mode, i.e. sends
# everything at a glance
BATCH_SIZE = 50
