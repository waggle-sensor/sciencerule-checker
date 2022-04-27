from os import getenv
import re

import numpy as np

import redis
from flask import Flask, request

app = Flask(__name__)


@app.route("/evaluate", methods=["POST"])
def evaluate():
    if request.content_type == None or not request.content_type.startswith("application/json"):
        return {
            "error": "content_type must be application/json"
        }
    j = request.json
    rule = j.get("rule", "")
    if rule == "":
        return {
            "error": "no rule is given"
        }
    with redis.Redis(host=getenv("REDIS_HOST", "localhost"), port=getenv("REDIS_PORT", 6379), decode_responses=True) as r:
        def avg(vs):
            return np.mean(vs)
        # !!! main function of interest compact notation for selecting measurements
        def v(name, **meta):
            value = r.get(name)
            if value == None:
                raise Exception(f'{name} does not exist')
            if re.match(r"[-+]?\d*\.\d+|[-+]?\d+", value):
                return float(value)
            else:
                return value
            # return np.array([m["value"] for m in measurements if m["name"] == name and matchmeta(meta, m["meta"])])

        def matchmeta(pattern, meta):
            return all(k in meta and meta[k] == v for k, v in pattern.items())

        try:
            return {
                "response": "success",
                "rule": rule,
                "result": eval(rule, None, locals())
            }
        except Exception as ex:
            return {
                "response": "failed",
                "rule": rule,
                "error": str(ex)
            }
        

if __name__ == "__main__":
    app.run()