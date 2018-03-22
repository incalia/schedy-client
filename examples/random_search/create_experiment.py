#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import schedy

db = schedy.SchedyDB()
distributions = {
    'x': schedy.random.Normal(0, 5),
    'y': schedy.random.Normal(0, 2),
}
experiment = schedy.RandomSearch('MinimizeRandom', distributions)
db.add_experiment(experiment)

