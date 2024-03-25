FROM python:3.8.18-slim

WORKDIR /code

RUN pip install pipenv

COPY Pipfile.lock Pipfile.lock

RUN pipenv sync

CMD tail -f /dev/null
