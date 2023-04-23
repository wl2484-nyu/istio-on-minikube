import os
import time
from functools import wraps

from opentelemetry import context, trace, propagate
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

MILLI_SEC_FACTOR = 1000
MICRO_SEC_FACTOR = 1000000

SVC_NAME = os.getenv("SVC_NAME", "e2e")

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
            span.set_attribute("function.name", f.__name__)
            start_exec_time = time.monotonic()
            start_cpu_time = time.process_time()
            r = f(*args, **kwargs)
            cpu_time = time.process_time() - start_cpu_time
            exec_time = time.monotonic() - start_exec_time
            span.set_attribute("cpu.ms", cpu_time * MILLI_SEC_FACTOR)
            span.set_attribute("exec.ms", exec_time * MILLI_SEC_FACTOR)
            return r

    return inner


def trace_performance_async(f):
    @wraps(f)
    async def inner(*args, **kwargs):
        with tracer.start_as_current_span(f.__name__ + "_performance_metrics", context=context.get_current()) as span:
            span.set_attribute("function.name", f.__name__)
            start_exec_time = time.monotonic()
            start_cpu_time = time.process_time()
            r = await f(*args, **kwargs)
            cpu_time = time.process_time() - start_cpu_time
            exec_time = time.monotonic() - start_exec_time
            span.set_attribute("cpu.ms", cpu_time * MILLI_SEC_FACTOR)
            span.set_attribute("exec.ms", exec_time * MILLI_SEC_FACTOR)
            return r

    return inner
