import os
import requests
from concurrent import futures

from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from performance_tracer import add_b3_header, trace_performance_async, trace_performance_sync

MILLI_SEC_FACTOR = 1000

NS = os.getenv("NS", "e2e")
SVC_NAME = os.getenv("SVC_NAME", "svcs")
API_PREFIX = os.getenv("API_PREFIX", "/app")
API_VERSION = os.getenv("API_VERSION", "v1")
DOWNSTREAM_SVCS = os.getenv("DOWNSTREAM_SVCS", "svc-b:5566,svc-e:5566,svc-g:5566").split(",")

URL_TEMPLATE = "http://{}.{}.svc.cluster.local:{}"
# URL_TEMPLATE = "http://0.0.0.0/{}"

app = FastAPI()
sub_app = FastAPI()

app.mount("{}/{}".format(API_PREFIX, API_VERSION), sub_app)
print("URI PREFIX: {}/{}".format(API_PREFIX, API_VERSION))

FastAPIInstrumentor.instrument_app(app)


def propagate_and_get_response(url, headers, timeout=30):
    return requests.get(url=url, headers=headers, timeout=timeout)


@sub_app.get("/a1")
@add_b3_header
@trace_performance_async
async def a1(request: Request):
    chunks = DOWNSTREAM_SVCS[0].split(":")
    url = "{}/b1".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1]))
    res = propagate_and_get_response(url, headers=request.headers)  # carry existing headers to include children spans in the trace
    # print("{}/b1".format(URL_TEMPLATE.format(chunks[1])))
    # res = requests.get("{}/b1".format(URL_TEMPLATE.format(chunks[1])),
    #                    headers={"Host": "app-b.dtp.org"}, timeout=TIMEOUT_SEC)
    return "a1 - {}".format(res.json())


@sub_app.get("/a2")
@add_b3_header
@trace_performance_async
async def a2(request: Request):
    chunks = DOWNSTREAM_SVCS[0].split(":")
    url = "{}/b2".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1]))
    res = propagate_and_get_response(url, headers=request.headers)  # carry existing headers to include children spans in the trace
    # print("{}/b1".format(URL_TEMPLATE.format(chunks[1])))
    # res = requests.get("{}/b1".format(URL_TEMPLATE.format(chunks[1])),
    #                    headers={"Host": "app-b.dtp.org"}, timeout=TIMEOUT_SEC)
    return "a2 - {}".format(res.json())


@sub_app.get("/a3")
@add_b3_header
@trace_performance_async
async def a3(request: Request): # concurrent calls
    urls = list()

    chunks = DOWNSTREAM_SVCS[1].split(":")
    urls.append("{}/e1".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1])))

    chunks = DOWNSTREAM_SVCS[2].split(":")
    urls.append("{}/g1".format(URL_TEMPLATE.format(chunks[0], NS, chunks[1])))

    args = [(url, request.headers) for url in urls]
    with futures.ThreadPoolExecutor() as executor:
        # ress = executor.map(propagate_and_get_response, *args)
        # for res in ress:
        #     print(res)
        fts = []
        for url in urls:
            fts.append(executor.submit(propagate_and_get_response, url, request.headers))
        return "a3 - {}".format(", ".join([future.result().json() for future in futures.as_completed(fts)]))
