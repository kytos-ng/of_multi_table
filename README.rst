|Stable| |Tag| |License| |Build| |Coverage| |Quality|

.. raw:: html

  <div align="center">
    <h1><code>kytos/of_multi_table</code></h1>

    <strong>This NApp implements Oplenflow multi tables</strong>

  </div>

Overview
========

This NApp implements Oplenflow multi tables

:warning: Uninstallation :warning:

If you are going to uninstall this NApp be sure to disable the current pipeline from database.

Requirements
============

This NApp needs consistency check to ensure miss flow entries installation. Ensure that ``ENABLE_CONSISTENCY_CHECK`` is `True` in the settings file from ``flow_manager``
The following NApps are also required:

- `kytos-ng/flow_manager <https://github.com/kytos-ng/flow_manager.git>`_
- `kytos-ng/of_core <https://github.com/kytos-ng/of_core>`_
- `MongoDB <https://github.com/kytos-ng/kytos#how-to-use-with-mongodb>`_

Events
======

Subscribed
----------

- ``kytos/flow_manager.flow.added``
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

.. |Stable| image:: https://img.shields.io/badge/stability-stable-green.svg
   :target: https://github.com/kytos-ng/of_multi_table
.. |License| image:: https://img.shields.io/github/license/kytos-ng/kytos.svg
    :target: https://github.com/kytos-ng/of_multi_table/blob/master/LICENSE
.. |Build| image:: https://scrutinizer-ci.com/g/kytos-ng/of_multi_table/badges/build.png?b=master
    :alt: Build status
    :target: https://scrutinizer-ci.com/g/kytos-ng/of_multi_table/?branch=master
.. |Tag| image:: https://img.shields.io/github/tag/kytos-ng/of_multi_table.svg
    :target: https://github.com/kytos-ng/of_multi_table/tags
.. |Coverage| image:: https://scrutinizer-ci.com/g/kytos-ng/of_multi_table/badges/coverage.png?b=master
    :alt: Code coverage
    :target: https://scrutinizer-ci.com/g/kytos-ng/of_multi_table/?branch=master
.. |Quality| image:: https://scrutinizer-ci.com/g/kytos-ng/of_multi_table/badges/quality-score.png?b=master
    :alt: Code-quality score
    :target: https://scrutinizer-ci.com/g/kytos-ng/of_multi_table/?branch=master
