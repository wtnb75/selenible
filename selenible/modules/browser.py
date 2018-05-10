import math
import time
import urllib.parse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.select import Select


def Base_open(self, param):
    """
    - name: open google
      open: https://www.google.com
    - name: open google
      open:
        url: https://www.google.com/search
        query:
          q: keyword1
    """
    self.log.debug("open %s", param)
    if isinstance(param, str):
        self.driver.get(param)
    elif isinstance(param, dict):
        url = param.get("url", None)
        if url is None:
            raise Exception("cannot find open.url: %s" % (param))
        query = param.get("query", {})
        qstr = urllib.parse.urlencode(query)
        if qstr != "":
            url += "?"
            url += qstr
        self.driver.get(url)


def Base_screenshot(self, param):
    """
    - name: take screenshot 1
      screenshot: shot1.png
    - name: take screenshot 2
      screenshot:
        output: shot2.png
        optimize: true
        archive: images.tar
        crop: auto
        resize: [800, 600]
    """
    self.log.debug("screenshot %s", param)
    if isinstance(param, str):
        self.saveshot(param)
    elif isinstance(param, dict):
        output = param.get("output")
        if output is None:
            # generate filename
            ts = time.time()
            msec = math.modf(ts)[0] * 1000
            output = param.get("prefix", "")
            output += time.strftime("%Y%m%d_%H%M%S", time.localtime(ts))
            output += "_%03d.png" % (msec)
            self.log.debug("filename generated %s", output)
        self.saveshot(output)
        elem = self.findone(param)
        if elem is not None:
            x1 = elem.location['x']
            y1 = elem.location['y']
            x2 = x1 + elem.size['width']
            y2 = y1 + elem.size['height']
            self.cropimg(output, (x1, y1, x2, y2))
        if param.get("crop", None) is not None:
            self.cropimg(output, param.get("crop"))
        if param.get("resize", None) is not None:
            self.resizeimg(output, param.get("resize"))
        if param.get("optimize", False):
            self.optimizeimg(output)
        if param.get("archive", False):
            self.archiveimg(output, param.get("archive"))


def Base_click(self, param):
    """
    - name: click1
      click:
        id: elementid1
    - name: click2
      click:
        xpath: //div[1]
    """
    self.findmany2one(param).click()


def Base_submit(self, param):
    """
    - name: submit element
      submit:
        id: elementid1
    """
    self.findmany2one(param).submit()


def Base_waitfor(self, param):
    waiter = WebDriverWait(self.driver, param.get("timeout", 10))
    simple_fn = [
        "title_is", "title_contains", "url_changes", "url_contains", "url_matches",
        "url_to_be", "number_of_windows_to_be",
    ]
    if "alert_is_present" in param:
        return waiter.until(expected_conditions.alert_is_present())
    for f in simple_fn:
        if f in param:
            return waiter.until(getattr(expected_conditions, f)(param.get(f)))
    locator_fn = [
        "element_located_to_be_selected", "element_to_be_clickable",
        "frame_to_be_available_and_switch_to_it",
        "invisibility_of_element_located", "presence_of_all_elements_located",
        "presence_of_element_located", "visibility_of_all_elements_located",
        "visibility_of_any_elements_located", "visibility_of_element_located"
    ]
    for f in locator_fn:
        if f in param:
            loc = self.getlocator(param)
            if len(loc) != 2 or loc[0] is None:
                raise Exception("locator not set: %s" % (param))
            return waiter.until(getattr(expected_conditions, f)(loc))
    locator_and_fn = {
        "text_to_be_present_in_element": None,
        "text_to_be_present_in_element_value": None,
        "element_located_selection_state_to_be": "selected",
    }
    for f, v in locator_and_fn.items():
        if f in param:
            if v is None:
                arg = self.getvalue(param)
            else:
                arg = param.get(v)
            if arg is None:
                raise Exception("missing argument %s: param=%s" % (v, param))
            loc = self.getlocator(param)
            if len(loc) != 2 or loc[0] is None:
                raise Exception("locator not set: %s" % (param))
            return waiter.until(getattr(expected_conditions, f)(loc, arg))
    # other conditions:
    #  element_selection_state_to_be, element_to_be_selected,
    #  new_window_is_opened, staleness_of, visibility_of
    raise Exception("not implemented: param=%s" % (param))


def Base_script(self, param):
    """
    - name: execute js
      script: 'alert("hello")'
    """
    if isinstance(param, (list, tuple)):
        for s in param:
            self.driver.execute_script(s)
    elif isinstance(param, str):
        self.driver.execute_script(param)
    elif isinstance(param, dict):
        fname = param.get("file", None)
        if fname is None:
            raise Exception("no file")
        with open(fname) as f:
            self.driver.execute_script(f.read())
    else:
        raise Exception("parameter error: %s" % (param))


def Base_history(self, param):
    """
    - name: back
      history: [back, fwd, back, refresh]
    """
    fwd = ("forward", "fwd", "f")
    back = ("backward", "back", "b")
    refresh = ("refresh", "reload", "r")
    if isinstance(param, (tuple, list)):
        for d in param:
            if d in fwd:
                self.driver.forward()
            elif d in back:
                self.driver.back()
            else:
                raise Exception("no such direction: %s" % (d))
    elif isinstance(param, str):
        if param in fwd:
            self.driver.forward()
        elif param in back:
            self.driver.back()
        elif param in refresh:
            self.driver.refresh()
        else:
            raise Exception("no such direction: %s" % (param))
    else:
        raise Exception("history: not supported direction: %s" % (param))


def Base_sendKeys(self, param):
    """
    - name: input username
      sendKeys:
        text: user1
        id: elementid1
    - name: input password
      sendKeys:
        password: site/password
        # get text from $(pass site/password)
        id: elementid2
    """
    clear = param.get("clear", False)
    txt = self.getvalue(param)
    if txt is None:
        raise Exception("text not set: param=%s" % (param))
    elem = self.findmany2one(param)
    if clear:
        elem.clear()
    elem.send_keys(txt)
    return self.return_element(param, elem)


def Base_save(self, param):
    """
    - name: save page title
      save:
        mode: title
        output: title.txt
    - name: save page content
      save:
        mode: source
        id: element1
    - name: copy page content to variable
      save:
        mode: text
        id: element2
      register: title1
    """
    mode = param.get("mode", "source")
    locator = self.getlocator(param)
    if mode == "source":
        if locator[0] is None:
            txt = [self.driver.page_source]
        else:
            txt = []
            for p in self.findmany(param):
                txt.append(p.get_attribute("innerHTML"))
    elif mode == "source_outer":
        if locator[0] is None:
            txt = [self.driver.page_source]
        else:
            txt = []
            for p in self.findmany(param):
                txt.append(p.get_attribute("outerHTML"))
    elif mode == "title":
        txt = [self.driver.title]
    elif mode == "text":
        if locator[0] is None:
            txt = [self.driver.find_element_by_xpath("/html").text]
        else:
            txt = []
            for p in self.findmany(param):
                txt.append(p.text)
    output = param.get("output", None)
    if output is not None:
        with open(output, "w") as f:
            f.write("\n".join(txt))
    return txt


def Base_dragdrop(self, param):
    """
    - name: drag and drop
      dragdrop:
        src:
          xpath: //div[1]
        dst:
          select: "$.x.y.z"
    """
    src = self.findmany2one(param.get("src"))
    dst = self.findmany2one(param.get("dst"))
    ActionChains(self.driver).drag_and_drop(src, dst).perform()


def Base_switch(self, param):
    """
    - name: switch window
      switch:
        window: win1
    - name: switch frame
      switch:
        frame: frm1
    - name: switch to default window
      switch: default
    """
    if "window" in param:
        self.driver.switch_to_window(param.get("window"))
    elif "frame" in param:
        self.driver.switch_to_frame(param.get("frame"))
    elif param in ("default", None, {}):
        self.driver.switch_to_default_content()


def Base_dropfile(self, param):
    """
    - name: drop file
      dropfile:
        filename: /path/to/file
        id: element1
    """
    raise Exception("not implemented yet")


def Base_deletecookie(self, param):
    """
    - name: delete all cookie
      deletecookie: all
    - name: clear cookie a, b, c
      deletecookie: [a, b, c]
    """
    if param == "all":
        self.driver.delete_all_cookies()
    elif isinstance(param, (tuple, list)):
        for c in param:
            self.driver.delete_cookie(c)
    elif isinstance(param, str):
        self.driver.delete_cookie(param)
    else:
        raise Exception("invalid argument")


def Base_alertOK(self, param):
    """
    - name: accept alert
      alertOK: true
    - name: cancel alert
      alertOK: false
    """
    if isinstance(param, bool):
        if param:
            Alert(self.driver).accept()
        else:
            Alert(self.driver).dismiss()


def Base_auth(self, param):
    """
    - name: basic/digest auth
      auth:
        username: user1
        password: password1
    """
    user = param.get("username", "")
    passwd = param.get("password", "")
    Alert(self.driver).authenticate(user, passwd)


def Base_select(self, param):
    """
    - name: select 1st
      select:
        id: element1
        by_index: 1
    - name: select by value
      select:
        id: element1
        by_value: value1
    - name: select by visible text
      select:
        id: element1
        by_text: "text 1"
    """
    elem = self.findone(param)
    if elem is None:
        raise Exception("element not found: %s" % (param))
    flag = param.get("deselect", False)
    sel = Select(elem)
    if "by_index" in param:
        if flag:
            sel.deselect_by_index(param.get("by_index"))
        else:
            sel.select_by_index(param.get("by_index"))
    elif "by_value" in param:
        if flag:
            sel.deselect_by_value(param.get("by_value"))
        else:
            sel.select_by_value(param.get("by_value"))
    elif "by_text" in param:
        if flag:
            sel.deselect_by_visible_text(param.get("by_text"))
        else:
            sel.select_by_visible_text(param.get("by_text"))
    elif param.get("all", False):
        if flag:
            sel.deselect_all()
        else:
            sel.select_all()
    retp = param.get("return", "selected")
    if retp == "selected":
        res = sel.all_selected_options
    elif retp == "first":
        res = sel.first_selected_option
    elif retp == "all":
        res = sel.options
    else:
        return
    return self.return_element(param, res)
