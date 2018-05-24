from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from . import Base


class Chrome(Base):
    def get_options(self):
        return Options()

    def boot_driver(self):
        self.log.debug("chrome: %s", self.browser_args)
        return webdriver.Chrome(**self.browser_args)

    def do_network_conditions(self, params):
        """
        - name: network emulation settings
          network_conditions:
            latency: 4
            download_throughput: 2
            upload_throughput: 1
            offline: false
        """
        prep = self.driver.get_network_conditions()
        self.log.info("network emulation settings: %s -> %s", prep, params)
        self.driver.set_network_conditions(**params)
