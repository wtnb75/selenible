from selenium import webdriver
from . import Base


class Edge(Base):
    def boot_driver(self):
        return webdriver.Edge(**self.browser_args)
