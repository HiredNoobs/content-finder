FROM python:3.10-slim-buster

WORKDIR /app

COPY ./setup.py ./.env /app/
RUN python -m pip install -e .

COPY ./cytubebot ./cytubebot
ADD https://github.com/dwyl/english-words/raw/master/words.txt /app/cytubebot/randomvideo/eng_dict.txt

ENV PYTHONUNBUFFERED=1

CMD ["python", "cytubebot/main.py"]