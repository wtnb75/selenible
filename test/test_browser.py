import os
import unittest
import tempfile
from unittest.mock import MagicMock
from selenible import cli


class TestBrowser(unittest.TestCase):
    def dummy(self):
        cls = cli.loadmodules("dummy", ["browser"])
        return cls, cls()

    def test_load(self):
        cls, drv = self.dummy()
        self.assertIsNotNone(cls)
        self.assertIsNotNone(drv)

    def test_open(self):
        _, drv = self.dummy()
        url = "https://www.google.com/"
        res = drv.do_open(url)
        self.assertEqual(res, url)
        res = drv.do_open({"url": url, "query": {"q1": "v1"}})
        self.assertEqual(res, url+"?q1=v1")

    def test_openfail(self):
        _, drv = self.dummy()
        with self.assertRaisesRegex(Exception, "cannot find"):
            res = drv.do_open({})
            self.fail(res)

    def test_screenshot(self):
        _, drv = self.dummy()
        tf = tempfile.NamedTemporaryFile(suffix=".png")
        res = drv.do_screenshot(tf.name)
        self.assertEqual(res, tf.name)
        st = os.stat(tf.name)
        self.assertNotEqual(st.st_size, 0)
        res = drv.do_screenshot({"output": tf.name})
        self.assertEqual(res, tf.name)
        st = os.stat(tf.name)
        self.assertNotEqual(st.st_size, 0)
        res = drv.do_screenshot({})
        st = os.stat(res)
        self.assertNotEqual(st.st_size, 0)
        os.unlink(res)
        drv.do_screenshot({"output": tf.name, "crop": [1, 2, 3, 4]})
        drv.do_screenshot({"output": tf.name, "resize": [10, 20]})
        drv.do_screenshot({"output": tf.name, "optimize": True})
        tfa = tempfile.NamedTemporaryFile(suffix=".tar")
        os.unlink(tfa.name)
        drv.do_screenshot({"archive": tfa.name})
        st = os.stat(tfa.name)
        self.assertNotEqual(st.st_size, 0)

    def test_click(self):
        _, drv = self.dummy()
        elem = MagicMock()
        drv.driver.find_elements = MagicMock(return_value=[elem])
        drv.do_click({"id": "element1"})
        elem.click.assert_called_once()

    def test_submit(self):
        _, drv = self.dummy()
        elem = MagicMock()
        drv.driver.find_elements = MagicMock(return_value=[elem])
        drv.do_submit({"id": "element1"})
        elem.submit.assert_called_once()

    def test_script(self):
        _, drv = self.dummy()
        drv.driver.execute_script = MagicMock()
        drv.do_script("alert();")
        drv.driver.execute_script.assert_called_once()
        drv.driver.execute_script.reset_mock()

        drv.do_script(["alert();", "alert();"])
        self.assertEqual(drv.driver.execute_script.call_count, 2)
        drv.driver.execute_script.reset_mock()

        tf = tempfile.NamedTemporaryFile()
        tf.write(b"alert();\n")
        tf.flush()
        drv.do_script({"file": tf.name})
        drv.driver.execute_script.assert_called_once()
        drv.driver.execute_script.reset_mock()

        with self.assertRaisesRegex(Exception, "no file"):
            drv.do_script({})
        drv.driver.execute_script.assert_not_called()
        drv.driver.execute_script.reset_mock()

        with self.assertRaisesRegex(Exception, "parameter"):
            drv.do_script(True)
        drv.driver.execute_script.assert_not_called()
        drv.driver.execute_script.reset_mock()

    def test_history(self):
        fwd = MagicMock()
        back = MagicMock()
        reload = MagicMock()
        _, drv = self.dummy()
        drv.driver.forward = fwd
        drv.driver.back = back
        drv.driver.refresh = reload
        drv.do_history(["b", "back", "backward", "r", "f", "forward"])
        self.assertEqual(back.call_count, 3)
        self.assertEqual(fwd.call_count, 2)
        self.assertEqual(reload.call_count, 1)

        fwd.reset_mock()
        back.reset_mock()
        reload.reset_mock()
        drv.do_history("back")
        fwd.assert_not_called()
        back.assert_called_once()
        reload.assert_not_called()
        drv.do_history("fwd")
        fwd.assert_called_once()
        back.assert_called_once()
        reload.assert_not_called()
        drv.do_history("refresh")
        fwd.assert_called_once()
        back.assert_called_once()
        reload.assert_called_once()

    def test_sendkeys(self):
        _, drv = self.dummy()
        elem = MagicMock()
        m2o = MagicMock(return_value=elem)
        drv.findmany2one = m2o
        drv.do_sendKeys({"id": "xxxx", "text": "hello world"})
        m2o.assert_called_once()
        elem.send_keys.assert_called_once_with("hello world")
        elem.clear.assert_not_called()

        with self.assertRaisesRegex(Exception, "not set"):
            drv.do_sendKeys({})

        m2o.reset_mock()
        elem.reset_mock()
        drv.do_sendKeys({"id": "xxxx", "text": "hello world2", "clear": True})
        elem.send_keys.assert_called_once_with("hello world2")
        elem.clear.assert_called_once()

    def test_settextvalue(self):
        _, drv = self.dummy()
        elem = "assert"
        m2o = MagicMock(return_value=elem)
        exs = MagicMock()
        drv.findmany2one = m2o
        drv.driver.execute_script = exs
        drv.do_setTextValue({"id": "xxx", "text": "hello world"})
        exs.assert_called_once_with("arguments[0].value = arguments[1];", elem, "hello world")

        with self.assertRaisesRegex(Exception, "not set"):
            drv.do_setTextValue({})

    def test_switch(self):
        _, drv = self.dummy()
        drv._driver = MagicMock()

        drv.do_switch({"window": "hello world"})
        drv.driver.switch_to_window.assert_called_once_with("hello world")
        drv.driver.reset_mock()

        drv.do_switch({"frame": "frame1"})
        drv.driver.switch_to_frame.assert_called_once_with("frame1")
        drv.driver.reset_mock()

        drv.do_switch(True)
        drv.driver.switch_to_default_content.assert_called_once()
