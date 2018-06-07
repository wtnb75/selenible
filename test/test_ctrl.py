import io
import time
import json
import yaml
import toml
import unittest
from unittest.mock import patch, MagicMock
from selenible import cli


class TestCtrl(unittest.TestCase):
    def dotest(self, param, expected=None, **kwargs):
        cls = cli.loadmodules("dummy", [])
        drv = cls()
        import logging
        drv.log.setLevel(logging.ERROR+10)  # suppress logging
        if isinstance(param, str):
            param = yaml.load(param)
        if isinstance(param, dict):
            res = drv.run([param])
        if isinstance(param, str):
            res = drv.run([{param: None}])
        if isinstance(param, (list, tuple)):
            res = drv.run(param)
        self.assertEqual(res, expected)
        for k, v in kwargs.items():
            self.assertEqual(drv.variables.get(k), v)

    def test_progn(self):
        self.dotest("""
        - progn:
          - echo: hello world
          - echo: hello
        """, "hello")

    def test_var(self):
        self.dotest("""
        - var:
            key1: value1
            key2:
             - value2.1
             - value2.2
        - var:
            key1: value1.1
        """, key1="value1.1")

    def test_var_if_not(self):
        self.dotest("""
        - var_if_not:
            key1: value1
            key2:
             - value2.1
             - value2.2
        - var_if_not:
            key1: value1.1
        """, key1="value1")

    def test_var_from(self):
        data = {"a": "hello", "b": "world"}
        mock = MagicMock(return_value=io.StringIO(yaml.dump(data)))
        with patch('builtins.open', mock):
            self.dotest("""
            - var_from: {yaml: test.yml}
            """, a="hello", b="world")
        mock = MagicMock(return_value=io.StringIO(json.dumps(data)))
        with patch('builtins.open', mock):
            self.dotest("""
            - var_from: {json: test.json}
            """, a="hello", b="world")
        mock = MagicMock(return_value=io.StringIO(toml.dumps(data)))
        with patch('builtins.open', mock):
            self.dotest("""
            - var_from: {toml: test.toml}
            """, a="hello", b="world")

    def test_var_from_if_not(self):
        data = {"a": "hello", "b": "world"}
        mock = MagicMock(return_value=io.StringIO(yaml.dump(data)))
        with patch('builtins.open', mock):
            self.dotest("""
            - var:
                a: help
            - var_from_if_not: {yaml: test.yml}
            """, a="help", b="world")
        mock = MagicMock(return_value=io.StringIO(json.dumps(data)))
        with patch('builtins.open', mock):
            self.dotest("""
            - var:
                a: help
            - var_from_if_not: {json: test.json}
            """, a="help", b="world")
        mock = MagicMock(return_value=io.StringIO(toml.dumps(data)))
        with patch('builtins.open', mock):
            self.dotest("""
            - var:
                a: help
            - var_from_if_not: {toml: test.toml}
            """, a="help", b="world")

    def test_echo(self):
        self.dotest("""
        - name: debug message
          echo: hello
        """, "hello")
        self.dotest("""
        - name: debug message
          echo:
            text: hello
        """, "hello")
        self.dotest("""
        - name: debug message
          echo: hello
          register: v
        """, "hello", v="hello")

    def test_runcmd(self):
        self.dotest("""
        - runcmd: echo hello
        """, "hello\n")
        self.dotest("""
        - runcmd:
            cmd: echo hello
            stdin: wow
        """, "hello\n")
        self.dotest("""
        - runcmd:
            cmd: echo hello
        """, "hello\n")
        self.dotest("""
        - runcmd:
            cmd: echo hello
            stderr: /dev/null
            stdout: /dev/null
        """, "hello\n")

    def test_runcmd_error(self):
        with self.assertRaisesRegex(Exception, "not supported"):
            self.dotest("""
            - runcmd: true
            """)
        with self.assertRaisesRegex(Exception, "missing cmd"):
            self.dotest("""
            - runcmd: {}
            """)

    def test_sleep(self):
        st = time.time()
        self.dotest("""
        - sleep: 1.0
        """)
        en = time.time()
        self.assertLessEqual(st + 1.0, en)

    def test_assert(self):
        self.dotest("""
        - assert:
            neq:
              - hello
              - world
        """)
        with self.assertRaisesRegex(Exception, "condition failed"):
            self.dotest("""
            - assert:
                eq:
                  - hello
                  - world
            """)

    def test_assert_not(self):
        self.dotest("""
        - assert_not:
            eq:
              - hello
              - world
        """)
        with self.assertRaisesRegex(Exception, "condition\\(not\\) failed"):
            self.dotest("""
            - assert_not:
                neq:
                  - hello
                  - world
            """)

    def test_set(self):
        self.dotest("""
        - set:
            text: hello
        """, "hello")
        self.dotest("""
        - set:
            text: hello
          register: v1
        """, "hello", v1="hello")
