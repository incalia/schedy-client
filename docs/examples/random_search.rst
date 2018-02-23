Random search
=============

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

As you can see, we're using a ``random`` scheduler this time, instead of a
``manual`` one. And we're defining the random variables immediately after this.
The parameters of each distribution are supplied using JSON notation. We'll
talk more about the supported distributions [later](#available-distributions).

The worker file does not change much.

::

    db = schedy.SchedyDB()
    experiment = db.get_experiment('MinimizeRandom')
    for i in range(20):
        try:
            with experiment.next_job() as job:
                x = job.hyperparameters['x']
                y = job.hyperparameters['y']
                time.sleep(10) # Simulate computing time
                result = x ** 2 + y ** 2
                job.results['result'] = result
        except Exception as e:
            print(e)
            # Wait a minute before issuing the next request
            time.sleep(60)

As you can see all we changed was the name of the experiment. We also changed
the infinite loop to a finite loop, because the random search scheduler will
continuously send new jobs to us. We wouldn't want to spam the Schedy database
with millions of jobs just because we're able to compute a result in a few
nanoseconds, right?

Once again, you can start the worker, then list your results using:

.. code-block:: bash

    schedy list -p MinimizeRandom

.. code-block:: none

    Id: E4wM_Q
    Status: DONE
    Quality: 0.0
    Hyperparameters:
     - x: 0.7631796730117579
     - y: 1.7928643416416767
    Results:
     - result: 3.7968057608285766

    Id: HeoaOw
    Status: DONE
    Quality: 0.0
    Hyperparameters:
     - y: 0.4081494909274223
     - x: -7.726479873690085
    Results:
     - result: 59.86507724548227

    Id: UdbGfQ
    Status: RUNNING
    Quality: 0.0
    Hyperparameters:
     - y: -1.0508884097470883
     - x: 6.625251239195508
    ...

As you can see, since I launched this while the worker was still running, one
of my jobs has the status "RUNNING" (and no result). This is the job that is
currently being processed by the worker.

Available distributions
-----------------------

Because this is a toy problem, using arbitrary normal distributions does not
have a lot of impact. But in practice, the distributions you choose for your
hyperparameters could change how fast you find a good solution.

In order to help you in this regard, Schedy offers several type of
distributions:

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
