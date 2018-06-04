import json
import yaml
import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from selenible import cli


class TestBase(unittest.TestCase):
    def setUp(self):
        pass

    def test_load(self):
        for drv in ["dummy", "phantom", "chrome", "firefox"]:
            cls = cli.loadmodules(drv, [])
            self.assertEqual(cls.__name__.lower(), drv)
            mods = cls.listmodule()
            self.assertTrue("echo" in mods)
            self.assertTrue("invalid" not in mods)
        for drv in ["illegal", "hello", "world"]:
            cls = cli.loadmodules(drv, [])
            # default is "Phantom"
            self.assertEqual(cls.__name__, "Phantom")

    def test_unknown(self):
        cls = cli.loadmodules("dummy", [])
        drv = cls()
        with self.assertRaisesRegex(Exception, "module not found"):
            drv.run1({"hello": "world"})
        with self.assertRaises(AttributeError):
            drv.run1("hello world")
        with self.assertRaises(TypeError):
            drv.run1(["hello", "world"])
        with self.assertRaises(TypeError):
            drv.run1([1, 2, 3])

    def test_listmodule(self):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["list-modules", "--pattern", "echo"])
        self.assertNotEqual(result.output.find("echo"), -1)
        self.assertEqual(result.exit_code, 0)

    def test_dumpschema(self):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["dump-schema", "--format", "yaml"])
        scm = yaml.load(result.output)
        self.assertEqual(scm.get("$schema", None), "http://json-schema.org/draft-04/schema")
        result = runner.invoke(cli.cli, ["dump-schema", "--format", "json"])
        scm = json.loads(result.output)
        self.assertEqual(scm.get("$schema", None), "http://json-schema.org/draft-04/schema")
        result = runner.invoke(cli.cli, ["dump-schema", "--format", "python"])
        scm = eval(result.output)
        self.assertEqual(scm.get("$schema", None), "http://json-schema.org/draft-04/schema")
        result = runner.invoke(cli.cli, ["dump-schema", "--format", "pprint"])
        scm = eval(result.output)
        self.assertEqual(scm.get("$schema", None), "http://json-schema.org/draft-04/schema")

        result = runner.invoke(cli.cli, ["dump-schema", "--format", "badformat"])
        self.assertRegex(result.output, "invalid choice")

    def test_dummyoptions(self):
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--quiet", "browser-options", "--driver", "dummy"])
        data = yaml.load(result.output)
        self.assertIn("browser_setting", data)
        self.assertIn("dummyparam", data.get("browser_setting", {}))
        result = runner.invoke(cli.cli, ["--quiet", "browser-options",
                                         "--driver", "dummy", "--mode", "doc"])
        self.assertRegex(result.output, "initialize dummy")

    def test_renderdict(self):
        cls = cli.loadmodules("dummy", [])
        drv = cls()
        drv.variables["hello"] = "world"
        data = drv.render_dict({"test": "replace string {{hello}}",
                                "test2": ["{{hello}}", "world"]})
        self.assertIn("test", data)
        self.assertEqual(data["test"], "replace string world")
        self.assertIn("test2", data)
        self.assertEqual(data["test2"], ["world", "world"])

    def test_getlocator(self):
        cls = cli.loadmodules("dummy", [])
        drv = cls()
        param = {
            "id": "id1"
        }
        res = drv.getlocator(param)
        self.assertEqual(res[0], "id")
        self.assertEqual(res[1], "id1")
        param = {
            "name": "name1"
        }
        res = drv.getlocator(param)
        self.assertEqual(res[0], "name")
        self.assertEqual(res[1], "name1")
        param = {
            "link_text": "ltxt1"
        }
        res = drv.getlocator(param)
        self.assertEqual(res[0], "link text")
        self.assertEqual(res[1], "ltxt1")
        param = {
            "tag": "tag1"
        }
        res = drv.getlocator(param)
        self.assertEqual(res[0], "tag name")
        self.assertEqual(res[1], "tag1")

    def test_findone(self):
        cls = cli.loadmodules("dummy", [])
        drv = cls()
        drv.driver.find_element = MagicMock()
        param = {
            "link_text": "ltxt1"
        }
        res = drv.findone(param)
        drv.driver.find_element.assert_called_once()
