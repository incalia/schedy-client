Using Schedy as a database
==========================

This example shows how to store the results of your experiments using Schedy,
so that you can retrieve them later using the command line or the `online
dashboard <https://schedy.io/>`_.

(See the `associated tutorial
<http://schedy.readthedocs.io/en/latest/examples/database.html>`_ for more
information.)

How do I run this example?
----------------

.. code-block:: bash

  ./create_experiment.py # same as running: schedy add MinimizeSimple manual
  ./worker.py

Files
-----

- `create_experiment.py <create_experiment.py>`_: Create and configure a manual
  experiment.
- `worker.py <worker.py>`_: Worker for this experiment.

