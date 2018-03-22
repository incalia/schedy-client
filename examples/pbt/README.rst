Population Based Training
=========================

This example shows how to use Population Based Training to optimize a Convolutional Neural Network to 
perform image classification on the MNIST dataset.

How do I run it?
----------------

The following commands will train 50 jobs:

.. code-block:: bash

  ./create_experiment.py
  for i in $(seq 50); do ./keras_worker.py; done

Files
-----

- `create_experiment.py <create_experiment.py>`_: Create and configure a PBT experiment.
- `keras_worker.py <keras_worker.py>`_: Worker for this experiment, implemented using `Keras <https://keras.io/>`_.
