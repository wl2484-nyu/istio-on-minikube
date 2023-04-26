import os
from random import randint

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from performance_tracer import add_b3_header, trace_performance_async, trace_performance_sync

MILLI_SEC_FACTOR = 1000

SVC_NAME = os.getenv("SVC_NAME", "svcs")
API_PREFIX = os.getenv("API_PREFIX", "/app")
API_VERSION = os.getenv("API_VERSION", "v1")

app = FastAPI()
sub_app = FastAPI()

app.mount("{}/{}".format(API_PREFIX, API_VERSION), sub_app)
print("URI PREFIX: {}/{}".format(API_PREFIX, API_VERSION))

FastAPIInstrumentor.instrument_app(app)


@sub_app.get("/b1")
@add_b3_header
@trace_performance_async
async def b1(request: Request):
    return "b1"


@sub_app.get("/b2")
@add_b3_header
@trace_performance_async
async def b2(request: Request):
    return "b2: {}".format(randint(0, 10000))
