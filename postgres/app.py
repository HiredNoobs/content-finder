"""Extremely simple API to kill the Postgres container."""

import os
import signal

from flask import Flask

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index() -> None:
    pid = 1
    os.kill(pid, signal.SIGTERM)
    return '', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
