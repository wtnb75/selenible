from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from . import Base


class Firefox(Base):
    def get_options(self):
        return Options()

    def boot_driver(self):
        return webdriver.Firefox(**self.browser_args)
