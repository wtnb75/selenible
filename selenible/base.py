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
import urllib.parse
from logging import getLogger, basicConfig, DEBUG, INFO, captureWarnings

import json
import yaml
import toml
import click
import jsonpath_rw
import jsonschema
from pkg_resources import resource_stream
from lxml import etree
from PIL import Image, ImageChops
from selenium import webdriver
from selenium.webdriver.common.by import By
from jinja2 import Template
from .version import VERSION


class Base:
    driver = None
    passcmd = "pass"
    schema = yaml.load(resource_stream(__name__, 'schema/base.yaml'))

    def __init__(self, driver):
        self.step = False
        self.driver = driver
        self.variables = {
            "driver": driver.name,
            "desired_capabilities": driver.desired_capabilities,
            "selenible_version": VERSION,
        }
        self.log = getLogger(self.__class__.__name__)
        self.log.info("driver started")

    def __del__(self):
        if hasattr(self, "driver") and self.driver is not None:
            self.driver.close()
            self.driver.quit()
            self.driver = None

    @classmethod
    def load_modules(cls, modname):
        log = getLogger(cls.__name__)
        log.info("load module %s", modname)
        pfx = cls.__name__ + "_"
        try:
            mod1 = __import__("selenible.modules", globals(), locals(), [modname], 0)
            mod = getattr(mod1, modname)
        except AttributeError as e:
            log.debug("cannot import %s from selenible.modules", modname)
            return
        log.debug("loaded: %s", dir(mod))
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
            log.info("register methods: %s", "/".join(mtd))

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
            self.run1(cmd)
            if self.step:
                ans = input("step(q=exit, s=screenshot, other=continue):")
                if ans == "q":
                    break
                elif ans == "s":
                    tf = tempfile.NamedTemporaryFile(suffix=".png")
                    self.saveshot(tf.name)
                    img = Image.open(tf.name)
                    img.show()
                    tf.close()

    def run1(self, cmd):
        withitem = self.render_dict(cmd.pop("with_items", None))
        if withitem is not None:
            loopctl = self.render_dict(cmd.pop("loop_control", {}))
            loopvar = loopctl.get("loop_var", "item")
            loopiter = loopctl.get("loop_iter", "iter")
            start = time.time()
            self.log.info("start loop: %d times", len(withitem))
            for i, j in enumerate(withitem):
                self.variables[loopvar] = j
                self.variables[loopiter] = i
                self.log.info("loop by %d: %s", i, j)
                self.run1(cmd.copy())
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
                res = mtd(param)

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
        raise Exception("exec js not implemented")

    def runcmd(self, cmd, encoding="utf-8", stdin=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL):
        return subprocess.check_output(cmd, stdin=stdin, stderr=stderr,
                                       shell=True).decode(encoding)

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
        return etree.fromstring(x.get_attribute("outerHTML"))


class Phantom(Base):
    def __init__(self, driver=None):
        if driver is None:
            driver = webdriver.PhantomJS()
        super().__init__(driver)
        self.driver.command_executor._commands['executePhantomScript'] = (
            'POST', '/session/$sessionId/phantom/execute')

    def execute(self, script, args):
        self.driver.execute('executePhantomScript',
                            {'script': script, 'args': args})

    def do_config(self, param):
        """
        - name: config phantomjs
          config:
            cookie_flag: false
            proxy:
              url: http://proxy.host:8080/
        - name: config common
          config:
            wait: 10
            cookie:
              var1: val1
            window:
              width: 600
              height: 480
        """
        super().do_config(param)
        if "cookie_flag" in param:
            if param.get("cookie_flag", True):
                self.execute("phantom.cookiesEnabled=true")
            else:
                self.execute("phantom.cookiesEnabled=false")
        if "proxy" in param:
            prox = param.get("proxy")
            host = prox.get("host")
            port = prox.get("port", 8080)
            ptype = prox.get("type", "http")
            username = prox.get("username")
            password = prox.get("password")
            with_page = prox.get("page", False)
            url = prox.get("url")
            if url is not None:
                u = urllib.parse.urlparse(url)
                if u.scheme in ("", b""):
                    self.log.debug("proxy not set. pass")
                    return
                proxyscript = '''setProxy("{}", {}, "{}", "{}", "{}")'''.format(
                    u.hostname, u.port, ptype, u.username, u.password)
            elif host is None:
                proxyscript = '''setProxy("")'''
            elif username is not None and password is not None:
                proxyscript = '''setProxy("{}", {}, "{}", "{}", "{}")'''.format(
                    host, port, ptype, username, password)
            else:
                proxyscript = '''setProxy("{}", {}, "{}")'''.format(
                    host, port, ptype)
            if with_page:
                prefix = "page"
            else:
                prefix = "phantom"
            self.execute(prefix + "." + proxyscript, [])

    def saveshot(self, output_fn):
        base, ext = os.path.splitext(output_fn)
        if ext in (".pdf", ".PDF"):
            page_format = 'this.paperSize = {format: "A4", orientation: "portrait" };'
            self.execute(page_format, [])
            render = '''this.render("{}")'''.format(output_fn)
            self.execute(render, [])
        else:
            super().saveshot(output_fn)


class Chrome(Base):
    def __init__(self, driver=None):
        if driver is None:
            driver = webdriver.Chrome()
        super().__init__(driver)


class Firefox(Base):
    def __init__(self, driver=None):
        if driver is None:
            driver = webdriver.Firefox()
        super().__init__(driver)


class Safari(Base):
    def __init__(self, driver=None):
        if driver is None:
            driver = webdriver.Safari()
        super().__init__(driver)


class WebKitGTK(Base):
    def __init__(self, driver=None):
        if driver is None:
            driver = webdriver.WebKitGTK()
        super().__init__(driver)


class Edge(Base):
    def __init__(self, driver=None):
        if driver is None:
            driver = webdriver.Edge()
        super().__init__(driver)


drvmap = {
    "phantom": Phantom,
    "chrome": Chrome,
    "firefox": Firefox,
    "safari": Safari,
    "edge": Edge,
    "webkit": WebKitGTK,
}


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


def loadmodules(driver, extension):
    Base.load_modules("ctrl")
    Base.load_modules("browser")
    for ext in extension:
        Base.load_modules(ext)
    drvcls = drvmap.get(driver, Phantom)
    drvcls.load_modules(drvcls.__name__.lower())
    for ext in extension:
        drvcls.load_modules(ext)
    return drvcls


@cli.command(help="run playbook")
@click.option("--verbose", is_flag=True, default=False)
@click.option("--driver", default="phantom", type=click.Choice(drvmap.keys()))
@click.option("--step", is_flag=True, default=False)
@click.option("-e", multiple=True)
@click.option("--extension", multiple=True)
@click.option("--var", type=click.File('r'), required=False)
@click.argument("input", type=click.File('r'), required=False)
def run(verbose, input, driver, step, var, e, extension):
    logfmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    if verbose:
        basicConfig(format=logfmt, level=DEBUG)
    else:
        basicConfig(format=logfmt, level=INFO)
    captureWarnings(True)
    drvcls = loadmodules(driver, extension)
    if input is not None:
        prog = yaml.load(input)
        b = drvcls()
        for k, v in os.environ.items():
            b.variables[k] = v
        if var is not None:
            b.load_vars(var)
        for x in e:
            k, v = x.split("=", 1)
            try:
                b.variables[k] = json.loads(v)
            except Exception:
                b.variables[k] = v
        b.step = step
        b.run(prog)
    else:
        click.echo("show usage: --help")


@cli.command("list-modules", help="list modules")
@click.option("--driver", default="phantom", type=click.Choice(drvmap.keys()))
@click.option("--extension", multiple=True)
def list_modules(driver, extension):
    drvcls = loadmodules(driver, extension)
    from texttable import Texttable
    table = Texttable()
    table.set_cols_align(["l", "l"])
    # table.set_deco(Texttable.HEADER)
    table.header(["Module", "Description"])
    mods = drvcls.listmodule()
    for k in sorted(mods.keys()):
        table.add_row([k, mods[k]])
    print(table.draw())


@cli.command("dump-schema", help="dump json schema")
@click.option("--driver", default="phantom", type=click.Choice(drvmap.keys()))
@click.option("--extension", multiple=True)
@click.option("--format", default="yaml", type=click.Choice(["yaml", "json", "python"]))
def dump_schema(driver, extension, format):
    drvcls = loadmodules(driver, extension)
    if format == "yaml":
        yaml.dump(drvcls.schema, sys.stdout, default_flow_style=False)
    elif format == "json":
        json.dump(drvcls.schema, fp=sys.stdout, ensure_ascii=False)
    elif format == "python":
        print(drvcls.schema)
    else:
        raise Exception("unknown format: %s" % (format))


@cli.command(help="validate by json schema")
@click.option("--driver", default="phantom", type=click.Choice(drvmap.keys()))
@click.option("--extension", multiple=True)
@click.argument("input", type=click.File('r'), required=False)
def validate(driver, extension, input):
    drvcls = loadmodules(driver, extension)
    prog = yaml.load(input)
    print("validating...")
    jsonschema.validate(prog, drvcls.schema)
    print("OK")


if __name__ == "__main__":
    cli()
