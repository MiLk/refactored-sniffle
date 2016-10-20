#!/usr/bin/env python

from __future__ import print_function

import os
import json

import numpy as np
import six

from elasticsearch import Elasticsearch, helpers


def fetch_data():
    client = Elasticsearch()
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"ident.raw": "rails"}},
                    {"wildcard": {"host.raw": "ci*"}},
                    {"match": {"message": "duration"}},
                    {"range": {"@timestamp": {"gte": "2016-10-19T00:00:00"}}}
                ]
            }
        }
    }
    return helpers.scan(client, query=query, index="logstash-*", size=50)


def analyze_data(data):
    docs = dict()
    i = 0
    for doc in data:
        message = dict()
        doc_id = doc['_id']
        for field in doc['_source']['message'].split(' '):
            try:
                k, v = field.split('=', 1)
                if k == 'params':
                    break
                message[k] = v
            except ValueError:
                pass
        analyzed = {
            '_id': doc_id,
            'message': message,
            '_timestamp': doc['_source']['@timestamp'],
            '_host': doc['_source']['host']
        }
        docs[doc_id] = analyzed

        i += 1
        if i % 1000:
            print('%d documents processed' % i)

    return docs


def create_routes_data(docs):
    routes = dict()
    for doc_id, doc in six.iteritems(docs):
        path = doc['message']['path']
        if path not in routes:
            routes[path] = [doc_id]
        else:
            routes[path].append(doc_id)

    routes_stats = []
    for name in routes.keys():
        durations = [float(docs[doc_id]['message']['duration'])
                     for doc_id in routes[name]]
        total = len(durations)
        avg = np.average(durations)
        p99 = np.percentile(durations, 99)
        p90 = np.percentile(durations, 90)
        histo = np.histogram(durations, bins=[
            0,
            500,
            1000,
            2000,
            5000,
            10000,
            15000,
            20000,
            25000,
            30000
        ])
        routes_stats.append({
            'name': name,
            'avg': avg,
            'p90': p90,
            'p99': p99,
            'total': total,
            'histo': histo
        })

    return routes, routes_stats


def main():
    if os.path.exists('data.json'):
        with open('data.json') as data_file:
            docs = json.load(data_file)
    else:
        raw = fetch_data()
        docs = analyze_data(raw)
        with open('data.json', 'w') as outfile:
            json.dump(docs, outfile)

    routes, routes_stats = create_routes_data(docs)
    sorted_routes = sorted(routes_stats, key=lambda x: x['avg'], reverse=True)
    print('25 slowest endpoints:')
    for route in sorted_routes[:25]:
        print('Endpoint %s - avg: %s ms - '
              '99th percentile: %s - 90th percentile: %s - '
              'hits: %s - histo: %s' % (route['name'], route['avg'],
                                        route['p99'], route['p90'],
                                        route['total'], route['histo']))

    ranking = sorted(docs.values(),
                     key=lambda x: float(x['message']['duration']),
                     reverse=True)
    print('\n\n25 longest responses:')
    for doc in ranking[:25]:
        print('duration: %s - doc: %s'
              % (doc['message']['duration'], json.dumps(doc)))

    print('\n\n25 endpoints which had the longest responses:')
    seen = set()
    i = 0
    for doc in ranking:
        path = doc['message']['path']
        if path in seen:
            continue
        seen.add(path)
        print('path: %s - duration: %s - doc: %s'
              % (path, doc['message']['duration'], json.dumps(doc)))
        i += 1
        if i == 25:
            break


if __name__ == "__main__":
    main()
