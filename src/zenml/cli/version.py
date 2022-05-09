#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import random

import click

from zenml import __version__
from zenml.cli.cli import cli
from zenml.cli.utils import declare

ascii_arts = [
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
    r"""
      ____..--'     .-''-.   ,---.   .--. ,---.    ,---.   .---.      
     |        |   .'_ _   \  |    \  |  | |    \  /    |   | ,_|      
     |   .-'  '  / ( ` )   ' |  ,  \ |  | |  ,  \/  ,  | ,-./  )      
     |.-'.'   / . (_ o _)  | |  |\_ \|  | |  |\_   /|  | \  '_ '`)    
        /   _/  |  (_,_)___| |  _( )_\  | |  _( )_/ |  |  > (_)  )    
      .'._( )_  '  \   .---. | (_ o _)  | | (_ o _) |  | (  .  .-'    
    .'  (_'o._)  \  `-'    / |  (_,_)\  | |  (_,_)  |  |  `-'`-'|___  
    |    (_,_)|   \       /  |  |    |  | |  |      |  |   |        \ 
    |_________|    `'-..-'   '--'    '--' '--'      '--'   `--------`                                                           
    """,
    r"""
     ________                      __       __  __       
    |        \                    |  \     /  \|  \      
     \$$$$$$$$  ______   _______  | $$\   /  $$| $$      
        /  $$  /      \ |       \ | $$$\ /  $$$| $$      
       /  $$  |  $$$$$$\| $$$$$$$\| $$$$\  $$$$| $$      
      /  $$   | $$    $$| $$  | $$| $$\$$ $$ $$| $$      
     /  $$___ | $$$$$$$$| $$  | $$| $$ \$$$| $$| $$_____ 
    |  $$    \ \$$     \| $$  | $$| $$  \$ | $$| $$     \
     \$$$$$$$$  \$$$$$$$ \$$   \$$ \$$      \$$ \$$$$$$$$
    """,
    r"""
        )                    *      (     
     ( /(                  (  `     )\ )  
     )\())    (            )\))(   (()/(  
    ((_)\    ))\    (     ((_)()\   /(_)) 
     _((_)  /((_)   )\ )  (_()((_) (_))   
    |_  /  (_))    _(_/(  |  \/  | | |    
     / /   / -_)  | ' \)) | |\/| | | |__  
    /___|  \___|  |_||_|  |_|  |_| |____| 
    """,
    r"""
███████ ███████ ███    ██ ███    ███ ██      
   ███  ██      ████   ██ ████  ████ ██      
  ███   █████   ██ ██  ██ ██ ████ ██ ██      
 ███    ██      ██  ██ ██ ██  ██  ██ ██      
███████ ███████ ██   ████ ██      ██ ███████ 
    """,
]


@cli.command()
def version() -> None:
    """Version of ZenML."""
    declare(random.choice(ascii_arts))
    click.echo(click.style(f"version: {__version__}", bold=True))
