# selenible

do selenium like ansible

## requirements

- python3
- selenium webdriver
    - phantomjs
    - chrome
    - firefox
    - etc...

## try

- git clone https://github.com/wtnb75/selenible.git
- cd selenible
- pip install -r requirements.txt

```
Usage: base.py [OPTIONS] COMMAND [ARGS]...

Options:
  --version          Show the version and exit.
  --verbose
  --quiet, --silent
  --help             Show this message and exit.

Commands:
  dump-schema   dump json schema
  list-modules  list modules
  run           run playbook
  validate      validate by json schema
```

```
# python -m selenible.base list-modules
+--------------+---------------------------------------------------------------+
|    Module    |                          Description                          |
+==============+===============================================================+
| alertOK      | - name: accept alert                                          |
|              |   alertOK: true                                               |
|              | - name: cancel alert                                          |
|              |   alertOK: false                                              |
+--------------+---------------------------------------------------------------+
| auth         | - name: basic/digest auth                                     |
|              |   auth:                                                       |
|              |     username: user1                                           |
|              |     password: password1                                       |
+--------------+---------------------------------------------------------------+
| click        | - name: click1                                                |
|              |   click:                                                      |
|              |     id: elementid1                                            |
|              | - name: click2                                                |
|              |   click:                                                      |
|              |     xpath: //div[1]                                           |
+--------------+---------------------------------------------------------------+
| config       | - name: config phantomjs                                      |
   :
```

## install

- pip install -e 'git+https://github.com/wtnb75/selenible.git#egg=selenible'
- selenible --help
- ...

### (uninstall)

- pip uninstall selenible -y

## examples

```yaml
- name: open url
  open: https://www.google.com
- name: screenshot
  screenshot: output.png
```

and [more examples](example/)...
