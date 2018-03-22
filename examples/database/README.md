# Using Schedy as a database

Schedy can be used as a simple database to store experiments. Schedy has two
main concepts: experiments, and jobs. An experiment is a set of jobs, each job
being a *trial* for its experiment.

For this example, let's say you are trying to find the value of `x` and `y`
that minimize `x^2 * y^2`. First, you would create an experiment in Schedy:

```bash
schedy add MinimizeSimple manual
```

This creates a new experience called *MinimizeSimple*. The keyword *manual*
tells Schedy that you are going to manage the jobs of this experiment yourself.
More on that later.

Now, let's try many values of `x` and `y` to find which one works the best. If
you do it by hand, you can record all your results in Schedy by creating new
jobs. For each job, tell Schedy which parameters you tried, and what result you
obtained.

```bash
schedy push MinimizeSimple --status DONE --hyperparameters x 1 y 2 --results result 5
# Or, for short:
schedy push MinimizeSimple -s DONE -p x 1 y 2 -r result 5
```

You just added a new job to the experiment *MinimizeSimple*, which is *DONE*
(finished). You tried `x = 1` and `y = 2`, and the *result* was 5 (`1^2 +
2^2`). Of course you could try to compute this expression for a bunch of
values, then push the jobs to the database by hand, but a program would be much
better at doing this.

Let's do this.

```python
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
    experiment.add_job(status=schedy.JOB_DONE, hyperparameters={'x': x, 'y': y}, results={'result': result})
```

Not too difficult right? Now let's see how we performed, by listing the results of each job.

```bash
# The -l flag indicates that we want the description of the jobs, not only their name
schedy list -l TestExperiment
```

```
Id: -Dce1A
Status: DONE
Quality: 0.0
Hyperparameters:
 - x: 0.5466782001607378
 - y: 2.670232673684742
Results:
 - result: 7.428999586144551

Id: 0cihqg
Status: DONE
Quality: 0.0
Hyperparameters:
 - x: -1.6405009632413652
 - y: 6.194904234971965
Results:
 - result: 41.06808189086943

Id: 1gOdxA
Status: DONE
Quality: 0.0
Hyperparameters:
 - y: -8.87377254969895
 - x: -5.764568950850821
Results:
 - result: 111.97409445290394
...
```

We are pretty far from the optimal result, but that's normal considering
we were trying values of `x` and `y` at random.

You might be wondering:

> There are a lot of results. Can't we sort these jobs from the best to the
> worst?

TODO

Once you are done, you can remove the experiment, so that it does not appear in
your listings later, as this is just an experiment for the tutorial.

```python
schedy rm MinimizeSimple
# You could also remove a single job using:
schedy rm MinimizeSimple <job-id>
```

However, do not hesitate to keep your real experiments in the database, if you
want to keep track of them. You don't have to remove them if you don't want to!

Next tutorial: [Schedy as a scheduler](../workers/README.md)
