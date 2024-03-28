[UNRELEASED] - Under development
********************************

Changed
=======
- Updated python environment installation from 3.9 to 3.11
- Updated test dependencies

[2023.2.0] - 2024-02-16
***********************

Added
=====
- Subscribed to ``"kytos/telemetry_int.enable_table"`` to support ``telemetry_int``

Changed
=======

- Replaced ``telemetry_int`` ``base`` table group with ``evpl`` and ``epl`` by default using table 2 and 3 respectively
- If a KytosEvent can't be put on ``buffers.app`` during ``setup()``, it'll make the NApp to fail to start

[2023.1.0] - 2023-06-12
***********************

Added
=====
- This NApp was created on this version
