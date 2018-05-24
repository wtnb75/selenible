from selenium import webdriver
from selenium.webdriver.webkitgtk.options import Options
from . import Base


class WebKitGTK(Base):
    def get_options(self):
        return Options()

    def boot_driver(self):
        return webdriver.WebKitGTK(**self.browser_args)
