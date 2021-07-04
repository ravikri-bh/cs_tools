import pathlib

from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from typer import Argument as A_, Option as O_  # noqa
import uvicorn
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand


app = typer.Typer(
    help="""
    One-liner describing the tool.

    Further explanation explaining the tool's usage or purpose. This can
    be as long as is necessary, but be mindful of much content you type
    here as the full text will display in the console when the user
    types...

      cs_tools tools my-cool-app --help

    If more ideas need to be conveyed, use separate paragraphs. Content
    will be wrapped to the console spec (default: 125 characters) unless
    you use a control character.

    Many tools augment a ThoughtSpot service. If they do, a relevant
    documentation link should be provided.

    \b
    For further information on <idea expressed in doc>, please refer to:
      https://docs.thoughtspot.com/path/to/documenation-link.html

    \f
    DEV NOTE:

      Two control characters are offered in order to help with
      docstrings in typer App helptext and command helptext
      (docstrings).

      \b - Preserve Whitespace / formatting.
      \f - EOF, don't include anything after this character in helptext.
    """,
    cls=RichGroup
)

#

HERE = pathlib.Path(__file__).parent
web_app = FastAPI()
web_app.mount('/static', StaticFiles(directory=f'{HERE}/static'), name='static')
web_app.mount('/new', StaticFiles(directory=f'{HERE}/static2'), name='static2')


@web_app.get('/')
async def read_index():
    return RedirectResponse(url='/static/index.html')


@web_app.get('/new')
async def read_index_new():
    return RedirectResponse(url='/new/index.html')

#


# NOTE:
#
# We will probably use Flask or simply host the JS using the built-in HTTP webserver
# library. Need to see Misha's code impl first to better understand what's the best
# option here.
#
# It also might be relevant to have a welcome-page describing requirements of how to get
# the app running (eg. enabling CORS appropriately, link-through to CLS settings
# documentation page, how-to guides on how to do those things -- all of these could be
# a v2 release if desired).
#

@app.command(cls=RichCommand)
def run(
    # **frontend_kw
):
    """
    """
    uvicorn.run('cs_tools.tools._cls-sharing.app:web_app', host='127.0.0.1', port=5000, log_level='info')
