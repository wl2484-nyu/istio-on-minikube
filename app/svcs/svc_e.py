import os
import time
from random import randint, seed

import requests
from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from performance_tracer import add_b3_header, trace_performance_async

MILLI_SEC_FACTOR = 1000
TIMEOUT_SEC = 30

NS = os.getenv("NS", "e2e")
SVC_NAME = os.getenv("SVC_NAME", "svcs")
API_PREFIX = os.getenv("API_PREFIX", "/app")
API_VERSION = os.getenv("API_VERSION", "v1")
DOWNSTREAM_SVCS = os.getenv("DOWNSTREAM_SVCS", "svc-f:5566/f/v1,svc-d:5566/d/v1").split(",")

URL_TEMPLATE = "http://{}.{}.svc.cluster.local:{}"

app = FastAPI()
sub_app = FastAPI()

app.mount("{}/{}".format(API_PREFIX, API_VERSION), sub_app)
print("URI PREFIX: {}/{}".format(API_PREFIX, API_VERSION))

FastAPIInstrumentor.instrument_app(app)


def propagate_and_get_response(url, headers, timeout=30):
    return requests.get(url=url, headers=headers, timeout=timeout)


@sub_app.get("/e1")
@add_b3_header
@trace_performance_async
async def e1(request: Request):  # sequential calls
    t = time.time()
    seed(t % 1 * 1000)
    n = randint(1, 1000)

    chunks = DOWNSTREAM_SVCS[0].split(":")
    url_f1 = "{}/f1".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1]))
    res_f1 = propagate_and_get_response(url_f1,
                                        headers=request.headers)  # carry existing headers to include children spans in the trace

    # sleep_time = round(random(), 3)
    sleep_time = 0.2
    print("sleep {} sec".format(sleep_time))
    time.sleep(sleep_time)

    chunks = DOWNSTREAM_SVCS[1].split(":")
    url_d2 = "{}/d2".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1]))
    res_d2 = propagate_and_get_response(url_d2,
                                        headers=request.headers)  # carry existing headers to include children spans in the trace

    return "e1={} : {}, {}".format(n, res_f1.json(), res_d2.json())


@sub_app.get("/e1n")
@add_b3_header
async def e1n(request: Request):  # sequential calls
    t = time.time()
    seed(t % 1 * 1000)
    n = randint(1, 1000)

    chunks = DOWNSTREAM_SVCS[0].split(":")
    url_f1 = "{}/f1n".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1]))
    res_f1 = propagate_and_get_response(url_f1,
                                        headers=request.headers)  # carry existing headers to include children spans in the trace

    # sleep_time = round(random(), 3)
    sleep_time = 0.2
    print("sleep {} sec".format(sleep_time))
    time.sleep(sleep_time)

    chunks = DOWNSTREAM_SVCS[1].split(":")
    url_d2 = "{}/d2n".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1]))
    res_d2 = propagate_and_get_response(url_d2,
                                        headers=request.headers)  # carry existing headers to include children spans in the trace

    return "e1n={} : {}, {}".format(n, res_f1.json(), res_d2.json())


@sub_app.get("/e2")
@add_b3_header
@trace_performance_async
async def e2(request: Request):
    t = time.time()
    seed(t % 1 * 1000)
    n = randint(1, 1000)
    return "e2={}".format(n)


@sub_app.get("/e2n")
@add_b3_header
async def e2n(request: Request):
    t = time.time()
    seed(t % 1 * 1000)
    n = randint(1, 1000)
    return "e2n={}".format(n)
