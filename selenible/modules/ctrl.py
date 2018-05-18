import time
import json
import yaml
import toml
import tempfile
import urllib.parse
import requests
from subprocess import DEVNULL
from lxml import etree
import logging.config


progn_schema = yaml.load("""
type: array
items: {type: object}
""")


def Base_progn(self, param):
    """
    - name: subroutine
      progn:
      - name: debug1
        echo: hello world
      - name: debug2
        echo: good-bye world
    """
    self.lock.release()
    self.run(param)
    self.lock.acquire()


var_schema = {"type": "object"}


def Base_var(self, param):
    """
    - name: set variables
      var:
        key1: value1
        key2:
         - value2.1
         - value2.2
    """
    self.variables.update(param)


var_if_not_schema = var_schema


def Base_var_if_not(self, param):
    """
    - name: set variables
      var_if_not:
        key1: value1
        key2:
         - value2.1
         - value2.2
    """
    for k, v in param.items():
        if k not in self.variables:
            self.variables[k] = v


var_from_schema = yaml.load("""
type: object
properties:
  yaml: {type: string}
  json: {type: string}
  toml: {type: string}
""")


def Base_var_from(self, param):
    """
    - name: set variables from file
      var_from:
        yaml: filename
        json: filename
        toml: filename
    """
    if "yaml" in param:
        with open(param.get("yaml")) as f:
            self.do_var(yaml.load(f))
    if "json" in param:
        with open(param.get("json")) as f:
            self.do_var(json.load(f))
    if "toml" in param:
        with open(param.get("toml")) as f:
            self.do_var(toml.load(f))


var_from_if_not_schema = var_from_schema


def Base_var_from_if_not(self, param):
    """
    - name: set variables from file
      var_from_if_not:
        yaml: filename
        json: filename
        toml: filename
    """
    if "yaml" in param:
        with open(param.get("yaml")) as f:
            self.do_var_if_not(yaml.load(f))
    if "json" in param:
        with open(param.get("json")) as f:
            self.do_var_if_not(json.load(f))
    if "toml" in param:
        with open(param.get("toml")) as f:
            self.do_var_if_not(toml.load(f))


def Base_runcmd(self, param):
    """
    - name: run shell command
      runcmd: echo hello
    - name: word count
      runcmd:
        stdin: "{{page_source}}"
        cmd: wc
    """
    if isinstance(param, (list, tuple, str)):
        self.log.debug("run: %s", param)
        out = self.runcmd(param)
        self.log.debug("result: %s", out)
        return out
    elif isinstance(param, dict):
        cmd = param.get("cmd", None)
        stdin = param.get("stdin", None)
        stdout = param.get("stdout", None)
        stderr = param.get("stderr", None)
        if cmd is None:
            raise Exception("missing cmd: %s" % (param))
        if stdin is not None:
            sin = tempfile.TemporaryFile()
            sin.write(stdin.encode("utf-8"))
            sin.seek(0)
        else:
            sin = DEVNULL
        if stderr is not None:
            serr = open(stderr)
        else:
            serr = DEVNULL
        out = self.runcmd(cmd, stdin=sin, stderr=serr)
        self.log.info("result: %s", out)
        if stdout is not None:
            with open(stdout, "w") as f:
                f.write(out)
        return out
    else:
        raise Exception("runcmd: param not supported: %s" % (param))


echo_schema = yaml.load("""
oneOf:
  - type: string
  - "$ref": "#/definitions/common/textvalue"
""")


def Base_echo(self, param):
    """
    - name: debug message
      echo:
        text: hello world
    """
    if isinstance(param, str):
        self.log.info("echo %s", param)
        return param
    else:
        txt = self.getvalue(param)
        self.log.info("echo %s", txt)
        return txt


sleep_schema = {"type": "integer"}


def Base_sleep(self, param):
    """
    - name: wait 10 sec
      sleep: 10
    """
    self.lock.release()
    time.sleep(int(param))
    self.lock.acquire()


include_schema = yaml.load("""
oneOf:
  - type: string
  - type: array
    items: {type: string}
""")


def Base_include(self, param):
    """
    - name: run other file
      include: filename.yaml
    - name: run other files
      include:
        - file1.yaml
        - file2.yaml
    """
    if isinstance(param, (list, tuple)):
        for fname in param:
            self.log.info("loading %s", fname)
            with open(fname) as f:
                self.lock.release()
                self.run(yaml.load(f))
                self.lock.acquire()
    elif isinstance(param, str):
        self.log.info("loading %s", param)
        with open(param) as f:
            self.lock.release()
            self.run(yaml.load(f))
            self.lock.acquire()
    else:
        raise Exception("cannot load: %s" % (param))


def Base_config(self, param):
    """
    - name: configuration
      config:
        wait: 10
        cookie:
          var1: val1
        window:
          width: 600
          height: 480
    """
    if "wait" in param:
        self.log.debug("implicitly wait %s sec", param.get("wait"))
        self.driver.implicitly_wait(param.get("wait"))
    if "cookie" in param:
        self.log.debug("cookie update: %s" % (param.get("cookie", {}).keys()))
        self.driver.add_cookie(param.get("cookie"))
    if "window" in param:
        self.log.info("window size update: %s" % (param.get("window", {})))
        win = param.get("window")
        if win.get("maximize", False):
            self.driver.maximize_window()
        else:
            x = win.get("x")
            y = win.get("y")
            if x is not None and y is not None:
                self.log.debug("set window pos: x=%d, y=%d", x, y)
                self.driver.set_window_position(x, y)
            width = win.get("width")
            height = win.get("height")
            if width is not None and height is not None:
                self.log.debug("set window size: width=%d, height=%d", width, height)
                self.driver.set_window_size(width, height)
    if "log" in param:
        logconf = param.get("log")
        if isinstance(logconf, str):
            logging.config.fileConfig(logconf)
        elif isinstance(logconf, dict):
            logging.config.dictConfig(logconf)
        else:
            raise Exception("config.log must be filename or dict: %s", param.get("log"))
    if "page_load_timeout" in param:
        self.driver.set_page_load_timeout(param.get("page_load_timeout"))
    if "implicitly_wait" in param:
        self.driver.implicitly_wait(param.get("implicitly_wait"))
    if "script_timeout" in param:
        self.driver.set_script_timeout(param.get("script_timeout"))


ensure_schema = {"$ref": "#/definitions/common/condition"}


def Base_ensure(self, param):
    """
    - name: check condition
      ensure:
        eq:
          - "{{selenible_version}}"
          - "0.1"
    """
    if not self.eval_param(param):
        self.log.error("condition failed: %s", param)
        raise Exception("condition failed: %s" % (param))


ensure_not_schema = ensure_schema


def Base_ensure_not(self, param):
    """
    - name: check condition
      ensure_not:
        eq:
          - "{{selenible_version}}"
          - "0.3"
    """
    if self.eval_param(param):
        self.log.error("condition(not) failed: %s", param)
        raise Exception("condition(not) failed: %s" % (param))


xslt_schema = yaml.load("""
type: object
properties:
  proc: {type: string}
  output: {type: string}
""")


def Base_xslt(self, param):
    """
    - name: transform
      xslt:
        proc: |
            <xsl:stylesheet version="1.0"  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
                <xsl:template match="/">
                    <xsl:value-of select="//a/@href" />
                </xsl:template>
            </xsl:stylesheet>
        output: outfile.txt
    """
    if isinstance(param, dict):
        proc = etree.XSLT(etree.XML(param.get("proc", "")))
        output = param.get("output", None)
        elem = self.findmany(param)
        if elem == [None]:
            p = etree.parse(self.driver.page_source)
            rst = [str(proc(p))]
        else:
            rst = []
            for e in elem:
                p = etree.parse(e.get_attribute("innerHTML"))
                rst.append(str(proc(p)))
        if output is not None:
            with open(output, "w") as f:
                for x in rst:
                    f.write(str(x))
        return rst
    else:
        raise Exception("invalid parameter: %s" % (param))


download_schema = yaml.load("""
type: object
properties:
  url: {type: string}
  method: {type: string}
  query: {type: object}
  headers: {type: object}
  json: {type: boolean}
  output: {type: string}
""")


def Base_download(self, param):
    """
    - name: download file using python-requests
      download:
        url: "{{current_url}}/file1"
        method: get
        query:
          var1: val1
        timeout: 10
        json: false
        output: outfile.txt
    """
    url = param.get("url", None)
    if url is None:
        raise Exception("url mut set: %s" % (param))
    parsed_url = urllib.parse.urlparse(url)
    self.log.debug("URL parsed: %s", parsed_url)
    method = param.get("method", "get")
    query = param.get("query", None)
    cookies = self.driver.get_cookies()
    headers = param.get("headers", None)
    timeout = param.get("timeout", None)
    is_json = param.get("json", False)
    sess = requests.Session()
    output = param.get("output", None)
    for ck in cookies:
        sess.cookies.set(ck.get("name"), ck.get("value"),
                         path=ck.get("path", "/"), domain=ck.get("domain", ""),
                         secure=ck.get("secure", False))
    resp = sess.request(method, url, params=query, headers=headers, timeout=timeout)
    if output is not None:
        with open(output, "w") as f:
            f.write(resp.content)
    if is_json:
        return resp.json()
    return resp.text


set_schema = yaml.load("""
anyOf:
  - "$ref": "#/definitions/common/locator"
  - "$ref": "#/definitions/common/textvalue"
  - type: object
    properties:
      parseHTML: {type: boolean}
""")


def Base_set(self, param):
    """
    - name: set variable (v1="blabla")
      register: v1
      set:
        text: blabla
    - name: set variable v2
      register: v2
      set:
        xpath: '//a'
        parseHTML: true
    - name: echo
      echo: 'v1={{v1}}, v2={%for x in v2%}{{x.get("href")}},{%endfor%}'
    """
    res = self.getvalue(param)
    if res is not None:
        return self.return_element(param, res)
    return self.return_element(param, self.findmany(param))
