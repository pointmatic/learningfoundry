# Copyright 2026 Pointmatic
# SPDX-License-Identifier: Apache-2.0

import click

from learningfoundry import __version__


@click.group()
@click.version_option(version=__version__, prog_name="learningfoundry")
def main() -> None:
    """A curriculum engine that generates deployable SvelteKit learning apps."""
