#!/usr/bin/python

from setuptools import setup

setup(
    name='gcat',
    version='0.1.0',
    description='Command-line interface for Google Drive',
    url='http://www.github.com/embr/gcat',
    author='Evan Rosen',
    author_email='erosen@wikimedia.org',
    entry_points = {
        'console_scripts': [
            'gcat = gcat:main',
            ]
        },
    install_requires=[
       "oauth2client >= 1.0",
       "google-api-python-client >= 1.0",
       "httplib2 >= 0.7.6",
       "pandas >= 0.9.0"
       ],
    include_package_data = True
    )

