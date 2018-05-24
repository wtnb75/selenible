from selenium import webdriver
from selenium.webdriver.opera.options import Options
from . import Base


class Opera(Base):
    def get_options(self):
        return Options()

    def boot_driver(self):
        return webdriver.Opera(**self.browser_args)
