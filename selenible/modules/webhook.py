import json
import yaml
import requests

webhook_schema = yaml.load("""
type: object
properties:
  url: {type: string}
  query: {type: object}
  body: {type: object}
  method: {type: string}
  cookies: {type: object}
  headers: {type: object}
required: [url, body]
""")


def Base_webhook(self, params):
    """
    - name: notify webhook
      webhook:
        url: https://host/path
        query:
          id: "xyz"
        body:
          text: "hello, world"
    """
    url = params.get("url")
    query = params.get("query", {})
    body = params.get("body", {})
    method = params.get("method", "post")
    cookies = params.get("cookies", {})
    headers = params.get("headers", {"content-type": "application/json"})
    timeout = params.get("timeout", None)
    sess = requests.Session()
    for name, value in cookies.items():
        sess.cookies.set(name, value)
    resp = sess.request(method, url, params=query, headers=headers, timeout=timeout,
                        data=json.dumps(body, ensure_ascii=False))
    return resp.json()
