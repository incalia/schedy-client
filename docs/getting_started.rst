Getting started
===============

Before going through this section, make sure you have :ref:`installed Schedy <setup>`.

Schedy is the combination of three tools:

- A Python API.
- An online `dashboard <https://schedy.io>`_, that will help you visualize your
  experiments.
- A command line tool, ``schedy``, that can help you with the basic setup and
  monitoring of your experiments.

Using the command line tool is totally optional. It simply wraps up the most
common operations you would perform with the Python API.

For example, running ``schedy add MyTask manual`` in the command line tool is
the same as running the following Python script::

   import schedy

   db = schedy.SchedyDB()
   exp = schedy.ManualSearch('MyTask')
   db.add_experiment(exp)

Database, experiments and jobs
------------------------------

When using Schedy, you store all your hyperparameters and results in the Schedy
*database*, represented by the SchedyDB object. You can access these
experiments and jobs from any workstation with your credentials (the ones you
retrieved using ``schedy gen-token`` or on the website).

An *experiment* is a topic, a single task, for which you try to find the best
configuration of hyperparameters. Examples of experiments are:

- Trying to fit a linear regression on your dataset
- Trying to train a Random Forest to predict tomorrow's temperature
- Trying to classify objects in a picture using an ResNet-50
- ...

A *job* is a trial for an experiment. A job tries to fulfill the task using a
set of hyperparameters. Once it has completed its task, it reports how well it
performed, by updating its results. (Actually, a job can also report results
while it is running, e.g. the training loss associated to each epoch while
training a neural network.)

