from selenium import webdriver
from selenium.webdriver.ie.options import Options
from . import Base


class Ie(Base):
    def get_options(self):
        return Options()

    def boot_driver(self):
        return webdriver.Ie(**self.browser_args)
