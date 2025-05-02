<<<<<<< HEAD
FROM python:3.9-slim-buster
=======
FROM python:3.10-slim-buster
>>>>>>> 80cf8075065cdab6ce3579d3b86cce2a8ba4f0f1

WORKDIR /app

COPY ./requirements.txt .
COPY ./setup.py .

<<<<<<< HEAD
RUN python -m pip install -r requirements.txt

COPY ./main.py .

COPY ./.env .

=======
RUN python -m pip install -e .

COPY ./cytubebot ./cytubebot

COPY ./.env .

>>>>>>> 80cf8075065cdab6ce3579d3b86cce2a8ba4f0f1
ENV PYTHONUNBUFFERED=1

CMD ["python", "cytubebot/main.py"]