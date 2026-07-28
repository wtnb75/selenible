from selenium import webdriver

from . import Base

try:
    from selenium.webdriver.opera.options import Options
except ImportError:
    # Opera support was removed from selenium (no more selenium.webdriver.opera).
    Options = None


class Opera(Base):
    def get_options(self):
        if Options is None:
            raise Exception(
                "selenium.webdriver.opera is not available in this selenium version"
            )
        return Options()

    def boot_driver(self):
        if not hasattr(webdriver, "Opera"):
            raise Exception(
                "selenium.webdriver.Opera is not available in this selenium version"
            )
        return webdriver.Opera(**self.browser_args)
