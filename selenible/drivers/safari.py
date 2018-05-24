from selenium import webdriver
from . import Base


class Safari(Base):
    def boot_driver(self):
        return webdriver.Safari(**self.browser_args)
