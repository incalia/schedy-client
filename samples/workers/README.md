# Schedy as a scheduler

Schedy was primarily designed to be used as a scheduler, that is to say a
service that orchestrates a cluster of workers by telling them which
hyperparameters to try. The simplest way to do that is by creating a queue of
jobs. Each of them will be pulled by a worker, which will try the set of
hyperparameters, and report how it performed.

Let's use the same problem as before, that is to say the minimization of `x^2 +
y^2`. First, we will create an experiment.

```bash
schedy add MinimizeManual manual
```

Let's create a worker using the Schedy Python API.

```python
import schedy
import time

db = schedy.SchedyDB()
experiment = db.get_experiment('MinimizeManual')
while True:
    try:
        with experiment.next_job() as job:
            x = job.hyperparameters['x']
            y = job.hyperparameters['y']
            result = x ** 2 + y ** 2
            job.results['result'] = result
    except Exception as e:
        print(e)
        time.sleep(60)
```

As you can see, this is just a script that pulls jobs from Schedy, computes the
results, and pushes the jobs back to Schedy. In case of crash it will just keep
on trying. Here's a quick explanation of it in more detail:

```python
import schedy
import time

db = schedy.SchedyDB()
experiment = db.get_experiment('MinimizeManual')
while True:
```

We initialize Schedy and retrieve the experiment we just created, then start an
infinite loop in which we'll handle incoming jobs.

```python
    try:
        with experiment.next_job() as job:
            x = job.hyperparameters['x']
            y = job.hyperparameters['y']
            result = x ** 2 + y ** 2
            job.results['result'] = result
```

We pull the next job, and start working on it. The `with` statement is there so
that we always report to Schedy whether the job has crashed or succeeded. The
results will only be pushed to Schedy at the end of the `with` statement. If you
wanted to report intermediary results to Schedy before the `with` statement
end, you could call `job.put()`.

```python
    except Exception as e:
        print(e)
        time.sleep(60)
```

If something failed, print what went wrong and wait a minute before retrying.
If everything was fine, pull the next job immediately.

You can run the worker (i.e. this script) in another terminal, in the
background, on the nodes of your cluster... You might notice it start by
printing errors like this one:

> HTTP Error None:
>
> \> No job left for experiment MinimizeManual.

This is normal and fine, as you do not have enqueued any job to your experiment
yet. You can keep the script running, as it will detect the new job as soon as
we enqueue it (or in the worst-case scenario, 60 seconds after that).

Let's ask the worker to compute the result using `x = 1` and `y = 2`.

```bash
schedy push MinimizeManual -p x 1 y 2
```

After at most 60 seconds, the worker should have computed the result and
reported back. You can see the result using:

```bash
schedy list -l MinimizeManual
# Or, if you only want to see the results of the job you just pushed instead of the whole list:
schedy show MinimizeManual <job-id>
```

*The id of the job was given to you when you pushed it. It is a sequence of
random characters that should look like this: fVKGjg.*

You should see something like this:

```bash
Id: fVKGjg
Status: DONE
Quality: 0.0
Hyperparameters:
 - x: 1
 - y: 2
Results:
 - result: 5
```

If you don't, and the status is still `QUEUED`, just wait a few seconds until
the worker pulls the experiment.

Schedy will always make sure that only one worker will work on a given job
(multiple workers will never pull the same job).

> But do I always have to push my jobs by hand? What if I want to do a
> systematic search (e.g. random search)?

Don't worry we've got you covered.
