FROM postgres:15-alpine

# Supervisord setup
RUN apk --update --no-cache upgrade \
    && apk add --no-cache supervisor logrotate

COPY ./supervisord.conf /etc/supervisord.conf

# Cron setup
COPY ./backup-cronjob /etc/crontabs/root

# Logrotate
COPY ./backup-rotate /etc/logrotate.d

# Postgres config
COPY ./init/ /docker-entrypoint-initdb.d/

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]