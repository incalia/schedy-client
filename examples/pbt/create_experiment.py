#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import schedy

if __name__ == '__main__':
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

