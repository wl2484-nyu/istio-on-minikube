import os
import requests

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from performance_tracer import add_b3_header, trace_performance_async, trace_performance_sync

MILLI_SEC_FACTOR = 1000

NS = os.getenv("NS", "e2e")
SVC_NAME = os.getenv("SVC_NAME", "svcs")
API_PREFIX = os.getenv("API_PREFIX", "/app")
API_VERSION = os.getenv("API_VERSION", "v1")
DOWNSTREAM_SVCS = os.getenv("DOWNSTREAM_SVCS", "svc-c:5566,svc-d:5566").split(",")

URL_TEMPLATE = "http://{}.{}.svc.cluster.local:{}"

app = FastAPI()
sub_app = FastAPI()

app.mount("{}/{}".format(API_PREFIX, API_VERSION), sub_app)
print("URI PREFIX: {}/{}".format(API_PREFIX, API_VERSION))

FastAPIInstrumentor.instrument_app(app)


def propagate_and_get_response(url, headers, timeout=30):
    return requests.get(url=url, headers=headers, timeout=timeout)


@sub_app.get("/b1")
@add_b3_header
@trace_performance_async
async def b1(request: Request):
    chunks = DOWNSTREAM_SVCS[0].split(":")
    url = "{}/c1".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1]))
    res = propagate_and_get_response(url, headers=request.headers)  # carry existing headers to include children spans in the trace
    return "b1 - {}".format(res.json())


@sub_app.get("/b2")
@add_b3_header
@trace_performance_async
async def b2(request: Request):
    chunks = DOWNSTREAM_SVCS[1].split(":")
    url = "{}/d1".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1]))
    res = propagate_and_get_response(url, headers=request.headers)  # carry existing headers to include children spans in the trace
    return "b2 - {}".format(res.json())
