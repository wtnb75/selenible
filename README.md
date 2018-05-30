# selenible

do selenium like ansible

```yaml
# open google and take screenshot
- name: open url
  open: https://www.google.com
- name: screenshot
  screenshot: output.png
```

## requirements

- python3
- selenium webdriver
    - phantomjs
    - chrome
    - firefox
    - etc...

## install

- pip install selenible

## usage

```
# selenible
Usage: selenible [OPTIONS] COMMAND [ARGS]...

Options:
  --version       Show the version and exit.
  --verbose
  --quiet
  --logfile PATH
  --help          Show this message and exit.

Commands:
  browser-options  show browser options
  dump-schema      dump json schema
  list-modules     list modules
  run              run playbook
  validate         validate by json schema
```

```
# selenible list-modules
+------------------+-----------------------------------------------------------+
|      Module      |                        Description                        |
+==================+===========================================================+
| alertOK          | - name: accept alert                                      |
|                  |   alertOK: true                                           |
|                  | - name: cancel alert                                      |
|                  |   alertOK: false                                          |
+------------------+-----------------------------------------------------------+
| auth             | - name: basic/digest auth                                 |
|                  |   auth:                                                   |
   :
```

```
# selenible run --help
Usage: selenible run [OPTIONS] [INPUT]

  run playbook

Options:
  --driver [phantom|chrome|firefox|safari|edge|webkit|dummy|ie|opera|android|remote]
  -x, --extension TEXT
  --step
  --screenshot
  -e TEXT
  --var FILENAME
  --help                          Show this message and exit.
```

### development

- git clone https://github.com/wtnb75/selenible.git
- cd selenible
- pip install -r requirements.txt

```
# python -m selenible.cli
Usage: cli.py [OPTIONS] COMMAND [ARGS]...

  :

# python -m selenible.cli list-modules
+--------------+---------------------------------------------------------------+
|    Module    |                          Description                          |
+==============+===============================================================+
| alertOK      | - name: accept alert                                          |
|              |   alertOK: true                                               |
|              | - name: cancel alert                                          |
   :
```

### install HEAD

- pip install -e 'git+https://github.com/wtnb75/selenible.git#egg=selenible'
- selenible --help
- ...

### (uninstall)

- pip uninstall selenible -y

## examples

```yaml
# input text into translate service and get new text
- name: get text
  set:
    input_multiline: "input(ctrl-d): "
  register: src
  when_not:
    defined: src
- name: open google translate
  open: https://translate.google.com/
- name: set input
  setTextValue:
    text: "{{src}}"
    id: source
- name: sleep
  sleep: 3
- name: get output
  save:
    mode: text
    id: result_box
  register: dst
- name: result
  echo: "{{dst}}"
```

and [more examples](example/)...

# work with jupyter notebook

## install kernel

- jupyter kernelspec install --user seleniblepiter

## examples

- [helloworld](example/helloworld.ipynb)
