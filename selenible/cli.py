import sys
import os
import pprint
import inspect
from logging import getLogger, DEBUG, INFO, WARN, captureWarnings
from logging import FileHandler, StreamHandler, Formatter

import json
import yaml
import click
import jsonschema
from .version import VERSION
from .drivers import Base, Phantom, Chrome, Firefox, Safari, Edge
from .drivers import WebKitGTK, Dummy, Ie, Opera, Android, Remote

drvmap = {
    "phantom": Phantom,
    "chrome": Chrome,
    "firefox": Firefox,
    "safari": Safari,
    "edge": Edge,
    "webkit": WebKitGTK,
    "dummy": Dummy,
    "ie": Ie,
    "opera": Opera,
    "android": Android,
    "remote": Remote,
}


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=VERSION, prog_name="selenible")
@click.option("--verbose", is_flag=True)
@click.option("--quiet", is_flag=True)
@click.option("--logfile", type=click.Path())
def cli(ctx, verbose, quiet, logfile):
    logfmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    fmt = Formatter(fmt=logfmt)
    lg = getLogger()
    if verbose:
        lg.setLevel(DEBUG)
    elif quiet:
        lg.setLevel(WARN)
    else:
        lg.setLevel(INFO)
    if logfile is not None:
        newhdl = FileHandler(logfile)
        newhdl.setFormatter(fmt)
        lg.addHandler(newhdl)
    else:
        newhdl = StreamHandler()
        newhdl.setFormatter(fmt)
        lg.addHandler(newhdl)
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


def loadmodules(driver, extension):
    def_modules = ["ctrl", "browser", "content", "imageproc"]
    for i in def_modules:
        Base.load_modules(i)
    for ext in extension:
        Base.load_modules(ext)
    drvcls = drvmap.get(driver, Phantom)
    drvcls.load_modules(drvcls.__name__.lower())
    for ext in extension:
        drvcls.load_modules(ext)
    return drvcls


@cli.command(help="run playbook")
@click.option("--driver", default="phantom", type=click.Choice(drvmap.keys()))
@click.option("--extension", "-x", multiple=True)
@click.option("--step", is_flag=True, default=False)
@click.option("--screenshot", is_flag=True, default=False)
@click.option("-e", multiple=True)
@click.option("--var", type=click.File('r'), required=False)
@click.argument("input", type=click.File('r'), required=False)
def run(input, driver, step, screenshot, var, e, extension):
    captureWarnings(True)
    drvcls = loadmodules(driver, extension)
    if input is not None:
        prog = yaml.load(input)
        b = drvcls()
        for k, v in os.environ.items():
            b.variables[k] = v
        if var is not None:
            b.load_vars(var)
        for x in e:
            if x.find("=") == -1:
                b.variables[k] = True
            else:
                k, v = x.split("=", 1)
                try:
                    b.variables[k] = json.loads(v)
                except Exception:
                    b.variables[k] = v
        b.step = step
        b.save_every = screenshot
        b.run(prog)
    else:
        click.echo("show usage: --help")


@cli.command("list-modules", help="list modules")
@click.option("--driver", default="phantom", type=click.Choice(drvmap.keys()))
@click.option("--extension", "-x", multiple=True)
@click.option("--pattern", default=None)
def list_modules(driver, extension, pattern):
    drvcls = loadmodules(driver, extension)
    from texttable import Texttable
    table = Texttable()
    table.set_cols_align(["l", "l"])
    # table.set_deco(Texttable.HEADER)
    table.header(["Module", "Description"])
    mods = drvcls.listmodule()
    for k in sorted(mods.keys()):
        if pattern is not None and k.find(pattern) == -1:
            continue
        table.add_row([k, mods[k]])
    print(table.draw())


@cli.command("dump-schema", help="dump json schema")
@click.option("--driver", default="phantom", type=click.Choice(drvmap.keys()))
@click.option("--extension", "-x", multiple=True)
@click.option("--format", default="yaml", type=click.Choice(["yaml", "json", "python", "pprint"]))
def dump_schema(driver, extension, format):
    drvcls = loadmodules(driver, extension)
    if format == "yaml":
        yaml.dump(drvcls.schema, sys.stdout, default_flow_style=False)
    elif format == "json":
        json.dump(drvcls.schema, fp=sys.stdout, ensure_ascii=False)
    elif format == "python":
        print(drvcls.schema)
    elif format == "pprint":
        pprint.pprint(drvcls.schema)
    else:
        raise Exception("unknown format: %s" % (format))


@cli.command(help="validate by json schema")
@click.option("--driver", default="phantom", type=click.Choice(drvmap.keys()))
@click.option("--extension", "-x", multiple=True)
@click.argument("input", type=click.File('r'), required=False)
def validate(driver, extension, input):
    drvcls = loadmodules(driver, extension)
    prog = yaml.load(input)
    try:
        click.echo("validating...", nl=False)
        jsonschema.validate(prog, drvcls.schema)
        click.echo("OK")
        sys.exit(0)
    except jsonschema.exceptions.ValidationError as e:
        click.echo("failed")
        click.echo(e)
    sys.exit(1)


@cli.command("browser-options", help="show browser options")
@click.option("--driver", default="phantom", type=click.Choice(drvmap.keys()))
@click.option("--mode", default="example", type=click.Choice(["example", "doc"]))
def browser_options(driver, mode):
    drvcls = loadmodules(driver, [])
    drv = drvcls()
    if mode == "doc":
        print(inspect.getdoc(drv.driver.__init__))
        return
    opts = drv.get_options()
    sig = inspect.signature(drv.driver.__init__)
    res = {}
    for k, v in sig.parameters.items():
        res[k] = v.default
    if opts != {}:
        res["options"] = {}
        for f in dir(opts):
            if f.startswith("__") or f.endswith("__"):
                continue
            if callable(getattr(opts, f)):
                s2 = inspect.signature(getattr(opts, f))
                res["options"][f] = [str(x) for x in s2.parameters.values()]
    yaml.dump({"browser_setting": res}, sys.stdout, default_flow_style=False)


if __name__ == "__main__":
    cli()
