Schedy as a scheduler
=====================

This example shows how to use Schedy to orchestrate one or several workers.

(See the `associated tutorial
<http://schedy.readthedocs.io/en/latest/examples/scheduler.html>`_ for more
information.)

How do I run this example?
----------------

.. code-block:: bash

  ./create_experiment.py # same as running: schedy add MinimizeManual manual
  ./worker.py

Files
-----

- `create_experiment.py <create_experiment.py>`_: Create and configure a manual
  experiment.
- `worker.py <worker.py>`_: Worker for this experiment.

