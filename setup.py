#!/usr/bin/python

from setuptools import setup
import sys


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'register':
    import pypandoc
    long_desc = pypandoc.convert('README.md', 'rst')
else:
    long_desc = ''

setup(
    name='gcat',
    version='0.1.0',
    description='OAuth wrapper and command line utility for interacting with Google Drive spreasheets',
    long_description=long_desc,
    url='http://www.github.com/embr/gcat',
    author='Evan Rosen',
    author_email='evnrsn@gmail.com',
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
    include_package_data = True,
    classifiers=[
        'Topic :: Scientific/Engineering',
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Operating System :: Unix',
        'Operating System :: MacOS :: MacOS X',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        ]
    )

