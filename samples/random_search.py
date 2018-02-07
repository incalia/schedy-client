#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

from schedy import SchedyDB, RandomSearch
from schedy.errors import ResourceExistsError
from schedy.random import Choice, LogUniform, Constant, Normal

def train(hyperparameters):
    # Put your training algorithm here
    # For this example, we always return the same results
    time.sleep(5)
    training_error = 0.2
    valid_error = 0.3
    return training_error, valid_error

if __name__ == '__main__':
    db = SchedyDB('integ_tests/client.json')
    exp = RandomSearch(
            'TestExperiment',
            {
                'learning_rate': LogUniform(10, -1, -5),
                'n_layers': Choice([5, 6, 7, 8]),
                'dropout': Constant(0.5),
            },
        )
    try:
        db.add_experiment(exp)
    except ResourceExistsError:
        exp = db.get_experiment(exp.name)
    while True:
        with exp.next_job() as job:
            train_err, val_err = train(job.hyperparameters)
            job.results['training_error'] = train_err
            job.results['valid_error'] = val_err
            # Setting the quality of the run is optional for random search, but
            # it allows you to find the best jobs for this experiment easily
            # later
            job.quality = val_err
            print(job.job_id, job.quality)

