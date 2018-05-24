from selenium import webdriver
from . import Base


class Android(Base):
    def boot_driver(self):
        return webdriver.Android(**self.browser_args)
