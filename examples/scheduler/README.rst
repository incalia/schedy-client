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
  ./add_job.py # same as running: schedy push MinimizeManual -p x 1 y 2
  ./worker.py # Press Ctrl+C to stop after the first error message is displayed

Files
-----

- `create_experiment.py <create_experiment.py>`_: Create and configure a manual
  experiment.
- `add_job.py <add_job.py>`_: Enqueue a job to the experiment.
- `worker.py <worker.py>`_: Worker for this experiment.

