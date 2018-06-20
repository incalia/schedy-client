#!/usr/bin/env python

from setuptools import setup

setup(
    name='Schedy',
    version='0.1.0b6',
    description='Python client for Schedy',
    long_description=open('README.rst').read(),
    author='Incalia',
    author_email='nathan@incalia.fr',
    url='https://schedy.io/',
    install_requires=[
        'requests>=2.18.4',
        'tabulate>=0.8.2',
        'six>=1.11.0',
    ],
    packages=['schedy'],
    entry_points={
        'console_scripts': [
            'schedy = schedy.cmd:main',
        ],
    },
    license='MIT',
    # TODO: Add license to classifiers
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Development Status :: 4 - Beta',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    project_urls={
        'Homepage': 'https://schedy.io/',
        'Source': 'https://github.com/incalia/schedy-client/',
        'Documentation': 'https://schedy.readthedocs.io/en/latest/',
    },
)

