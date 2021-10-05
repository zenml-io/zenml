#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import click

from zenml import __version__
from zenml.cli.cli import cli


@cli.command()
def version():
    """Version of ZenML"""
    click.echo(
        click.style(
            r"""      
           .-') _   ('-.       .-') _  _   .-')              
          (  OO) )_(  OO)     ( OO ) )( '.( OO )_            
        ,(_)----.(,------.,--./ ,--,'  ,--.   ,--.),--.      
        |       | |  .---'|   \ |  |\  |   `.'   | |  |.-')  
        '--.   /  |  |    |    \|  | ) |         | |  | OO ) 
        (_/   /  (|  '--. |  .     |/  |  |'.'|  | |  |`-' | 
         /   /___ |  .--' |  |\    |   |  |   |  |(|  '---.' 
        |        ||  `---.|  | \   |   |  |   |  | |      |  
        `--------'`------'`--'  `--'   `--'   `--' `------' 
         """,
            fg="green",
        )
    )
    click.echo(click.style(f"version: {__version__}", bold=True))
