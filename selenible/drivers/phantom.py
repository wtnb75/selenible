
import os
import urllib.parse
from selenium import webdriver
from . import Base


class Phantom(Base):
    def boot_driver(self):
        self.log.debug("phantom args: %s", self.browser_args)
        return webdriver.PhantomJS(**self.browser_args)

    def saveshot(self, output_fn):
        base, ext = os.path.splitext(output_fn)
        if ext in (".pdf", ".PDF"):
            page_format = 'this.paperSize = {format: "A4", orientation: "portrait" };'
            self.execute(page_format, [])
            render = '''this.render("{}")'''.format(output_fn)
            self.execute(render, [])
        else:
            super().saveshot(output_fn)

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
