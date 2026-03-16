# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Top level arguments for playbook commands"""

from secops.cli.commands.playbook import (
    playbooks
)


def setup_playbooks_command(subparsers):
    """Setup playbooks command"""
    playbooks_parser = subparsers.add_parser(
        "playbook", help="Manage SecOps playbooks"
    )
    lvl1 = playbooks_parser.add_subparsers(
        dest="playbooks_command", help="Playbooks command"
    )

    # Setup all subcommands under `playbooks`
    playbooks.setup_playbooks_command(lvl1)