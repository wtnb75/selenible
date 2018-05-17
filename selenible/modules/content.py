import re
import yaml

update_style_schema = yaml.load("""
allOf:
  - type: object
  - "$ref": "#/definitions/common/locator"
""")


def Base_update_style(self, param):
    """
    - name: red background
      update_style:
        id: element1
        "background-color": red
    - name: dismiss heading
      update_style:
        tag: h1
        display: none
    """
    newstyle = self.removelocator(param)
    for elem in self.findmany(param):
        self.log.debug("update style %s <- %s", elem.id, newstyle)
        for k, v in newstyle.items():
            script = "".join([
                "arguments[0].style[", repr(k), "]=", repr(v), ";",
                "return arguments[0];"
            ])
            self.execute(script, elem)


update_content_schema = yaml.load("""
allOf:
  - type: object
    properties:
      pattern: {type: string}
      replacement: {type: string}
      regexp: {type: boolean}
      flag:
        type: string
        enum: [i, g]
  - "$ref": "#/definitions/common/locator"
""")


def Base_update_content(self, param):
    """
    - name: mask some number
      update_content:
        pattern: "[0-9]"
        replacement: "*"
        regexp: true
        id: element1
    """
    pattern = param.get("pattern")
    replacement = param.get("replacement")
    regexp = param.get("regexp", False)
    flag = param.get("flag", "g")
    if pattern is None or replacement is None:
        raise Exception("invalid parameter: %s" % (param))
    if regexp:
        # check regexp
        re.compile(pattern)
        # OK
        script = "".join([
            "arguments[0].innerHTML=arguments[0].innerHTML.replace(/",
            pattern, "/", flag, ",", repr(replacement), ");"
            "return arguments[0];"
        ])
    else:
        script = "".join([
            "arguments[0].innerHTML=arguments[0].innerHTML.replace(",
            repr(pattern), ",", repr(replacement), ");"
            "return arguments[0];"
        ])
    for elem in self.findmany(param):
        self.execute(script, elem)


update_attribute_schema = yaml.load("""
allOf:
  - "$ref": "#/definitions/common/locator"
  - type: object
    properties:
      replacement: {type: object}
""")


def Base_update_attribute(self, param):
    """
    - name: link redirection
      update_attribute:
        tag: a
        href: http://example.com/
    - name: rename
      update_attribute:
        id: element1
        replacement:
          id: new-element1
          class: null  # remove attribute
    """
    newattr = self.removelocator(param)
    if len(newattr) == 0:
        newattr = param.get("replacement", {})
    for elem in self.findmany(param):
        self.log.debug("update style %s <- %s", elem.id, newattr)
        for k, v in newattr.items():
            if v is None:
                script = "".join([
                    "arguments[0].removeAttribute(", repr(k), ");",
                    "return arguments[0];"
                ])
            else:
                script = "".join([
                    "arguments[0].setAttribute(", repr(k), ",", repr(v), ");",
                    "return arguments[0];"
                ])
            self.execute(script, elem)
