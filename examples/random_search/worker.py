#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import schedy
import time

db = schedy.Client()
experiment = db.get_experiment('MinimizeRandom')
for i in range(20):
    try:
        # Pull the next job, and start working on it
        # The with statement is there so that we always report to Schedy
        # whether the job has crashed or succeeded
        # The results will only be pushed to Schedy at the end of the with
        # statement
        with experiment.next_job() as job:
            x = job.hyperparameters['x']
            y = job.hyperparameters['y']
            result = x ** 2 + y ** 2
            job.results['result'] = result
    # Catch any type of exception so that the worker never crashes
    # This includes the NoJobError exception thrown by Schedy if there is no
    # job queued for this experiment.
    except Exception as e:
        print(e)
        # Wait a minute before issuing the next request
        time.sleep(60)


