from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from . import Base


class Chrome(Base):
    def get_options(self):
        return Options()

    def boot_driver(self):
        return webdriver.Chrome(**self.browser_args)
