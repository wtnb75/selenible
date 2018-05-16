import re


def Base_update_style(self, param):
    newstyle = self.removelocator(param)
    for elem in self.findmany(param):
        self.log.debug("update style %s <- %s", elem.id, newstyle)
        for k, v in newstyle.items():
            script = "".join([
                "arguments[0].style[", repr(k), "]=", repr(v), ";",
                "return arguments[0];"
            ])
            self.execute(script, elem)


def Base_update_content(self, param):
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
