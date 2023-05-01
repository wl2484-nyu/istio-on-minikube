import os
import time
from random import randint, seed

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from performance_tracer import add_b3_header, trace_performance_async

MILLI_SEC_FACTOR = 1000

SVC_NAME = os.getenv("SVC_NAME", "svcs")
API_PREFIX = os.getenv("API_PREFIX", "/app")
API_VERSION = os.getenv("API_VERSION", "v1")

app = FastAPI()
sub_app = FastAPI()

app.mount("{}/{}".format(API_PREFIX, API_VERSION), sub_app)
print("URI PREFIX: {}/{}".format(API_PREFIX, API_VERSION))

FastAPIInstrumentor.instrument_app(app)


@sub_app.get("/c1")
@add_b3_header
@trace_performance_async
async def c1(request: Request):
    t = time.time()
    seed(t % 1 * 1000)
    n = randint(1, 1000)
    return "c1={}".format(n)


@sub_app.get("/c2")
@add_b3_header
@trace_performance_async
async def c2(request: Request):
    t = time.time()
    seed(t % 1 * 1000)
    n = randint(1, 1000)
    return "c2={}".format(n)
