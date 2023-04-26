import numpy as np
import os
import time
from random import randint

from fastapi import FastAPI, Request
from opentelemetry import metrics, trace, propagate
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from performance_tracer import add_b3_header, trace_performance_async, trace_performance_sync

MILLI_SEC_FACTOR = 1000

SVC_NAME = os.getenv("SVC_NAME", "toy")
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

        arr = np.ones(1024, dtype=int)
        span.set_attribute("toy_sum", int(arr.sum()))

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

            arr = np.ones(256, dtype=int)
            for i in range(arr.shape[0]):
                arr[i] += 1

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
