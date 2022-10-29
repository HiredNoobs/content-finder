import atexit
import os
import signal
import subprocess

from flask import Flask, jsonify
from psycopg_pool import ConnectionPool


app = Flask(__name__)

conn_info = (
    'postgres://'
    f'{os.getenv("POSTGRES_USER")}:{os.getenv("POSTGRES_PASSWORD")}'
    '@postgres.content-finder:5432/content?connect_timeout=30'
)
pool = ConnectionPool(conn_info)
atexit.register(pool.close)


@app.route('/shutdown', methods=['GET'])
def shutdown() -> None:
    with open('/backups/database-shutdown.sql', 'w') as sql_file:
        subprocess.run(['pg_dumpall'], stdout=sql_file)

    pool.close()

    pid = 1
    os.kill(pid, signal.SIGTERM)
    return '', 200


@app.route('/', methods=['GET'])
def index() -> None:
    result = None
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM content')
            result = cur.fetchall()
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
