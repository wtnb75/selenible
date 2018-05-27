import click
import yaml
import json
from jinja2 import Environment
from .cli import cli, drvmap, loadmodules


def yamlify(data):
    return yaml.dump(data, default_flow_style=False)


@cli.command()
@click.option("--driver", default="dummy", type=click.Choice(drvmap.keys()))
@click.option("--extension", "-x", multiple=True)
@click.option("--docdata", type=click.File('r'))
def docdata(driver, extension, docdata):
    drvcls = loadmodules(driver, extension)
    def_text = "(description write here)\n"
    result = {}
    if docdata is not None:
        result = yaml.load(docdata)
    mods = drvcls.listmodule()
    for k in sorted(mods.keys()):
        print("%s: |" % (k))
        txt = result.get(k, def_text)
        print("  " + "\n  ".join(txt.split("\n")))


@cli.command()
@click.option("--driver", default="dummy", type=click.Choice(drvmap.keys()))
@click.option("--extension", "-x", multiple=True)
@click.option("--name", default="echo")
@click.option("--docdata", type=click.File('r'), required=True)
@click.option("--longdoc", type=click.File('r'))
@click.option("--template", required=True)
def show(driver, extension, name, template, docdata, longdoc):
    drvcls = loadmodules(driver, extension)
    mods = drvcls.listmodule()
    arg = {
        "name": name,
        "example": mods.get(name),
        "schema": drvcls.schema.get("items", {}).get("properties", {}).get(name, None),
        "description": yaml.load(docdata).get(name),
    }
    if longdoc is not None:
        arg["long_description"] = longdoc.read()
    env = Environment()
    env.filters['jsonify'] = json.dumps
    env.filters['yamlify'] = yamlify
    with open(template) as tmpl:
        print(env.from_string(tmpl.read()).render(arg))


@cli.command("list-missing-schema", help="list missing json schema")
@click.option("--driver", default="dummy", type=click.Choice(drvmap.keys()))
@click.option("--extension", "-x", multiple=True)
def list_missing_schema(driver, extension):
    drvcls = loadmodules(driver, extension)
    props = drvcls.schema.get("items", {}).get("properties", {})
    mods = drvcls.listmodule()
    ignore = ["name", "register", "when", "when_not", "with_items", "loop_control"]
    for k in sorted(mods.keys()):
        if k not in props:
            click.echo("missing schema: %s" % (k,))
    for k in sorted(props.keys()):
        if k in ignore:
            continue
        if k not in mods:
            click.echo("missing method: %s" % (k,))


if __name__ == "__main__":
    cli()
