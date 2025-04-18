FROM postgres:17.4-alpine

# Supervisord setup
RUN apk --update --no-cache upgrade \
    && apk add --no-cache supervisor logrotate py3-pip

COPY ./supervisord.conf /etc/supervisord.conf

# Cron setup
COPY ./backup-cronjob /etc/crontabs/root

# Logrotate
COPY ./backup-rotate /etc/logrotate.d

# Postgres config
COPY ./init/ /docker-entrypoint-initdb.d/

# Python Flask API setup
COPY ./app.py ./requirements.txt ./run_app.sh /app/

RUN chmod +x /app/run_app.sh

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
