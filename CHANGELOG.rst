#########
Changelog
#########
All notable changes to the of_multi_table NApp will be documented in this file.

[UNRELEASED] - Under development
********************************

[2025.2.0] - 2026-02-02
***********************

No major changes since the last release.

[2025.1.0] - 2025-04-14
***********************

Fixed
=====
- Fixed exception message when a Napp loads before ``of_multi_table``. Now it logs an ``ERROR`` message instead.

[2024.1.1] - 2024-08-04
***********************

Changed
=======
- Included ``owner`` attribute when deleting flows

[2024.1.0] - 2024-07-23
***********************

Changed
=======
- Updated python environment installation from 3.9 to 3.11

Removed
=======
- Removed client side batching with ``BATCH_INTERVAL`` and ``BATCH_SIZE``, now replaced with pacing in ``flow_manager``

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
