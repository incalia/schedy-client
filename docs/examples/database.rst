Using Schedy as a database
==========================

Schedy can be used as a simple database to store experiments. Schedy has two
main concepts: experiments, and jobs. An experiment is a set of jobs, each job
being a *trial* for its experiment.

For this example, let's say you are trying to find the values of ``x`` and ``y``
that minimize ``x^2 * y^2``. First, you would create an experiment in Schedy:

.. code-block:: bash

    schedy add MinimizeSimple manual

... or, in Python::

    import schedy

    db = schedy.SchedyDB()
    exp = schedy.ManualSearch('MinimizeSimple')
    db.add_experiment(exp)

This creates a new experiment called *MinimizeSimple*. The keyword *manual*
tells Schedy that you are going to manage the jobs of this experiment yourself.
More on that later.

Now, let's try many values of ``x`` and ``y`` to find which one works the best. If
you do it by hand, you can record all your results in Schedy by creating new
jobs. For each job, tell Schedy which parameters you tried, and what results you
obtained.

.. code-block:: bash

    schedy push MinimizeSimple --status DONE --hyperparameters x 1 y 2 --results result 5
    # Or, for short:
    schedy push MinimizeSimple -s DONE -p x 1 y 2 -r result 5

... or, in Python::

    import schedy

    db = schedy.SchedyDB()
    exp = db.get_experiment('MinimizeSimple')
    job = exp.add_job(
        status=schedy.Job.DONE,
        hyperparameters={
            'x': 1,
            'y': 2,
        },
        results={
            'result': 5
        },
    )

You just added a new job to the experiment *MinimizeSimple*, which is *DONE*
(finished). You tried ``x = 1`` and ``y = 2``, and the *result* was 5 (``1^2 +
2^2``). Of course you could try to compute this expression for a bunch of
values, then push the jobs to the database by hand, but a program would be much
better at doing this.

Let's do this::

    import schedy
    import random

    db = schedy.SchedyDB()
    experiment = db.get_experiment('MinimizeSimple')
    for i in range(20):
        # Test the problem for random values of x and y, 20 times
        x = random.uniform(-100, 100)
        y = random.uniform(-100, 100)
        result = x ** 2 + y ** 2
        # Tell Schedy about it!
        experiment.add_job(status=schedy.Job.DONE, hyperparameters={'x': x, 'y': y}, results={'result': result})

Not too difficult right? Now let's see how we performed, by listing the results
of each job. The easiest way is to use your `online dashboard
<https://schedy.io/>`_.

However, if you want to do it using the command line, you can run:

.. code-block:: bash

    # The -t flag indicates that we want the description of the jobs, not only
    # their name, and that we want them in a table
    schedy list -t MinimizeSimple
    # You could also use the -p flag to display the jobs as a paragraph (this
    # can be useful when you have lots of hyperparameters/results)
    # schedy list -p MinimizeSimple

.. code-block:: none

    +--------+----------+-----------+----------+------------+-----------+
    | id     | status   |   quality |        x |          y |    result |
    |--------+----------+-----------+----------+------------+-----------|
    | -bPmlQ | DONE     |         0 |  15.0542 |   3.27561  |   237.36  |
    | 06wn6w | DONE     |         0 |  27.7519 |   0.301546 |   770.257 |
    | 0jjY2Q | DONE     |         0 |  95.2792 |  36.0534   | 10378     |
    | 5Jz0hA | DONE     |         0 | -60.2291 | -19.56     |  4010.13  |
    | 8_7e5Q | DONE     |         0 |  24.3572 |  19.2384   |   963.389 |
    | IOHsSw | DONE     |         0 | -82.2053 | -82.4315   | 13552.7   |
    | M4m6CA | DONE     |         0 | -66.6737 |  41.7379   |  6187.44  |
    | MQmuTw | DONE     |         0 |  27.3775 | -31.1913   |  1722.43  |
    | NavIrw | DONE     |         0 |   1      |   2        |     5     |
    | NiHt6A | DONE     |         0 |  79.5122 | -74.5573   | 11881     |
    | OP7aGw | DONE     |         0 | -12.5107 |  -0.683612 |   156.985 |
    | Wjz2Wg | DONE     |         0 |  81.5054 | -66.08     | 11009.7   |
    | ZM3nww | DONE     |         0 |  66.9189 | -52.3469   |  7218.33  |
    | b6T0TA | DONE     |         0 |  70.9641 | -70.5859   | 10018.3   |
    | csui0g | DONE     |         0 |  71.7953 |  49.0019   |  7555.74  |
    | gRjRQA | DONE     |         0 | -47.0694 | -25.1969   |  2850.42  |
    | gqfFQg | DONE     |         0 | -35.5846 | -46.4451   |  3423.41  |
    | m0f9vA | DONE     |         0 | -80.614  | -72.4938   | 11754     |
    | mL2NXw | DONE     |         0 |  18.0392 | -13.1687   |   498.828 |
    | n8tNMQ | DONE     |         0 |  77.8921 |  80.532    | 12552.6   |
    | yFvyFQ | DONE     |         0 | -41.0681 |  96.7539   | 11047.9   |
    +--------+----------+-----------+----------+------------+-----------+

We are pretty far from the optimal result, but that's normal considering
we tried only 20 combinations of hyperparameters.

Note that you can also access all these values using the Python API::

    import schedy

    db = schedy.SchedyDB()
    exp = db.get_experiment('MinimizeSimple')
    for job in exp.all_jobs():
        print('Id:', job.job_id)
        print('Status:', job.status)
        print('Quality', job.quality)
        print('Hyperparameters:')
        for name, value in job.hyperparameters.items():
            print('- {}: {}'.format(name, value))
        print('Results:')
        for name, value in job.results.items():
            print('- {}: {}'.format(name, value))
        print()


You might be wondering:

.. epigraph::

    There are a lot of results. Can't we sort these jobs from the best to the
    worst?

Well of course! He're how you would do it:

.. code-block:: bash
    
    schedy list -t MinimizeSimple -s result

.. code-block:: none

    +--------+----------+-----------+----------+------------+-----------+
    | id     | status   |   quality |        x |          y |    result |
    |--------+----------+-----------+----------+------------+-----------|
    | NavIrw | DONE     |         0 |   1      |   2        |     5     |
    | OP7aGw | DONE     |         0 | -12.5107 |  -0.683612 |   156.985 |
    | -bPmlQ | DONE     |         0 |  15.0542 |   3.27561  |   237.36  |
    | mL2NXw | DONE     |         0 |  18.0392 | -13.1687   |   498.828 |
    | 06wn6w | DONE     |         0 |  27.7519 |   0.301546 |   770.257 |
    | 8_7e5Q | DONE     |         0 |  24.3572 |  19.2384   |   963.389 |
    | MQmuTw | DONE     |         0 |  27.3775 | -31.1913   |  1722.43  |
    | gRjRQA | DONE     |         0 | -47.0694 | -25.1969   |  2850.42  |
    | gqfFQg | DONE     |         0 | -35.5846 | -46.4451   |  3423.41  |
    | 5Jz0hA | DONE     |         0 | -60.2291 | -19.56     |  4010.13  |
    | M4m6CA | DONE     |         0 | -66.6737 |  41.7379   |  6187.44  |
    | ZM3nww | DONE     |         0 |  66.9189 | -52.3469   |  7218.33  |
    | csui0g | DONE     |         0 |  71.7953 |  49.0019   |  7555.74  |
    | b6T0TA | DONE     |         0 |  70.9641 | -70.5859   | 10018.3   |
    | 0jjY2Q | DONE     |         0 |  95.2792 |  36.0534   | 10378     |
    | Wjz2Wg | DONE     |         0 |  81.5054 | -66.08     | 11009.7   |
    | yFvyFQ | DONE     |         0 | -41.0681 |  96.7539   | 11047.9   |
    | m0f9vA | DONE     |         0 | -80.614  | -72.4938   | 11754     |
    | NiHt6A | DONE     |         0 |  79.5122 | -74.5573   | 11881     |
    | n8tNMQ | DONE     |         0 |  77.8921 |  80.532    | 12552.6   |
    | IOHsSw | DONE     |         0 | -82.2053 | -82.4315   | 13552.7   |
    +--------+----------+-----------+----------+------------+-----------+

Once you are done, you can remove the experiment, so that it does not appear in
your listings later, as this is just an experiment for the tutorial.

.. code-block:: bash

    schedy rm MinimizeSimple
    # You could also remove a single job using:
    # schedy rm MinimizeSimple NavIrw

... or, in Python::
    
    import schedy

    db = schedy.SchedyDB()
    db.get_experiment('MinimizeSimple').delete()
    # Or, to delete a specific job:
    # db.get_experiment('MinimizeSimple').get_job('NavIrw').delete()


However, do not hesitate to keep your real experiments in the database, if you
want to keep track of them. You don't have to remove them if you don't want to!

