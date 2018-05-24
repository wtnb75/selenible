from selenium import webdriver
from . import Base


class Ie(Base):
    def boot_driver(self):
        return webdriver.Ie()
