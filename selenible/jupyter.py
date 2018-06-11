import io
import base64
import shlex
import inspect
import yaml
from PIL import Image
from logging import getLogger, DEBUG, StreamHandler
from ipykernel.kernelbase import Kernel
from .version import VERSION
from . import cli
from selenium.webdriver.remote.webelement import WebElement


class SelenibleKernel(Kernel):
    log = getLogger("selenible")
    implementation = 'Selenible'
    implementation_version = '0.0.1'
    language = 'selenible'
    language_version = VERSION
    language_info = {
        'name': 'Selenible',
        'mimetype': 'text/yaml',
        'file_extension': '.yaml',
    }
    banner = "Selenible kernel"
    driver_name = "phantom"
    extensions = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._drv = None
        self.thumbnail = None
        self.log.setLevel(DEBUG)
        self.log.info("kernel started")

    @property
    def drv(self):
        if self._drv is None:
            drvcls = cli.loadmodules(self.driver_name, self.extensions)
            self.log.info("driver: cls=%s, name=%s, exts=%s",
                          drvcls, self.driver_name, self.extensions)
            self._drv = drvcls()
            drvlog = self._drv.log
            self.logio = io.StringIO()
            drvlog.addHandler(StreamHandler(self.logio))
        return self._drv

    def do_shutdown(self, restart):
        self.log.info("kernel finished")
        del self._drv
        self._drv = None

    def cmd_driver(self, args):
        "set driver: phantom, chrome, firefox, etc..."
        self.log.info("driver: %s -> %s", self.driver_name, args[0])
        self.driver_name = args[0]

    def cmd_module(self, args):
        "load modules"
        self.extensions = args

    def cmd_shutdown(self, args):
        "shutdown driver"
        del self._drv
        self._drv = None

    def cmd_loglevel(self, args):
        "set log level"
        self.drv.log.setLevel(args[0])

    def cmd_thumbnail(self, args):
        "set thumbnail size"
        self.thumbnail = tuple(map(lambda f: int(f), args[:2]))

    def cmd_help(self, args):
        "show this help"
        cmds = filter(lambda f: f.startswith("cmd_"), dir(self))
        cmds = sorted(filter(lambda f: callable(getattr(self, f)), cmds))
        cmds = [(x.split("_", 1)[1], inspect.getdoc(getattr(self, x))) for x in cmds]
        txt = "\n".join(["%s: %s" % x for x in cmds])
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': txt})

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        if code.startswith("%"):
            token = shlex.split(code)
            cmd = token[0].lstrip("%")
            args = token[1:]
            if hasattr(self, "cmd_"+cmd):
                fn = getattr(self, "cmd_"+cmd)
                if callable(fn):
                    fn(args)
                else:
                    self.cmd_help()
            else:
                return {'status': 'error', 'ename': "NotFound", "evalue":  "not found", "traceback": []}
            return {'status': 'ok', 'execution_count': self.execution_count}
        v = yaml.load(code)
        self.log.info("yaml: %s", v)
        if not silent:
            stream_content = {'name': 'stdout', 'text': yaml.dump(v, default_flow_style=False)}
            self.send_response(self.iopub_socket, 'stream', stream_content)
        if isinstance(v, (list, tuple)):
            res = self.drv.run(v)
        elif isinstance(v, dict):
            res = self.drv.run([v])
        elif isinstance(v, str):
            res = self.drv.run([{v: None}])
        else:
            raise Exception("invalid type: %s : %s" % (type(v), v))

        logstr = self.logio.getvalue()
        self.logio.seek(0)
        self.logio.truncate(0)
        if logstr != "":
            stream_content = {'data': {"text/plain": logstr},
                              'execution_count': self.execution_count}
            self.send_response(self.iopub_socket, 'execute_result', stream_content)
        if not isinstance(res, (str, dict, list, tuple)):
            self.log.info("not json serializeable?: %s", res)
            ress = str(res)
        else:
            ress = res
        if res is not None:
            stream_content = {'data': {"text/plain": ress}, 'execution_count': self.execution_count}
            self.send_response(self.iopub_socket, 'execute_result', stream_content)
        if isinstance(res, WebElement):
            imgdata = res.screenshot_as_png
        else:
            imgdata = self.drv.saveshot()
        img = Image.open(io.BytesIO(imgdata))
        if self.thumbnail is not None:
            olen = len(imgdata)
            img.thumbnail(self.thumbnail, Image.ANTIALIAS)
            buf = io.BytesIO()
            img.save(buf, format="png")
            imgdata = buf.getvalue()
            self.log.info("datasize: %d -> %d", olen, len(imgdata))
        imgdict = {
            "data": {
                "image/png": base64.b64encode(imgdata).decode("ascii"),
            },
            "metadata": {
                "image/png": {
                    "width": img.size[0],
                    "height": img.size[1],
                }
            }
        }
        self.send_response(self.iopub_socket, 'display_data', imgdict)
        self.log.info("image: %s", img.size)
        return {'status': 'ok', 'execution_count': self.execution_count}


def main():
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=SelenibleKernel)


if __name__ == '__main__':
    main()
