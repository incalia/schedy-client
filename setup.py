#!/usr/bin/env python

from setuptools import setup

setup(
    name='Schedy',
    version='0.1.0a1',
    description='Python client for Schedy',
    author='Incalia',
    author_email='nathan@incalia.fr',
    url='https://schedy.io/',
    install_requires=[
        'requests>=2.18.4',
        'tabulate>=0.8.2',
    ],
    packages=['schedy'],
    entry_points={
        'console_scripts': [
            'schedy = schedy.cmd:main',
        ],
    },
    # TODO: Add license to classifiers
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Development Status :: 3 - Alpha',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)


