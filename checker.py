from flask import Flask, request

app = Flask(__name__)

in_memory_db = {}

@app.route("/store", methods=["POST"])
def store():
    global in_memory_db
    if request.content_type == None or not request.content_type.startswith("application/json"):
        return {
            "error": "content_type must be application/json"
        }
    j = request.json
    k =j.get("key", "")
    v = j.get("value", "")
    if all([k, v]):
        in_memory_db[k] = v
        return {
            "response": "success",
            "result": f'key {k} with value {v} is added'
        }
    else:
        return {
            "error": "must have key and value"
        }


@app.route("/evaluate", methods=["POST"])
def evaluate():
    global in_memory_db
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
    return {
        "response": "success",
        "rule": rule,
        "result": eval(rule, in_memory_db)
    }

if __name__ == "__main__":
    app.run()