Welcome to Schedy's documentation!
==================================

**Schedy** is your machine learning assistant. It will help you record your
experiments, your results, visualize them, and it will even suggest new
parameters for your next experiments!

Schedy can do useful things for you:

- Record the hyperparameters and results of all your past models.
- Suggest new hyperparameters for your next models.
- Coordinate a pool of workers (e.g. in a cluster), by making sure they
  stay busy trying to find the best combination of hyperparameters for
  your task.

And all of that in just a few lines of code! Coordinating a cluster of workers
becomes as simple as this:

.. code-block:: python

   import schedy

   db = schedy.SchedyDB()
   exp = db.get_experiment('My Task')
   while True:
      with exp.next_job() as job:
         my_train_function(job)

You can follow the evolution of your experiments thanks to our `online dashboard
<https://schedy.io/>`_.

.. image:: https://raw.githubusercontent.com/incalia/schedy-client/master/docs/images/dashboard.png
  :align: center

We also provide a command line tool, that will help you with the most
repetitive tasks.

.. _setup:

Installation and setup
----------------------

`Sign up here <https://schedy.io>`_, install Schedy & get your API token:

.. code-block:: bash

   pip3 install schedy
   schedy gen-token

You are now ready to `get started <https://schedy.readthedocs.io/en/latest/getting_started.html>`_!

You can also read the `API reference <https://schedy.readthedocs.io/en/latest/reference.html>`_.
