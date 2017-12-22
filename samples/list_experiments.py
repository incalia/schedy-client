#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from schedy import SchedyDB

if __name__ == '__main__':
    db = SchedyDB('http://localhost:8080')
    for exp in db.get_experiments():
        print(exp)

