from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from . import Base


class Firefox(Base):
    def get_options(self):
        return Options()

    def boot_driver(self):
        return webdriver.Firefox(**self.browser_args)

    def do_install_addon(self, params):
        """
        - name: install local addons
          install_addon:
            install: /path/to/addon.xpi
          register: addon_id
        - name: uninstall addon
          install_addon:
            uninstall: "{{addon_id}}"
        """
        to_uninstall = params.get("uninstall", [])
        if isinstance(to_uninstall, (tuple, list)):
            for i in to_uninstall:
                self.driver.uninstall_addon(i)
        else:
            self.driver.uninstall_addon(to_uninstall)
        to_install = params.get("install", [])
        if isinstance(to_install, (tuple, list)):
            res = []
            for i in to_install:
                res.append(self.driver.install_addon(i))
            return res
        else:
            return self.driver.install_addon(to_install)
