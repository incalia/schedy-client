Random search
=============

This example shows how to use Schedy to find the best hyperparameters for an
experiment using random search.

(See the `associated tutorial
<http://schedy.readthedocs.io/en/latest/examples/random_search.html>`_ for more
information.)

How do I run this example?
----------------

.. code-block:: bash

  ./create_experiment.py
  # The previous command is equivalent to running:
  # schedy add MinimizeRandom random x normal '{"mean": 0, "std": 5}' y normal '{"mean": 0, "std": 2}'
  ./worker.py

Files
-----

- `create_experiment.py <create_experiment.py>`_: Create and configure a random search
  experiment.
- `worker.py <worker.py>`_: Worker for this experiment.


