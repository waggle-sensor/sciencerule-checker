import os
import logging
import argparse
from urllib import request, parse

import json

def query(args):
    data = json.dumps({
        "rule": args.rule,
    }).encode()
    url = parse.urljoin(args.url, "/evaluate")
    headers = {
        "content-type": "application/json"
    }
    req = request.Request(url, data, headers=headers)
    logging.debug(f'url: {url}')
    logging.debug(f'payload: {data}')
    resp = request.urlopen(req)
    return_code = resp.getcode()
    logging.debug(return_code)
    if return_code == 200:
        body = json.loads(resp.read().strip().decode())
        logging.info(json.dumps(body, indent=4))
        return 0
    else:
        logging.error(resp.read())
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose",
        dest="verbose", action="store_true",
        help="Print debug information")
    parser.add_argument("-r", "--rule",
        dest="rule", type=str,
        required=True,
        help="rule to be evaluated")
    parser.add_argument("-u", "--checker-url",
        dest='url', type=str,
        default=os.getenv("CHECKER_URL", "http://localhost:5000"),
        help="URL to science checker")
    args = parser.parse_args()
    logging.basicConfig(
        format='%(levelname)s %(asctime)s %(message)s',
        level= logging.DEBUG if args.verbose else logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')
    exit(query(args))