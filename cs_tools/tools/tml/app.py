# DEV NOTE:
#

import pathlib

import yaml
from typer import Argument as A_, Option as O_  # noqa
import typer
from typing import List

from cs_tools import util
from cs_tools._enums import TMLImportPolicy, TMLType
from cs_tools.helpers.cli_ux import _csv, console, CSToolsCommand, CSToolsGroup, frontend
from cs_tools.settings import TSConfig
from cs_tools.thoughtspot import ThoughtSpot


def strip_blanks(list: List[str]) -> List[str]:
    return [l for l in list if l]


app = typer.Typer(
    help="""
    Tool for easily migrating TML between clusters.

    ThoughtSpot provides the ability to extract object metadata (tables, worksheets, liveboards, etc.) 
    in ThoughtSpot Modeling Language (TML) format, which is a text format based on YAML.  These files 
    can be modified and uploaded into another instance. These files can then be modified and imported 
    into another (or the same) instance to either create or modify objects.

      cs_tools tools tml-migration --help
    
    \f
    TODO - add more details on using the tools and a workflow.
    
    DEV NOTE:

      Two control characters are offered in order to help with
      docstrings in typer App helptext and command helptext
      (docstrings).

      \b - Preserve Whitespace / formatting.
      \f - EOF, don't include anything after this character in helptext.
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@frontend
def export(
        tags: List[str] = O_([], metavar='TAGS',
                             callback=_csv,
                             help='list of tags to export for'),
        export_ids: List[str] = O_([], metavar='GUIDS',
                                    callback=_csv,
                                    help='list of guids to export'),
        format_type: TMLType = O_(TMLType.yaml.value,
                                  help=f'if specified, format to export, either {TMLType.yaml.value} or {TMLType.json.value}'),
        export_associated: bool = O_(False,
                                     help='if specified, also export related content'),
        path: pathlib.Path = O_(  # may not want to use
            None,
            help='full path (directory) to save data set to',
            metavar='DIR',
            dir_okay=True,
            resolve_path=True
        ),
        **frontend_kw
) -> None:
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    export_ids = strip_blanks(export_ids)
    tags = strip_blanks(tags)

    # Options:
    #    guids, no associated
    #    guids, associated
    #    tag, associated
    #    tag, not associated
    # if associated - get all the guids, then get the mapping of types, then call to use edoc
    # if not associated - get all the guids, then call export

    with ThoughtSpot(cfg) as ts:
        if tags:
            export_ids.extend(ts.metadata.get_object_ids_with_tags(tags))

        if not export_associated:
            with console.status(f"[bold green]exporting ${export_ids} without associated content.[/]"):
                r = ts.api.metadata.tml_export(export_ids=export_ids,
                                               format_type=format_type,
                                               export_associated=export_associated)

                # TODO - add code to check that I got something back and handle errors.
                objects = r.json().get('object', [])
                for _ in objects:
                    status = _['info']['status']
                    if not status['status_code'] == 'OK':  # usually access errors.
                        console.log(f"unable to get {_['info']['name']}: {_['info']['status']}")

                    else:
                        fn = _['info'].get('filename', None)
                        if path:
                            fn = f"{path}/{fn}"

                        console.log(f'\twriting {fn}')
                        with open (fn, "w") as f:
                            f.write(_['edoc'])

        else:  # getting associated, so get the full pack.
            with console.status(f"[bold green]exporting ${export_ids} with associated content.[/]"):
                object_list = ts.metadata.get_edoc_object_list(export_ids)
                r = ts.api._metadata.edoc_export_epack(
                    {
                        "object": object_list,
                        "export_dependencies": True
                    }
                )
                console.log(r)
                filepath = path if not path.is_dir() else path / "metadata.tml.zip"

                util.base64_to_file(r.json()['zip_file'], filepath=filepath)

    return None


@app.command(cls=CSToolsCommand)
@frontend
def upload(  # can't use import, since that's a reserved word.
        path: pathlib.Path = A_(
            ...,
            help='full path to the TML file or directory to upload.',
            metavar='FILE_OR_DIR',
            dir_okay=True,
            resolve_path=True
        ),
        import_policy: TMLImportPolicy = O_(TMLImportPolicy.validate_only.value,
                                            help="The import policy type"),
        force_create: bool = O_(False,
                                help="If true, will force a new object to be created."),
        **frontend_kw
) -> None:
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    if not path.exists():
        console.log(f"[bold red]Error: {path} doesn't exist[/]")
        exit(-1)

    if import_policy == TMLImportPolicy.validate_only:
        console.log(f"[bold green]validating {path.name}.[/]")
    else:
        console.log(f"[bold green]importing {path.name} with policy {import_policy.value}.[/]")

    tml = []  # array of TML to update

    if path.is_dir():
        for p in path.iterdir():
            if not p.is_dir():  # don't currently support sub-folders.  Might add later.
                tml.append(yaml.load(p.read_text("utf-8"), Loader=yaml.Loader))
    else:
        tml.append(yaml.load(path.read_text("utf-8"), Loader=yaml.Loader))

    with ThoughtSpot(cfg) as ts:
        with console.status(f"[bold green]importing {path.name}[/]"):
            r = ts.api.metadata.tml_import(import_objects=tml,
                                           import_policy=import_policy.value,
                                           force_create=force_create)
            console.log(f"{r.status_code}: {r.text}")

    return None

