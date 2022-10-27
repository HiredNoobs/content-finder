from setuptools import setup, find_packages


setup(
    name='cytubebot',
    version='1.1.0',
    packages=['cytubebot'] + ['cytubebot.' + pkg for pkg in find_packages('cytubebot')],
    install_requires=[
        'beautifulsoup4==4.11.1',
        'lxml==4.9.1',
        'python-engineio==3.14.2',
        'python-socketio[client]==4.6.1',
        'requests==2.28.1',
        'psycopg[binary,pool]==3.1.4',
    ],
)
