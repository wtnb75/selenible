from selenium import webdriver
from . import Base


class Remote(Base):
    def boot_driver(self):
        return webdriver.Remote(**self.browser_args)
