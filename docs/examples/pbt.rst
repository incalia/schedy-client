Population based training
=========================

`Population Based Training <https://arxiv.org/pdf/1711.09846.pdf>`_ (PBT) allows you
to train your models in a smarter way. It takes care of finding not only the
best set of hyperparameters, but it also able to find the best hyperparameters
schedule during training. For instance, having a fixed learning rate during
training is often suboptimal, so PBT helps you find out when and how you should
change your learning rate.

If you want to use Population Based Training with Schedy, you only need to know
the following:

PBT is an improvement over random search: it is able to focus on the most
promising jobs using to strategies:

- An *exploit* strategy, in which the least promising jobs are thrown away, and
  replaced by copies of the most promising ones. This allows you not to waste
  resources on the wrong jobs.

- An *explore* strategy, that tries new values for the hyperparameters of the
  most promising jobs during training. For instance, this is what allows you to
  find the optimal learning rate schedule of a neural network.

An example using PBT to finetune an Image Recognition neural network can be
found on our `GitHub repository
<https://github.com/incalia/schedy-client/tree/master/examples/pbt>`_.

Creating an experiment
----------------------

An experiment using Population Based Training can be created this way::

    import schedy
    db = schedy.SchedyDB()
    experiment = schedy.PopulationBasedTraining(
        'MNIST with PBT',
        schedy.pbt.MAXIMIZE,
        'max_accuracy',
        exploit=schedy.pbt.Truncate(),
        explore={
            'learning_rate': schedy.pbt.Perturb(),
            'dropout_rate': schedy.pbt.Perturb(),
        },
        initial_distributions={
            'num_layers': schedy.random.Choice(range(1, 10)),
            'activations': schedy.random.Choice(['relu', 'tanh']),
            'kernel_size': schedy.random.Choice([3, 5, 7]),
            'num_filters': schedy.random.Choice([2, 4, 8, 16, 32, 64, 128, 256, 512]),
            'learning_rate': schedy.random.LogUniform(1e-6, 1e-1),
            'dropout_rate': schedy.random.Uniform(0.0, 0.8),
        },
        population_size=20,
    )
    db.add_experiment(experiment)

The first argument (``MNIST with PBT``) is the name of the experiment.

The second argument tells Schedy that we are trying to maximize
(:py:const:`schedy.pbt.MAXIMIZE`) the result specified in the third argument, the
``max_accuracy`` obtained by the network.

The argument called ``exploit`` tells us that we are using the *Truncate* strategy to
exploit results (i.e. if we are working on a job that scored in the bottom 20%,
explore a job from the top 20% instead, see :py:class:`schedy.pbt.Truncate`).

The argument called ``explore`` tells us that we are using the *Perturb*
strategy to explore the learning rate and the dropout rate. This strategy
multiplies the values of these hyperparameters by a random number (see
:py:class:`schedy.pbt.Perturb`).

Remember the exploration modifies the value of your hyperparameters *during
training* so you should only use it when it makes sense. For instance, it is
possible to change the value of the learning rate while training (it does not
change the model in itself), but it is not possible to change the number of
layers (it usually does not make sense to create/remove weights while
training).

*Using* :py:class:`schedy.pbt.Truncate` *as your exploit strategy, and*
:py:class:`schedy.pbt.Perturb` *as your explore strategy is usually a sensible
default.*

The argument called ``initial_distributions`` tells Schedy how to pick values
for the initial jobs, as those are basically created using random search. The
available distributions are the same as :ref:`the ones used for random search
<available_distributions>`. The next argument, ``population_size``, specifies
the number of initial jobs that should be created before starting to
exploit/explore.

*Note: Specifying the population size and the initial distributions is
optional. You can also create the initial jobs by hand, using* ``schedy push``
*in the command line or* :py:meth:`schedy.Experiment.add_job` *.
This allows you to choose the initial value of your hyperparameters by hand,
instead of using random search.*

Creating the worker
-------------------

Creating a worker that will work efficiently with PBT requires a few more steps
than other experiment types (e.g. Random Search).

Let's have a little reminder. When using random search, the basic worker
followed these steps::

    import schedy

    db = schedy.SchedyDB()
    experiment = db.get_experiment('MyExperiment')
    with experiment.next_job() as job:
        model = create_model(job)
        train(model) # Full training until convergence
        job.results = evaluate(model)

When using PBT, you should be doing something along those lines instead:

.. code-block:: python
    :emphasize-lines: 7,8,11,12,13

    import schedy

    db = schedy.SchedyDB()
    experiment = db.get_experiment('MyExperiment')
    with experiment.next_job() as job:
        model = create_model(job)
        if 'model_path' in job.results:
            model.load(job.results['model_path'])
        partial_train(model) # Partial training for a limited amount of time
        job.results = evaluate(model)
        model_save_path = 'dump_dir/' + job.id + '.mdl'
        model.save(model_save_path) 
        job.results['model_path'] = model_save_path

For every job it receives, the worker follows these three simple steps:

- Try to reload the model if it exists
- Train the model a bit more
- Save the model

As you can see, instead of training the model until convergence, you should
only train it for a limited amount of time (e.g. five epochs, 30 minutes...).
You should then save your model to a location that can be accessed by all
workers (here we suppose that all workers have accessed to the ``dump_dir``
directory, and we save the model as ``dump_dir/<job_id>.mdl``). You should also
record the location of your model into the job's results.

The reason for this is that Schedy might choose to ask another worker to resume
the work on your job later, by copying the job's hyperparameters and results to
a new job, and sending it to a new worker. This is why this worker starts by
checking whether there is a result called ``model_path``, and if there is, it
reloads the weights from this location.

Everything else is handled by Schedy. All you need to do is to reload the model
if it exists, to train it a bit more, then to save it.

We provide examples `here
<https://github.com/incalia/schedy-client/tree/master/examples/pbt>`_, and a
more detailed description of the PBT experiments in the API reference,
:ref:`here <pbt_experiment>` and :doc:`here </reference/pbt>`.
