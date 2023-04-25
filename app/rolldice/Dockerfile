# syntax=docker/dockerfile:1.4
#FROM python:3.11.2-alpine3.16 AS builder
FROM python:3.10

ARG DEFAULT_MODULE_NAME=main
ARG DEFAULT_APP_NAME=app
ARG DEFAULT_PORT=5566
ENV MODULE=$DEFAULT_MODULE_NAME
ENV APP=$DEFAULT_APP_NAME
ENV PORT=$DEFAULT_PORT

COPY . /app/
WORKDIR /app

RUN pip3 install -r requirements.txt

EXPOSE $PORT
CMD opentelemetry-instrument uvicorn "$MODULE:$APP" --host "0.0.0.0" --port $PORT
