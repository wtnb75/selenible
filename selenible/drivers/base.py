import sys
import os
import subprocess
import inspect
import tarfile
import zipfile
import time
import functools
import tempfile
import getpass
import copy
from logging import getLogger

import json
import yaml
import toml
import jsonpath_rw
from threading import Lock
from pkg_resources import resource_stream
from lxml import etree
from PIL import Image, ImageChops
from selenium.webdriver.common.by import By
from jinja2 import Template
from ..version import VERSION


class Base:
    passcmd = "pass"
    schema = yaml.load(resource_stream(__name__, '../schema/base.yaml'))

    def __init__(self):
        self.lock = Lock()
        self.step = False
        self.save_every = False
        self._driver = None
        self.variables = {
            "selenible_version": VERSION,
        }
        self.funcs = {}
        self.log = getLogger(self.__class__.__name__)
        self.browser_args = {}

    @property
    def driver(self):
        if self._driver is None:
            self._driver = self.boot_driver()
            self.log.info("driver started")
        self.variables["driver"] = self._driver.name
        self.variables["desired_capabilities"] = self._driver.desired_capabilities
        return self._driver

    def get_options(self):
        return {}

    def boot_driver(self):
        raise Exception("please implement")

    def shutdown_driver(self):
        if hasattr(self, "_driver") and self._driver is not None:
            self._driver.close()
            self._driver.quit()
            self._driver = None

    def __del__(self):
        self.shutdown_driver()

    @classmethod
    def load_modules(cls, modname):
        log = getLogger(cls.__name__)
        log.debug("load module %s", modname)
        pfx = cls.__name__ + "_"
        try:
            mm = modname.rsplit(".", 1)
            if len(mm) == 1:
                modfirst = "selenible.modules"
                modlast = mm[0]
            else:
                modfirst = mm[0]
                modlast = mm[1]
            mod1 = __import__(modfirst, globals(), locals(), [modlast], 0)
            mod = getattr(mod1, modlast)
        except AttributeError as e:
            log.debug("cannot import %s from %s", modlast, modfirst)
            return
        log.debug("names: %s", dir(mod))
        mtd = []
        for m in filter(lambda f: f.startswith(pfx), dir(mod)):
            fn = getattr(mod, m)
            if callable(fn):
                log.debug("register method: %s", m[len(pfx):])
                name = "do_%s" % (m[len(pfx):])
                setattr(cls, name, fn)
                funcname = m[len(pfx):]
                mtd.append(funcname)
                scmname = "%s_schema" % (funcname)
                if hasattr(mod, scmname):
                    scm = getattr(mod, scmname)
                    if isinstance(scm, dict):
                        cls.schema["items"]["properties"][funcname] = scm
            else:
                log.warn("%s is not callable", fn)
        if len(mtd) != 0:
            log.debug("register methods: %s", "/".join(mtd))

    def load_vars(self, fp):
        self.variables.update(yaml.load(fp))

    def render(self, s):
        return Template(s).render(self.variables)

    def render_dict(self, d):
        if isinstance(d, dict):
            res = {}
            for k, v in d.items():
                res[k] = self.render_dict(v)
            return res
        elif isinstance(d, (list, tuple)):
            return [self.render_dict(x) for x in d]
        elif isinstance(d, str):
            return self.render(d)
        return d

    def run(self, prog):
        for cmd in prog:
            self.log.debug("cmd %s", cmd)
            with self.lock:
                self.run1(cmd)
            if self.step:
                ans = input("step(q=exit, s=screenshot, c=continue, other=continue):")
                if ans == "q":
                    break
                elif ans == "s":
                    tf = tempfile.NamedTemporaryFile(suffix=".png")
                    self.saveshot(tf.name)
                    img = Image.open(tf.name)
                    img.show()
                    tf.close()
                elif ans == "c":
                    self.step = False
            if self.save_every:
                self.do_screenshot({})

    def run1(self, cmd):
        withitem = self.render_dict(cmd.pop("with_items", None))
        delay = cmd.pop("delay", 0)
        if withitem is not None:
            loopctl = self.render_dict(cmd.pop("loop_control", {}))
            loopvar = loopctl.get("loop_var", "item")
            loopiter = loopctl.get("loop_iter", "iter")
            start = time.time()
            if isinstance(withitem, dict) and "range" in withitem:
                rg = withitem.get("range")
                if isinstance(rg, (list, tuple)):
                    withitem = range(*rg)
                else:
                    withitem = range(int(rg))
            self.log.info("start loop: %d times", len(withitem))
            for i, j in enumerate(withitem):
                self.variables[loopvar] = j
                self.variables[loopiter] = i
                self.log.info("loop by %d: %s", i, j)
                self.run1(cmd.copy())
                time.sleep(delay)
            self.variables.pop(loopvar)
            self.variables.pop(loopiter)
            self.log.info("finish loop: %f second", time.time() - start)
            return
        # cmd = self.render_dict(cmd)
        name = self.render_dict(cmd.pop("name", ""))
        condition = self.render_dict(cmd.pop("when", True))
        ncondition = self.render_dict(cmd.pop("when_not", False))
        if not self.eval_param(condition):
            self.log.info("skip(when) %s", repr(name))
            return
        if self.eval_param(ncondition):
            self.log.info("skip(when_not) %s", repr(name))
            return
        register = self.render_dict(cmd.pop("register", None))
        ignoreerr = self.render_dict(cmd.pop("ignore_error", False))
        if len(cmd) != 1:
            raise Exception("too many parameters: %s" % (cmd.keys()))
        self.variables["env"] = os.environ
        if self._driver is not None:
            # set driver related variables
            for v in ("current_url", "page_source", "title",
                      "window_handles", "session_id", "current_window_handle",
                      "capabilities", "log_types", "w3c"):
                self.variables[v] = getattr(self.driver, v)
            for v in ("cookies", "window_size", "window_position"):
                self.variables[v] = getattr(self.driver, "get_" + v)()
            self.variables["log"] = {}
            for logtype in self.driver.log_types:
                self.variables["log"][logtype] = self.driver.get_log(logtype)
                # phantomjs case
                try:
                    if logtype == "har":
                        logdata = json.loads(self.variables["log"][logtype][0]["message"])
                        self.variables["log"][logtype][0]["message"] = logdata
                except (KeyError, IndexError, json.decoder.JSONDecodeError) as e:
                    self.log.debug("log.har.0.message does not exists or not json")
                    pass
        for c in cmd.keys():
            mtdname = "do_%s" % (c)
            mtdname2 = "do2_%s" % (c)
            if hasattr(self, mtdname):
                mtd = getattr(self, mtdname)
                param = self.render_dict(cmd.get(c))
                self.log.debug("%s %s %s", name, c, param)
                self.log.info("start %s", repr(name))
                start = time.time()
                try:
                    res = mtd(param)
                except Exception as e:
                    if ignoreerr:
                        self.log.info("error(ignored): %s", e)
                    else:
                        self.log.error("error: %s", e)
                        raise e
                if register is not None:
                    self.log.debug("register %s = %s", register, res)
                    self.variables[register] = res
                self.log.info("finish %s %f second", repr(name), time.time() - start)
            elif hasattr(self, mtdname2):
                # 1st class module
                mtd = getattr(self, mtdname2)
                param = cmd.get(c)
                self.log.debug("%s %s %s", name, c, param)
                res = mtd(c, param)
                if register is not None:
                    self.log.debug("register %s = %s", register, res)
                    self.variables[register] = res
            else:
                raise Exception("module not found: %s" % (c))
            time.sleep(delay)

    def do2_defun(self, funcname, params):
        """
        - name: define func1
          defun:
            name: func1
            args: [a1, a2]
            return: r
            progn:
              - name: hello
                echo: "{{a1}} is {{a2}}"
              - name: set-retval
                var:
                  r: "hello"
        - name: call func1
          func1:
            a1: xyz
            a2: abc
          register: rval1
        - name: return value
          echo: "{{rval1}}"
        """
        funcname = params.get("name")
        args = params.get("args", [])
        retvar = params.get("return", None)
        progn = params.get("progn", [])
        self.funcs[funcname] = (args, retvar, progn)
        setattr(self, "do2_" + funcname, self.run_func)

    def run_func(self, funcname, params):
        params = self.render_dict(params)
        args, retvar, progn = self.funcs.get(funcname, ([], [], None))
        oldvars = self.variables
        self.variables = copy.deepcopy(self.variables)
        for a in args:
            self.variables[a] = params.get(a)
        self.log.debug("running %s", progn)
        self.run(progn)
        newvars = self.variables
        self.variables = oldvars
        self.log.debug("return val %s -> %s", retvar, newvars.get(retvar))
        return newvars.get(retvar)

    @classmethod
    def listmodule(cls):
        pfx = ["do_", "do2_"]
        res = {}
        for x in dir(cls):
            for p in pfx:
                if x.startswith(p):
                    doc = inspect.getdoc(getattr(cls, x))
                    if doc is None:
                        doc = "(no document)"
                    res[x[len(p):]] = doc
        return res

    def execute(self, script, args):
        self.driver.execute_script(script, args)

    def runcmd(self, cmd, encoding="utf-8", stdin=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL):
        flag = False
        if isinstance(cmd, str):
            flag = True
        self.log.debug("run(%s) %s", flag, cmd)
        ret = subprocess.check_output(cmd, stdin=stdin, stderr=stderr,
                                      shell=flag).decode(encoding)
        self.log.debug("result: %s", ret)
        return ret

    def saveshot(self, output_fn):
        self.driver.save_screenshot(output_fn)

    def cropimg(self, filename, param):
        base, ext = os.path.splitext(filename)
        if ext not in (".png", ".PNG"):
            self.log.info("non-png: %s ...pass", filename)
            return
        if isinstance(param, str) and param == "auto":
            img = Image.open(filename)
            bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))
            diff = ImageChops.difference(img, bg)
            diff = ImageChops.add(diff, diff, 2.0, -100)
            box = diff.getbbox()
            self.log.info("auto crop: %s", box)
            crop = img.crop(box)
            crop.save(filename)
        elif isinstance(param, (tuple, list)):
            img = Image.open(filename)
            self.log.info("manual crop: %s", param)
            crop = img.crop(param)
            crop.save(filename)
        else:
            raise Exception("not implemented yet: crop %s %s" % (filename, param))

    def optimizeimg(self, filename):
        base, ext = os.path.splitext(filename)
        if ext not in (".png", ".PNG"):
            self.log.info("non-png: %s ...pass", filename)
            return
        self.log.info("optimize image: %s", filename)
        before = os.stat(filename)
        if before.st_size == 0:
            raise Exception("image size is zero: %s" % (filename))
        cmd = ["optipng", "-o9", filename]
        self.log.debug("run: %s", cmd)
        sout = self.runcmd(cmd)
        self.log.debug("command result: %s", sout)
        after = os.stat(filename)
        self.log.info("%s: before=%d, after=%d, reduce %d bytes (%.1f %%)", filename,
                      before.st_size, after.st_size, before.st_size - after.st_size,
                      100.0 * (before.st_size - after.st_size) / before.st_size)

    def resizeimg(self, filename, param):
        base, ext = os.path.splitext(filename)
        if ext not in (".png", ".PNG"):
            self.log.info("non-png: %s ...pass", filename)
            return
        self.log.info("resize image: %s %s", filename, param)
        img = Image.open(filename)
        rst = img.resize(tuple(param))
        rst.save(filename)

    def archiveimg(self, filename, param):
        assert isinstance(param, str)
        base, ext = os.path.splitext(param)
        if ext in (".zip", ".cbz"):
            with zipfile.ZipFile(param, 'a') as zf:
                self.log.debug("zip %s %s", param, filename)
                zf.write(filename)
                os.unlink(filename)
        elif ext in (".tar"):
            with tarfile.open(param, 'a') as tf:
                self.log.debug("tar %s %s", param, filename)
                tf.add(filename)
                os.unlink(filename)
        else:
            raise Exception("not implemented yet: archive %s %s" % (filename, param))

    findmap = {
        "id": By.ID,
        "xpath": By.XPATH,
        "linktext": By.LINK_TEXT,
        "partlinktext": By.PARTIAL_LINK_TEXT,
        "name": By.NAME,
        "tag": By.TAG_NAME,
        "class": By.CLASS_NAME,
        "select": By.CSS_SELECTOR,
    }

    def removelocator(self, param):
        res = copy.deepcopy(param)
        res.pop("nth", None)
        for k, v in self.findmap.items():
            res.pop(k, None)
        for v in filter(lambda f: not f.startswith("_"), dir(By)):
            res.pop(v, None)
            res.pop(v.lower(), None)
            if getattr(By, v) in res:
                res.pop(getattr(By, v), None)
        return res

    def getlocator(self, param):
        for k, v in self.findmap.items():
            if k in param:
                return (v, param.get(k))
        for v in filter(lambda f: not f.startswith("_"), dir(By)):
            if v in param:
                return (getattr(By, v), param.get(v))
            if v.lower() in param:
                return (getattr(By, v), param.get(v.lower()))
            if getattr(By, v) in param:
                return (getattr(By, v), param.get(getattr(By, v)))
        return (None, None)

    def findone(self, param):
        k, v = self.getlocator(param)
        if k is not None:
            return self.driver.find_element(k, v)
        if param.get("active", False):
            return self.driver.switch_to.active_element
        return None

    def findmany2one(self, param):
        ret = self.findmany(param)
        nth = param.get("nth", 0)
        if isinstance(ret, (list, tuple)):
            self.log.debug("found %d elements. choose %d-th", len(ret), nth)
            return ret[nth]
        return ret

    def findmany(self, param):
        k, v = self.getlocator(param)
        if k is not None:
            return self.driver.find_elements(k, v)
        if param.get("active", False):
            return [self.driver.switch_to.active_element]
        return []

    def getvalue(self, param):
        if isinstance(param, str):
            return param
        encoding = param.get("encoding", "utf-8")
        if "text" in param:
            return param.get("text")
        elif "password" in param:
            label = param.get("password")
            return self.runcmd([self.passcmd, label], encoding).strip()
        elif "pipe" in param:
            cmd = param.get("pipe")
            return self.runcmd(cmd, encoding).strip()
        elif "yaml" in param:
            p = param.get("yaml")
            with open(p.get("file")) as f:
                data = yaml.load(f)
                return jsonpath_rw.parse(p.get("path", "*")).find(data)[0].value
        elif "json" in param:
            p = param.get("json")
            with open(p.get("file")) as f:
                data = json.load(f)
                return jsonpath_rw.parse(p.get("path", "*")).find(data)[0].value
        elif "toml" in param:
            p = param.get("toml")
            with open(p.get("file")) as f:
                data = toml.load(f)
                return jsonpath_rw.parse(p.get("path", "*")).find(data)[0].value
        elif "input" in param:
            return input(param.get("input"))
        elif "input_password" in param:
            return getpass.getpass(param.get("input_password"))
        elif "input_multiline" in param:
            print(param.get("input_multiline"))
            res = sys.stdin.read()
            sys.stdin.seek(0)
            return res
        return None

    def eval_param(self, param):
        if isinstance(param, (list, tuple)):
            return [self.eval_param(x) for x in param]
        elif isinstance(param, dict):
            res = []
            for k, v in param.items():
                if k in ("eq", "equals", "==", "is"):
                    res.append(len(set(self.eval_param(v))) == 1)
                elif k in ("neq", "not_equals", "!=", "is_not"):
                    res.append(len(set(self.eval_param(v))) >= 2)
                elif k in ("not"):
                    res.append(not self.eval_param(v))
                elif k in ("and", "&", "&&"):
                    res.append(functools.reduce(lambda a, b: a and b, self.eval_param(v)))
                elif k in ("or", "|", "||"):
                    res.append(functools.reduce(lambda a, b: a or b, self.eval_param(v)))
                elif k in ("xor", "^"):
                    res.append(functools.reduce(lambda a, b: bool(a) ^ bool(b), self.eval_param(v)))
                elif k in ("add", "sum", "plus", "+"):
                    res.append(functools.reduce(lambda a, b: a + b, self.eval_param(v)))
                elif k in ("sub", "minus", "-"):
                    res.append(functools.reduce(lambda a, b: a - b, self.eval_param(v)))
                elif k in ("mul", "times", "*"):
                    res.append(functools.reduce(lambda a, b: a * b, self.eval_param(v)))
                elif k in ("div", "/"):
                    res.append(functools.reduce(lambda a, b: a / b, self.eval_param(v)))
                elif k in ("selected",):
                    for e in self.findmany(v):
                        res.append(e.is_selected())
                elif k in ("not_selected", "unselected"):
                    for e in self.findmany(v):
                        res.append(not e.is_selected())
                elif k in ("enabled",):
                    for e in self.findmany(v):
                        res.append(e.is_enabled())
                elif k in ("not_enabled", "disabled"):
                    for e in self.findmany(v):
                        res.append(not e.is_enabled())
                elif k in ("displayed",):
                    for e in self.findmany(v):
                        res.append(e.is_displayed())
                elif k in ("not_displayed", "undisplayed"):
                    for e in self.findmany(v):
                        res.append(not e.is_displayed())
                elif k in ("defined",):
                    if isinstance(v, (tuple, list)):
                        res.extend([x in self.variables for x in v])
                    elif isinstance(v, str):
                        res.append(v in self.variables)
                    else:
                        raise Exception("invalid argument: %s" % (v))
                elif k in ("not_defined", "undefined"):
                    if isinstance(v, (tuple, list)):
                        res.extend([x not in self.variables for x in v])
                    elif isinstance(v, str):
                        res.append(v not in self.variables)
                    else:
                        raise Exception("invalid argument: %s" % (v))
                else:
                    raise Exception("operator not supported: %s (%s)" % (k, v))
            return functools.reduce(lambda a, b: a and b, res)
        return param

    def return_element(self, param, elem):
        if elem is None:
            return elem
        if not param.get("parseHTML", False):
            return elem
        if isinstance(elem, (tuple, list)):
            return [etree.fromstring(x.get_attribute("outerHTML")) for x in elem]
        elif isinstance(elem, str):
            return etree.fromstring(elem)
        return etree.fromstring(elem.get_attribute("outerHTML"))
