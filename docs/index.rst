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
becomes as simple as this::

   import schedy

   db = schedy.SchedyDB()
   exp = db.get_experiment('My Task')
   while True:
      with exp.next_job() as job:
         my_train_function(job)

You can follow the evolution of your experiment thanks to our `online dashboard
<https://schedy.io>`_.

.. todo:: Add image of dashboard

We also provide a command line tool, that will help you with the most
repetitive tasks.

.. _setup:

Installation and setup
----------------------

Install Schedy::

   pip3 install schedy

`Sign up for free <https://schedy.io>`_

Get your API token::

   schedy gen-token

You are now ready to :doc:`get started </getting_started>`!

.. toctree::
   :hidden:
   :maxdepth: 2

   Homepage <self>

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   examples
   reference

Other
-----

* :ref:`Alphabetical index <genindex>`
* :ref:`Modules index <modindex>`