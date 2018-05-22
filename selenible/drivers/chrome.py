from selenium import webdriver
from . import Base


class Chrome(Base):
    def boot_driver(self):
        return webdriver.Chrome()
