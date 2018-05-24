from selenium import webdriver
from . import Base


class Opera(Base):
    def boot_driver(self):
        return webdriver.Opera()
