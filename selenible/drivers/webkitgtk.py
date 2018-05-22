from selenium import webdriver
from . import Base


class WebKitGTK(Base):
    def boot_driver(self):
        return webdriver.WebKitGTK()
