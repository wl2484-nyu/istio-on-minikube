#!/usr/bin/python
import argparse
import json
import sys
import time

import requests
from performance_tracer import STR_SUMMARY, STR_PM, STR_FUNC_NAME, STR_CPU_TIME, STR_EXEC_TIME, STR_PEAK_MEM

_DEBUG = False

STR_DATA = 'data'
STR_TRACEID = 'traceID'
STR_SPANS = 'spans'
STR_SPANID = 'spanID'
STR_REFERENCES = 'references'
STR_PROCESSES = 'processes'
STR_PROCID = 'processID'
STR_SVCNAME = 'serviceName'
STR_OPNAME = 'operationName'
STR_REFTYPE = 'refType'
STR_CHILDOF = 'CHILD_OF'
STR_DURATION = 'duration'
STR_TAGS = 'tags'
STR_KEY = 'key'
STR_VALUE = 'value'

JAEGER_ENDPOINT_TEMPLATE = "{}/jaeger/api/traces?service={}"


def get_traces_from_jaeger(jaeger_endpoint, svc, start_time, end_time, limit=10000):
    jaeger_url = JAEGER_ENDPOINT_TEMPLATE.format(jaeger_endpoint, svc)
    if start_time:
        jaeger_url += "&start={}".format(start_time)
    if end_time:
        jaeger_url += "&end={}".format(end_time)
    if limit:
        jaeger_url += "&limit={}".format(limit)
    print(jaeger_url)
    return requests.get(jaeger_url).json()


def get_traces_from_file(input_path):
    with open(input_path, 'r') as f:
        return json.loads(f.read())


def parse_children_spans(procs, parent_trace_id, parent_span_id, all_spans, indices_to_check):
    children_spans = list()
    next_indices_to_check = list()
    for i in indices_to_check:
        span = all_spans[i]
        # assumed one parent
        assert len(span[STR_REFERENCES]) == 1
        assert span[STR_REFERENCES][0][STR_REFTYPE] == STR_CHILDOF
        span_ref = span[STR_REFERENCES][0]
        if span_ref[STR_TRACEID] != parent_trace_id or span_ref[STR_SPANID] != parent_span_id:
            next_indices_to_check.append(i)
            continue

        if span[STR_OPNAME].startswith('/'):
            continue

        span_info = dict({
            STR_TRACEID: span[STR_TRACEID],
            STR_SPANID: span[STR_SPANID],
            STR_SVCNAME: procs[span[STR_PROCID]][STR_SVCNAME],
            STR_OPNAME: span[STR_OPNAME],
            STR_DURATION: span[STR_DURATION]
        })
        if span[STR_OPNAME].endswith(STR_PM):
            tag_dict = {tag[STR_KEY]: tag[STR_VALUE] for tag in span[STR_TAGS]}
            span_info[STR_FUNC_NAME] = tag_dict[STR_FUNC_NAME]
            span_info[STR_CPU_TIME] = tag_dict[STR_CPU_TIME]
            span_info[STR_EXEC_TIME] = tag_dict[STR_EXEC_TIME]
            span_info[STR_PEAK_MEM] = tag_dict[STR_PEAK_MEM]
        children_spans.append(span_info)

    for child_span in children_spans:
        next_children_spans, next_indices_to_check = parse_children_spans(
            procs, child_span[STR_TRACEID], child_span[STR_SPANID], all_spans, next_indices_to_check)
        child_span[STR_SPANS] = next_children_spans
    return children_spans, next_indices_to_check


def parse_trace_tree(trace):
    trace_tree = dict({STR_TRACEID: trace[STR_TRACEID], STR_SPANS: list()})
    if len(trace[STR_SPANS]) > 0:
        procs = trace[STR_PROCESSES]
        # assume len(references) == 0 always appears at spans[0]
        parent_span_index = 0
        parent_span = trace[STR_SPANS][parent_span_index]
        assert len(parent_span[STR_REFERENCES]) == 0
        parent_span_info = dict({
            STR_TRACEID: parent_span[STR_TRACEID],
            STR_SPANID: parent_span[STR_SPANID],
            STR_SVCNAME: procs[parent_span[STR_PROCID]][STR_SVCNAME],
            STR_OPNAME: parent_span[STR_OPNAME],
            STR_DURATION: parent_span[STR_DURATION]
        })
        children_spans, _ = parse_children_spans(
            procs, parent_span[STR_TRACEID], parent_span[STR_SPANID], trace[STR_SPANS],
            list(range(1, len(trace[STR_SPANS]))))
        parent_span_info[STR_SPANS] = children_spans
        trace_tree[STR_SPANS].append(parent_span_info)
    return trace_tree


def combine_summaries(summaries):
    if len(summaries) == 0:
        return dict()

    key = ":".join(sorted(list(map(lambda s: s[STR_KEY], summaries))))
    duration = sum(list(map(lambda s: s[STR_DURATION], summaries)))
    cpu_time = sum(list(map(lambda s: s[STR_CPU_TIME], summaries)))
    exec_time = sum(list(map(lambda s: s[STR_EXEC_TIME], summaries)))
    peak_mem = sum(list(map(lambda s: s[STR_PEAK_MEM], summaries))) # sum-up peak memory for concurrent calls
    return dict({
        STR_KEY: key,
        STR_DURATION: duration,
        STR_CPU_TIME: cpu_time,
        STR_EXEC_TIME: exec_time,
        STR_PEAK_MEM: peak_mem
    })


def get_summary_paths(spans):
    if len(spans) == 0:
        return list()

    summaries = list()
    for span in spans:
        if span[STR_OPNAME].endswith(STR_SUMMARY):
            summary = dict({
                STR_KEY: "{}:{}".format(span[STR_SVCNAME], span[STR_OPNAME]),
                STR_DURATION: span[STR_DURATION],
                STR_CPU_TIME: 0,
                STR_EXEC_TIME: 0,
                STR_PEAK_MEM: 0
            })
            if len(span[STR_SPANS]) > 0:
                assert span[STR_SPANS][0][STR_OPNAME].endswith(STR_PM)
                pm_info = span[STR_SPANS][0]
                summary[STR_CPU_TIME] = pm_info[STR_CPU_TIME]
                summary[STR_EXEC_TIME] = pm_info[STR_EXEC_TIME]
                summary[STR_PEAK_MEM] = pm_info[STR_PEAK_MEM]
            summaries.append(summary)
    summary = combine_summaries(summaries)

    paths = list()
    for span in spans:
        if span[STR_OPNAME].endswith(STR_SUMMARY):
            continue
        for path in get_summary_paths(span[STR_SPANS]):
            if len(summary) > 0:
                path = [summary] + path
            if len(path) > 0:
                paths.append(path)

    if len(paths) == 0 and len(summary) > 0:
        paths.append([summary])
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--jaeger-endpoint', type=str, help='http://endpoint-ip:port')
    parser.add_argument('--input-path', type=str, help='input trace file')
    parser.add_argument('--svc', type=str, help='target service name')
    parser.add_argument('--start-time', type=str, default=int((time.time() - 3600) * 1000000),
                        help='trace start epoch time in micro sec; default to within an hour')
    parser.add_argument('--end-time', type=str, default=int(time.time() * 1000000),
                        help='trace end epoch time in micro sec; default to now')
    parser.add_argument('--limit', type=int, default=10000, help='trace limit')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    global _DEBUG
    if args.debug:
        _DEBUG = True

    if args.jaeger_endpoint:
        if args.svc:
            traces = get_traces_from_jaeger(args.jaeger_endpoint, args.svc, args.start_time, args.end_time, args.limit)
        else:
            sys.exit('please specify --svc')
    elif args.input_path:
        traces = get_traces_from_file(args.input_path)
    else:
        sys.exit('please specify --jaeger-endpoint or --input')

    trace_count = len(traces[STR_DATA])
    for trace in traces[STR_DATA]:
        trace_tree = parse_trace_tree(trace)
        paths = get_summary_paths(trace_tree[STR_SPANS])    # assumed 1st-level of the trace_tree is not a summary
        for path in paths:
            print(path)


if __name__ == '__main__':
    main()
