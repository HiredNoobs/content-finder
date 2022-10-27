# Postgres

This directory contains the Database container (currently a postgres DB) and a number of supporting tools:
1. Supervisord to manage all the running services and be Docker's main entrypoint for the container.
2. A cronjob to occassionally backup the DB, this should be adjusted to match how often the content-finder is actually running (i.e. don't set daily backups if you're running for five minutes.)
3. Logrotate to manage the backups, again configure to match your setup.
4. Python Flask API to shutdown the container along with the main bot container when a user issues the !kill command. The 5000 flask port is not exposed by default and I would not recommend exposing the port unless you have a specific reason to do so.