#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='maketrackhubs',
    version='1.0.0',
    url='github.com/YeoLab/maketrackhubs',
    license='',
    author='gpratt, adomissy, byee4',
    author_email='bay001@ucsd.edu',
    description='Creates and attempts to upload trackhub files to yeolab aws',
    packages=['maketrackhubs'],
    package_dir={
        'maketrackhubs': 'maketrackhubs',
    },
    entry_points = {
        'console_scripts': [
            'maketrackhubs = maketrackhubs.make_trackhubs:main',
        ]
    }
)
