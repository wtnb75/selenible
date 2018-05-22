from selenium import webdriver
from . import Base


class Firefox(Base):
    def boot_driver(self):
        return webdriver.Firefox()
