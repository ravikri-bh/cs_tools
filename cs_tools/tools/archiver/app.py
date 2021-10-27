import pathlib
import enum

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand, DataTable
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig
from cs_tools import util


class ContentType(enum.Enum):
    answer = 'answer'
    pinboard = 'pinboard'
    all = 'all'


class UserActions(enum.Enum):
    view_answer = 'ANSWER_VIEW'
    view_pinboard = 'PINBOARD_VIEW'
    view_embed_pinboard = 'PINBOARD_TSPUBLIC_RUNTIME_FILTER'
    view_embed_filtered_pinboard_view = 'PINBOARD_TSPUBLIC_NO_RUNTIME_FILTER'

    @classmethod
    def strigified(cls, sep: str=' ', context: str=None) -> str:
        mapper = {
            'answer': ['ANSWER_VIEW'],
            'pinboard': [
                'PINBOARD_VIEW',
                'PINBOARD_TSPUBLIC_RUNTIME_FILTER',
                'PINBOARD_TSPUBLIC_NO_RUNTIME_FILTER'
            ]
        }
        allowed = mapper.get(context, [_.value for _ in cls])
        return sep.join([_.value for _ in cls if _.value in allowed])


app = typer.Typer(
    help="""
    Manage stale answers and pinboards within your platform.

    [b][yellow]This tool is still in active development![/b] Tool and command
    names are not final and some or all commands may not yet be implemented.[/]

    As your platform grows, users will create and use answers and pinboards.
    Sometimes, users will create content for temporary exploratory purpopses
    and then abandon it for newer pursuits. Archiver enables you to identify,
    tag, export, and remove that potentially abandoned content.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def identify(
    tag: str=O_('TO BE ARCHIVED', help='tag name to use for labeling objects to archive'),
    content: ContentType=O_('all', help='type of content to archive'),
    usage_months: int=O_(
        999,
        show_default=False,
        help='months to consider for user activity (default: all user history)'
    ),
    dry_run: bool=O_(
        False,
        '--dry-run',
        show_default=False,
        help='test selection criteria, do not apply tags and instead output information on content to be archived'
    ),
    **frontend_kw
):
    """
    Identify objects which objects can be archived.

    ThoughtSpot stores usage activity (by default, 6 months of interactions) by user in
    the platform. If a user views, edits, or creates an Answer or Pinboard, ThoughtSpot
    knows about it. This can be used as a proxy to understanding what content is
    actively being used.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)
    actions = UserActions.strigified(sep="', '", context=content)

    with ThoughtSpot(cfg) as ts:
        data = ts.search(
            f"[user action] = '{actions}' "
            f"[timestamp].'last {usage_months} months' "
            f"[timestamp].'this month' "
            f"[answer book guid]",
            worksheet='TS: BI Server'
        )

        # Currently used GUIDs (within the past {months} months ...)
        usage = set(_['Answer Book GUID'] for _ in data)

        # Repository of all available GUIDs
        data = []

        if content.value in ('all', 'answer'):
            data.extend({**a, 'content_type': 'answer'} for a in ts.answer.all())

        if content.value in ('all', 'pinboard'):
            data.extend({**p, 'content_type': 'pinboard'} for p in ts.pinboard.all())

        #
        #
        #

        archive = set(_['id'] for _ in data) - usage

        to_archive = [
            {'content_type': _['content_type'], 'guid': _['id'], 'name': _['name']}
            for _ in data if _['id'] in archive
        ]

        table = DataTable(
                    to_archive,
                    title=f"[green]Archive Results[/]: Tagging content with [cyan]'{tag}'[/]",
                    caption=f'Total of {len(to_archive)} items tagged.. ({len(data)} seen)'
                )
        console.log('\n', table)

        if dry_run:
            raise typer.Exit(-1)

        tag = ts.tag.get(tag, create_if_not_exists=True)

        answers = [content['guid'] for content in to_archive if content['content_type'] == 'answer']
        ts.api._metadata.assigntag(
            id=answers,
            type=['QUESTION_ANSWER_BOOK' for _ in answers],
            tagid=[tag['id'] for _ in answers]
        )

        pinboards = [content['guid'] for content in to_archive if content['content_type'] == 'pinboard']
        ts.api._metadata.assigntag(
            id=pinboards,
            type=['PINBOARD_ANSWER_BOOK' for _ in pinboards],
            tagid=[tag['id'] for _ in pinboards]
        )


@app.command(cls=RichCommand)
@frontend
def deidentify(
    tag: str=O_('TO BE ARCHIVED', help='tag name to remove on labeled objects'),
    remove_tag: bool=O_(
        False,
        '--remove-tag',
        show_default=False,
        help='remove the tag after untagging identified objects'
    ),
    dry_run: bool=O_(
        False,
        '--dry-run',
        show_default=False,
        help='test selection criteria, do not remove tags and instead output information on content to be unarchived'
    ),
    **frontend_kw
):
    """
    Remove objects from the temporary archive.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        to_unarchive = []

        to_unarchive.extend(
            {'content_type': 'answer', 'guid': a['id'], 'name': a['name']}
            for a in ts.answer.all(tags=tag)
        )

        to_unarchive.extend(
            {'content_type': 'pinboard', 'guid': p['id'], 'name': p['name']}
            for p in ts.pinboard.all(tags=tag)
        )

        if not to_unarchive:
            console.log(f"no content found with the tag '{tag}'")
            raise typer.Exit()

        table = DataTable(
                    to_unarchive,
                    title=f"[green]Unarchive Results[/]: Untagging content with [cyan]'{tag}'[/]",
                    caption=f'Total of {len(to_unarchive)} items tagged..'
                )

        console.log('\n', table)

        if dry_run:
            raise typer.Exit()

        tag = ts.tag.get(tag)

        answers = [content['guid'] for content in to_unarchive if content['content_type'] == 'answer']
        ts.api._metadata.unassigntag(
            id=answers,
            type=['QUESTION_ANSWER_BOOK' for _ in answers],
            tagid=[tag['id'] for _ in answers]
        )

        pinboards = [content['guid'] for content in to_unarchive if content['content_type'] == 'pinboard']
        ts.api._metadata.unassigntag(
            id=pinboards,
            type=['QUESTION_ANSWER_BOOK' for _ in pinboards],
            tagid=[tag['id'] for _ in pinboards]
        )

        if remove_tag:
            ts.tag.delete(tag['name'])


@app.command(cls=RichCommand)
@frontend
def remove(
    tag: str=O_('TO BE ARCHIVED', help='tag name to remove on labeled objects'),
    export_tml: pathlib.Path=O_(None, help='file path to export tagged objects, as zipfile'),
    remove_tag: bool=O_(
        False,
        '--remove-tag',
        show_default=False,
        help='remove the tag after deleting identified objects'
    ),
    dry_run: bool=O_(
        False,
        '--dry-run',
        show_default=False,
        help=(
            'test selection criteria, does not export/delete content and instead '
            'output information on content to be unarchived'
        )
    ),
    **frontend_kw
):
    """
    Remove objects from the ThoughtSpot platform.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    if export_tml is not None and not export_tml.as_posix().endswith('zip'):
        console.print(f"[b red]TML export path must be a zip file! Got, '{export_tml}'")
        raise typer.Exit(-1)

    with ThoughtSpot(cfg) as ts:
        to_unarchive = []

        to_unarchive.extend(
            {'content_type': 'answer', 'guid': a['id'], 'name': a['name']}
            for a in ts.answer.all(tags=tag)
        )

        to_unarchive.extend(
            {'content_type': 'pinboard', 'guid': p['id'], 'name': p['name']}
            for p in ts.pinboard.all(tags=tag)
        )

        if not to_unarchive:
            console.log(f"no content found with the tag '{tag}'")
            raise typer.Exit()

        _mod = '' if export_tml is None else ' and exporting '
        table = DataTable(
                    to_unarchive,
                    title=f"[green]Remove Results[/]: Removing{_mod} content with [cyan]'{tag}'[/]",
                    caption=f'Total of {len(to_unarchive)} items tagged..'
                )
        console.log('\n', table)

        if dry_run:
            raise typer.Exit()

        tag = ts.tag.get(tag)
        answers = [content['guid'] for content in to_unarchive if content['content_type'] == 'answer']
        pinboards = [content['guid'] for content in to_unarchive if content['content_type'] == 'pinboard']

        if export_tml is not None:
            r = ts.api._metadata.edoc_export_epack(
                    request={
                        'object': [
                            *[{'id': id, 'type': 'QUESTION_ANSWER_BOOK'} for id in answers],
                            *[{'id': id, 'type': 'PINBOARD_ANSWER_BOOK'} for id in pinboards]
                        ],
                        'export_dependencies': False
                    }
                )

            util.base64_to_file(r.json()['zip_file'], filepath=export_tml)

        ts.api._metadata.delete(id=answers, type=['QUESTION_ANSWER_BOOK' for _ in answers])
        ts.api._metadata.delete(id=pinboards, type=['PINBOARD_ANSWER_BOOK' for _ in pinboards])

        if remove_tag:
            ts.tag.delete(tag['name'])
