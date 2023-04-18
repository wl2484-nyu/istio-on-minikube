# syntax=docker/dockerfile:1.4
#FROM python:3.11.2-alpine3.16 AS builder
FROM python:3.10

COPY . /app/
WORKDIR /app

RUN pip3 install -r requirements.txt

EXPOSE 5566
CMD ["opentelemetry-instrument", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5566"]
