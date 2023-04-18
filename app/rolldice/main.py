from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry import propagate

from opentelemetry import trace
from opentelemetry import metrics

from random import randint
from functools import wraps
from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

import os
import time
import uuid


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


def add_b3_header(name):
    def wrapper(f):
        @wraps(f)
        async def inner(*args, **kwargs):
            request = kwargs.get('request')
            ctx = B3MultiFormat().extract(dict(request.headers))
            with tracer.start_as_current_span(name, context=ctx):
                return await f(*args, **kwargs)
        return inner
    return wrapper


def get_cur_time(ms=True):
    if ms:
        return int(time.time() * 1000)
    else:
        return int(time.time())


@sub_app.get('/')
@sub_app.get('/home')
async def hello(request: Request):
    return "Let's roll the dice!"


def roll(count):
    with tracer.start_as_current_span("roll") as span:
        span.set_attribute("time", get_cur_time())
        span.set_attribute('level', 1)
        span.set_attribute('roll.count', count)

        rolls = list()
        for i in range(count):
            res = randint(1, 6)
            rolls.append(str(res))
            roll_counter.add(1, {"roll.value": res})

        rolls_str = ', '.join(rolls)
        span.set_attribute("roll.value", rolls_str)
        return rolls_str


@sub_app.get("/rolldice")
@sub_app.get("/rolldice/{count}")
@add_b3_header("rolldice")
async def rolldice(request: Request):
    span = trace.get_current_span()
    span.set_attribute("uuid", str(uuid.uuid4()))
    span.set_attribute("time", get_cur_time())
    span.set_attribute("level", 0)

    try:
        count = int(request.path_params['count']) if 'count' in request.path_params else 1
        magic_rolls = roll(count)

        if count < 1:
            return "Please specify a positive integer."
        elif count == 1:
            return "Your magic roll is {}".format(magic_rolls)
        else:
            return "Your magic rolls are {}".format(magic_rolls)

    except ValueError as e:
        return "Please specify a valid integer."

    except Exception as e:
        return "You've got no luck."
