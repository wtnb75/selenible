from selenium import webdriver

from . import Base


class Android(Base):
    def boot_driver(self):
        if not hasattr(webdriver, "Android"):
            raise Exception(
                "selenium.webdriver.Android is not available in this selenium version"
            )
        return webdriver.Android(**self.browser_args)
