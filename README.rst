|License|

.. raw:: html

  <div align="center">
    <h1><code>kytos-ng/of_multi_table</code></h1>

    <strong>This NApp implements Oplenflow multi tables</strong>

  </div>

Overview
========

This NApp implements Oplenflow multi tables

Requirements
============

- `kytos-ng/flow_manager <https://github.com/kytos-ng/flow_manager.git>`_
- `kytos-ng/of_core <https://github.com/kytos-ng/of_core>`_
- `MongoDB <https://github.com/kytos-ng/kytos#how-to-use-with-mongodb>`_

Events
======

Subscribed
----------

- ``kytos/flow_manager.flow.added``
- ``kytos/of_core.handshake.completed``
- ``kytos/flow_manager.flow.error``
- ``kytos/[mef_eline|telemetry_int|coloring|of_lldp].enable_table``

Generated
---------

kytos/of_multi_table.enable_table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This event should sent before any NApp sends its first flow to be published.

Content:

.. code-block:: python3
    
    {
      "mef_eline": {"epl": 3, "evpl": 2},
      "of_lldp": {"base": 0},
      "coloring": {"base": 0}
    }

.. TAGs

.. |License| image:: https://img.shields.io/github/license/kytos-ng/kytos.svg
    :target: https://github.com/kytos-ng/of_multi_table/blob/master/LICENSE