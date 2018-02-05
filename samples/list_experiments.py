#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from schedy import SchedyDB

import logging
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    db = SchedyDB()
    for exp in db.get_experiments():
        print(exp)
        for job in exp.all_jobs():
            print(job)

