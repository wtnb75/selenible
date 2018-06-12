import os
import unittest
import tempfile
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
