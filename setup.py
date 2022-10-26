from importlib.metadata import entry_points
from setuptools import setup, find_packages


setup(
    name='cytubebot',
    version='1.1.0',
    packages=['cytubebot'] + ['cytubebot.' + pkg for pkg in find_packages('cytubebot')],
    install_requires=[
        'beautifulsoup4~=4.10.0',
        'lxml==4.6.3',
        'python-engineio==3.14.2',
        'python-socketio[client]==4.6.1',
        'requests~=2.26.0',
    ]
)
