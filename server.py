from os import getenv
import re

import numpy as np

import redis
from flask import Flask, request
from checker import Checker, InfluxDataBackbone

from prometheus_client import start_http_server, Histogram

REQUEST_TIME = Histogram('request_processing_seconds', 'Time spent processing request')

app = Flask(__name__)
port = getenv("SERVER_PORT", 5000)

c = Checker(InfluxDataBackbone(
    getenv("NODE_INFLUXDB_URL", "http://wes-node-influxdb:8086"),
    getenv("NODE_INFLUXDB_QUERY_TOKEN", "")
))


def generate_result(rule, success, message):
    return {
        "response": "success" if success else "failed",
        "rule": rule,
        "result" if success else "error": message,
    }

@app.route("/listrules", methods=["GET"])
def listrules():
    return {
        "response": "success",
        "rules": c.get_supported_funcs().keys()
    }


@app.route("/evaluate", methods=["POST"])
@REQUEST_TIME.time()
def evaluate():
    if request.content_type == None or not request.content_type.startswith("application/json"):
        return generate_result("", False, "content_type must be application/json")
    j = request.json
    rule = j.get("rule", "")
    if rule == "":
        return generate_result(rule, False, "no rule is given")
    ret, result = c.evaluate(rule)
    return generate_result(rule, ret, result)
        

if __name__ == "__main__":
    start_http_server(8000)
    app.run(host='0.0.0.0', port=port)