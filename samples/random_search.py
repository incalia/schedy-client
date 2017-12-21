#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from schedy import SchedyDB, RandomSearch
from schedy.errors import ResourceExistsError
from schedy.random import Choice, Uniform, Constant

if __name__ == '__main__':
    db = SchedyDB('http://localhost:8080')
    exp = RandomSearch(
            'TestExperiment',
            {
                'learning_rate': Uniform(1, 3),
                'n_layers': Choice([5, 6, 7, 8]),
                'dropout': Constant(0.5),
            }
        )
    try:
        db.add_experiment(exp)
    except ResourceExistsError:
        exp = db.get_experiment(exp.name)
    print(exp)

