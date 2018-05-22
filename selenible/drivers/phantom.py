
import os
from selenium import webdriver
from . import Base


class Phantom(Base):
    def boot_driver(self):
        return webdriver.PhantomJS()

    def saveshot(self, output_fn):
        base, ext = os.path.splitext(output_fn)
        if ext in (".pdf", ".PDF"):
            page_format = 'this.paperSize = {format: "A4", orientation: "portrait" };'
            self.execute(page_format, [])
            render = '''this.render("{}")'''.format(output_fn)
            self.execute(render, [])
        else:
            super().saveshot(output_fn)
