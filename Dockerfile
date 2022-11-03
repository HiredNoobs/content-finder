ARG python=python:3.11-slim-bullseye

#################################################
######## Setup + run tests
#################################################
FROM ${python} as test-stage

WORKDIR /app

COPY ./setup.py ./setup.cfg ./tox.ini ./requirements.txt /app/

RUN python -m pip install -r requirements.txt \
    && python -m pip install tox

# Copy scripts - copying in this early is necessary but Docker will rebuild a lot of layers.
COPY ./cytubebot ./cytubebot
COPY ./tests ./tests

RUN tox

#################################################
######## Setup venv and install application
#################################################
FROM ${python} as build-stage

WORKDIR /app

COPY --from=test-stage /app/cytubebot/ /app/cytubebot/
COPY --from=test-stage /app/setup.py /app/setup.cfg /app/

RUN apt-get update \
    && apt-get install --no-install-recommends -yy \
    && python -m pip install --upgrade pip \
    && python -m pip install virtualenv \
    && python -m venv venv

ENV PATH="/app/venv/bin:$PATH"

RUN python -m pip install --upgrade pip \
    && python -m pip install .

#################################################
######## Production container
#################################################

FROM ${python} as prod-stage

ENV PATH="/app/venv/bin:$PATH"

# Copy scripts across from builder
COPY --from=build-stage /app/venv/ /app/venv/

# Download english dictionary
ADD https://github.com/dwyl/english-words/raw/master/words.txt /app/cytubebot/randomvideo/eng_dict.txt

CMD ["python", "-m", "cytubebot"]