#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

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
        'num_layers': schedy.random.Choice(range(1, 6)),
        'activations': schedy.random.Choice(['relu', 'tanh']),
        'kernel_size': schedy.random.Choice([3, 5, 7]),
        'num_filters': schedy.random.Choice([2, 4, 8, 16, 32, 64, 128, 256]),
        'learning_rate': schedy.random.LogUniform(1e-8, 1),
        'dropout_rate': schedy.random.Uniform(0.0, 0.8),
    },
    population_size=20,
)
db.add_experiment(experiment)

