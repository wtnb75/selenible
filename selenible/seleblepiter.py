import io
import base64
import yaml
from PIL import Image
from logging import getLogger, DEBUG
from ipykernel.kernelbase import Kernel
from .version import VERSION
from . import drivers
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        def_modules = ["ctrl", "browser", "content", "imageproc"]
        for i in def_modules:
            drivers.Base.load_modules(i)
        self.drv = drivers.Phantom()
        self.log.setLevel(DEBUG)
        self.log.info("kernel started")

    def __del__(self):
        self.log.info("kernel finished?")
        del self.drv

    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        v = yaml.load(code)
        self.log.info("yaml: %s", v)
        if not silent:
            stream_content = {'name': 'stdout', 'text': yaml.dump(v, default_flow_style=False)}
            self.send_response(self.iopub_socket, 'stream', stream_content)
        if isinstance(v, (list, tuple)):
            res = self.drv.run(v)
        else:
            res = self.drv.run1(v)

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
            imgdata = self.drv.driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(imgdata))
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
