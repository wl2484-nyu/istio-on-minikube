from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry import propagate

from opentelemetry import context, trace
from opentelemetry import metrics

from random import randint
from functools import wraps
from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

import os
import time


MILLI_SEC_FACTOR = 1000
MICRO_SEC_FACTOR = 1000000

SVC_NAME = os.getenv("SVC_NAME", "e2e")
API_PREFIX = os.getenv("API_PREFIX", "app")
API_VERSION = os.getenv("API_VERSION", "v1")


# set B3 headers format
propagate.set_global_textmap(B3MultiFormat())

trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({SERVICE_NAME: SVC_NAME})
    )
)
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    # OTEL_EXPORTER_JAEGER_ENDPOINT=http://jaeger-collector.istio-system.svc:14268/api/traces
    # is a required container environment variable
)

# create a batch processor with Jaeger exporter and set it
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

meter = metrics.get_meter(__name__)

roll_counter = meter.create_counter(
    "roll_counter",
    description="The number of rolls by roll value",
)

app = FastAPI()
sub_app = FastAPI()

API_PREFIX = os.getenv("API_PREFIX", "app")
API_VERSION = os.getenv("API_VERSION", "v1")
app.mount("{}/{}".format(API_PREFIX, API_VERSION), sub_app)
print("URI PREFIX: {}/{}".format(API_PREFIX, API_VERSION))

FastAPIInstrumentor.instrument_app(app)


def add_b3_header(f):
    @wraps(f)
    async def inner(*args, **kwargs):
        request = kwargs.get('request')
        """ [Example]
        request.headers = 
        {
          "host": "svc-1.dtp.org",
          "user-agent": "curl/7.87.0",
          "accept": "*/*",
          "x-forwarded-for": "10.244.0.1",
          "x-forwarded-proto": "http",
          "x-request-id": "022151ab-3a51-9018-9f6d-e63af3b29a8b",
          "x-envoy-attempt-count": "1",
          "x-envoy-internal": "true",
          "x-forwarded-client-cert": "By=spiffe://cluster.local/ns/e2e/sa/default;Hash=ae960b05fdad696034d38c346fc92f6e5a8405b1de4663c38ca05a6dda09caf5;Subject=\"\";URI=spiffe://cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account",
          "x-b3-traceid": "a53f0d4604621cde3840400b055fb50d",
          "x-b3-spanid": "e694b9d15adf6119",
          "x-b3-parentspanid": "3840400b055fb50d",
          "x-b3-sampled": "1"
        }
        """
        ctx = B3MultiFormat().extract(dict(request.headers))
        with tracer.start_as_current_span(f.__name__ + "_summary", context=ctx):
            return await f(*args, **kwargs)
    return inner


def trace_performance_sync(f):
    @wraps(f)
    def inner(*args, **kwargs):
        request = kwargs.get('request')
        with tracer.start_as_current_span(f.__name__ + "_performance_metrics", context=context.get_current()) as span:
            span.set_attribute("service", SVC_NAME)
            span.set_attribute("function", f.__name__)
            start_time = time.monotonic()
            r = f(*args, **kwargs)
            full_duration = time.monotonic() - start_time
            span.set_attribute("exec_ms", full_duration * MILLI_SEC_FACTOR)
            return r
    return inner


def trace_performance_async(f):
    @wraps(f)
    async def inner(*args, **kwargs):
        with tracer.start_as_current_span(f.__name__ + "_performance_metrics", context=context.get_current()) as span:
            span.set_attribute("service", SVC_NAME)
            span.set_attribute("function", f.__name__)
            start_time = time.monotonic()
            r = await f(*args, **kwargs)
            full_duration = time.monotonic() - start_time
            span.set_attribute("exec_ms", full_duration * MILLI_SEC_FACTOR)
            return r
    return inner


def get_cur_time(ms=True):
    if ms:
        return int(time.time() * MILLI_SEC_FACTOR)
    else:
        return int(time.time())


@sub_app.get('/')
@sub_app.get('/home')
async def hello(request: Request):
    return "Let's roll the dice!"


@trace_performance_sync
def roll(count):
    with tracer.start_as_current_span("roll") as span:
        span.set_attribute("start_time", get_cur_time())
        span.set_attribute('roll.count', count)

        rolls = list()
        for i in range(count):
            res = randint(1, 6)
            rolls.append(str(res))
            roll_counter.add(1, {"roll.value": res})

        rolls_str = ', '.join(rolls)
        span.set_attribute("roll.value", rolls_str)
        span.set_attribute("end_time", get_cur_time())
        return rolls_str


@sub_app.get("/rolldice")
@sub_app.get("/rolldice/{count}")
@add_b3_header
@trace_performance_async
async def rolldice(request: Request):
    with tracer.start_as_current_span("rolldice") as span:
        span.set_attribute("start_time", get_cur_time())
        res = None

        try:
            count = int(request.path_params['count']) if 'count' in request.path_params else 1
            magic_rolls = roll(count)

            if count < 1:
                res = "Please specify a positive integer."
            elif count == 1:
                res = "Your magic roll is {}".format(magic_rolls)
            else:
                res = "Your magic rolls are {}".format(magic_rolls)

        except ValueError as e:
            res = "Please specify a valid integer."

        except Exception as e:
            res = "You've got no luck."

        span.set_attribute("end_time", get_cur_time())
        return res
