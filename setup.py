from setuptools import setup, find_packages


setup(
    name='cytube-bot',
    version='1.1.0',
    packages=find_packages('cytubebot'),
    install_requires=[
        'python-dotenv~=0.19.0',
        'beautifulsoup4~=4.10.0',
        'lxml==4.6.3',
        'python-engineio==3.14.2',
        'python-socketio[client]==4.6.1',
        'requests~=2.26.0',
    ],
    setup_requires=['flake8']
)
