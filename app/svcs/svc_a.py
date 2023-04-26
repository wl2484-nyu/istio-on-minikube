import os
import requests
from random import randint

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from performance_tracer import add_b3_header, trace_performance_async, trace_performance_sync

MILLI_SEC_FACTOR = 1000
TIMEOUT_SEC = 30

NS = os.getenv("NS", "e2e")
SVC_NAME = os.getenv("SVC_NAME", "svcs")
API_PREFIX = os.getenv("API_PREFIX", "/app")
API_VERSION = os.getenv("API_VERSION", "v1")
DOWNSTREAM_SVCS = os.getenv("DOWNSTREAM_SVCS", "svc-b").split(",")

URL_TEMPLATE = "http://{}.{}.svc.cluster.local:{}"
# URL_TEMPLATE = "http://0.0.0.0/{}"

app = FastAPI()
sub_app = FastAPI()

app.mount("{}/{}".format(API_PREFIX, API_VERSION), sub_app)
print("URI PREFIX: {}/{}".format(API_PREFIX, API_VERSION))

FastAPIInstrumentor.instrument_app(app)


@sub_app.get("/a1")
@add_b3_header
@trace_performance_async
async def a1(request: Request):
    chunks = DOWNSTREAM_SVCS[0].split(":")
    print("{}/b1".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1])))
    res = requests.get("{}/b1".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1])), timeout=TIMEOUT_SEC,
                       headers=request.headers) # carry existing headers to include children spans in the trace
    # print("{}/b1".format(URL_TEMPLATE.format(chunks[1])))
    # res = requests.get("{}/b1".format(URL_TEMPLATE.format(chunks[1])),
    #                    headers={"Host": "app-b.dtp.org"}, timeout=TIMEOUT_SEC)
    return "a1 - {}".format(res.json())


@sub_app.get("/a2")
@add_b3_header
@trace_performance_async
async def a2(request: Request):
    return "a2: {}".format(randint(0, 10000))
