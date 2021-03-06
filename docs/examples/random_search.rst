Random search
=============

*The scripts created in this tutorial can be found in our* `GitHub repository
<https://github.com/incalia/schedy-client/tree/master/examples/random_search>`_ .

A simple example
----------------

In the last tutorial, we learned how to create a manual scheduler. When using a
manual scheduler, you have a worker (or a pool of workers) treating jobs that
you submit to a queue manually. This is useful for manual finetuning, when you
know which hyperparameters you would like to try.

However, in many cases, you would like to explore the space of hyperparameters
automatically, using a black-box optimization algorithm for instance. This is
where automatic schedulers become useful.

Random search is one of the most basic schedulers there are: it will simply
create jobs, whose hyperparameters will be randomly picked. The distribution
of these hyperparameters must be chosen by yourself. Using the previous example
(finding the values of ``x`` and ``y`` that minimize ``x^2 + y^2``), you could define
these distributions using your instincts. For instance, we'll make ``x`` and ``y``
follow a normal distribution, centered around *0* with a standard deviation of
*5* for ``x``, and 2 for ``y`` (yes, this is totally arbitrary).

.. code-block:: bash

    schedy add MinimizeRandom random x normal '{"mean": 0, "std": 5}' y normal '{"mean": 0, "std": 2}'

... or, in Python::

    import schedy

    db = schedy.SchedyDB()
    distributions = {
        'x': schedy.random.Normal(0, 5),
        'y': schedy.random.Normal(0, 2),
    }
    experiment = schedy.RandomSearch('MinimizeRandom', distributions)
    db.add_experiment(experiment)

As you can see, we're using a ``random`` scheduler this time, instead of a
``manual`` one. And we're defining the random variables immediately after this.
The parameters of each distribution are supplied using JSON notation. We'll
talk more about the supported distributions :ref:`later <available_distributions>`.

The worker file does not change much::

    import schedy
    import time

    db = schedy.SchedyDB()
    experiment = db.get_experiment('MinimizeRandom')
    for i in range(20):
        try:
            with experiment.next_job() as job:
                x = job.hyperparameters['x']
                y = job.hyperparameters['y']
                result = x ** 2 + y ** 2
                job.results['result'] = result
        except Exception as e:
            print(e)
            # Wait a minute before issuing the next request
            time.sleep(60)

As you can see all we changed was the name of the experiment. We also changed
the infinite loop to a finite loop, because the random search scheduler will
continuously send new jobs to us. Because we are able to perform a task in a
few nanoseconds, an infinite loop would create several thousand jobs per second
and spam the database (remember, we're not trying to optimize a neural network
here, we're just minimizing ``x^2 + y^2``).

Once again, you can start the worker, then list your results using:

.. code-block:: bash

    schedy list -t MinimizeRandom

.. code-block:: none

    +--------+----------+------------+------------+-----------+
    | id     | status   |          x |          y |    result |
    |--------+----------+------------+------------+-----------|
    | 2WDn_w | DONE     |  -0.836867 | -0.71981   |   1.21847 |
    | m4hoTw | DONE     |  -1.15003  | -0.83331   |   2.01698 |
    | l26a6g | DONE     |   0.862245 |  1.27614   |   2.372   |
    | ZDmNqw | DONE     |  -2.52887  |  0.429102  |   6.57931 |
    | LMEOaQ | DONE     |   2.86853  | -0.742761  |   8.78014 |
    | iKCzuw | DONE     |   2.47215  |  1.95058   |   9.91631 |
    | E6K6Ew | DONE     |  -2.90947  |  1.81924   |  11.7746  |
    | hRaPOQ | DONE     |   2.63032  |  3.00305   |  15.9369  |
    | Tby5Og | DONE     |  -3.68871  |  1.66496   |  16.3787  |
    | b0pp7g | DONE     |   1.76621  |  4.14727   |  20.3194  |
    | NZQw7w | DONE     |   4.92685  |  0.71905   |  24.7909  |
    | sMUVuA | DONE     |   5.58645  |  1.50509   |  33.4737  |
    | zLxjYA | DONE     |   6.70355  |  0.0705488 |  44.9426  |
    | hDi9uw | DONE     |  -6.75093  |  1.57475   |  48.0549  |
    | oMcmeQ | DONE     |  -7.17896  |  0.100174  |  51.5475  |
    | fF8NHQ | DONE     |   7.20394  |  0.692157  |  52.3758  |
    | tKwlHw | DONE     |   9.02237  |  0.156419  |  81.4276  |
    | m9G7GA | DONE     |   8.18227  |  3.95599   |  82.5994  |
    | 7MgmuA | DONE     |  10.0929   | -2.78685   | 109.634   |
    | l8L6xQ | DONE     | -10.6514   | -0.970788  | 114.395   |
    +--------+----------+------------+------------+-----------+

.. _available_distributions:

Available distributions
-----------------------

Because this is a toy problem, using arbitrary normal distributions does not
have a lot of impact. But in practice, the distributions you choose for your
hyperparameters could change how fast you find a good solution.

In order to help you in this regard, Schedy offers several type of
distributions. The following is a short description of these distributions (see
also: :doc:`API reference </reference/random>`).

Uniform distribution
^^^^^^^^^^^^^^^^^^^^

Values will be uniformly distributed in the interval [``low``, ``high``).

Example:

.. code-block:: bash

    # One hyperparameter (x) with values ranging from 2.1 (included) to 5 (excluded)
    schedy add Test random x uniform '{"low": 2.1, "high": 5}'

Normal distribution
^^^^^^^^^^^^^^^^^^^

Values will be distributed following a normal distribution, centered around
``mean`` with a standard deviation of ``std``.

Example:

.. code-block:: bash

    schedy add Test random x normal '{"mean": 2.1, "std": 5}'

LogUniform distribution
^^^^^^^^^^^^^^^^^^^^^^^

Values will be distributed between ``low`` and ``high``, such that log(value) is
uniformly distributed between log(``low``) and log(``high``).

This might be useful for hyperparameters that only have an influence when they
change their order of magnitude (e.g. learning rates for neural networks).

Example:

.. code-block:: bash

    schedy add Test random x loguniform '{"low": 0.000001, "high": 0.1}'

Choice distribution
^^^^^^^^^^^^^^^^^^^

Values will be picked randomly in a set of ``values``. You can optionally provide
``weights`` for these values, to make some of them more likely to be suggested by
Schedy than others. The values can be numbers, strings, booleans, strings,
arrays or objects, and you can mix those.

Simple example:

.. code-block:: bash

    schedy add Test random x choice '{"values": [2, 4, 8, 10]}'

Advanced example:

.. code-block:: bash

    schedy add Test random x choice '{"values": [false, 1, "two", {"key": "three", "key2": 3}, [4, "four"]], "weights": [0.1, 0.2, 0.3, 0.3, 0.1]}'

Constant distribution
^^^^^^^^^^^^^^^^^^^^^

The value will always be the same. The value can be a number, a string, a
boolean, an array or an object. This can be useful to pass configuration
parameters to the workers, for instance.

.. code-block:: bash

    schedy add Test random x const 0 config const '{"log_dir": "/var/log", "schedy_rocks": true}'
