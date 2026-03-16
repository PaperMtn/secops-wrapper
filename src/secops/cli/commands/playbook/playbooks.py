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
"""Google SecOps CLI playbook commands"""

from pathlib import Path
import sys

from secops.chronicle.models import PlaybookType
from secops.cli.utils.common_args import add_as_list_arg
from secops.cli.utils.formatters import output_formatter
from secops.cli.utils.input_utils import load_json_or_file, load_string_or_file


def setup_playbooks_command(subparsers):
    """Setup playbooks command."""
    playbooks_parser = subparsers.add_parser(
        "playbooks",
        help="Manage Chronicle legacy playbooks",
    )
    lvl1 = playbooks_parser.add_subparsers(
        dest="playbooks_command", help="Playbooks command"
    )
    playbooks_parser.set_defaults(
        func=lambda args, _: playbooks_parser.print_help()
    )

    _setup_playbook_read_commands(lvl1)
    _setup_playbook_write_commands(lvl1)
    _setup_playbook_helper_commands(lvl1)


def _setup_playbook_read_commands(subparsers):
    """Set up read-oriented playbook commands."""
    list_parser = subparsers.add_parser("list", help="List playbooks")
    _add_playbook_types_arg(list_parser)
    add_as_list_arg(list_parser)
    list_parser.set_defaults(func=handle_playbooks_list_command)

    get_parser = subparsers.add_parser("get", help="Get playbook metadata")
    _add_playbook_identifier_arg(get_parser)
    get_parser.set_defaults(func=handle_playbooks_get_command)

    get_full_parser = subparsers.add_parser(
        "get-full", help="Get the full playbook definition"
    )
    _add_playbook_identifier_arg(get_full_parser)
    get_full_parser.set_defaults(func=handle_playbooks_get_full_command)

    get_full_env_parser = subparsers.add_parser(
        "get-full-by-environment",
        help="Get the full playbook definition filtered by environment access",
    )
    _add_playbook_identifier_arg(get_full_env_parser)
    get_full_env_parser.set_defaults(
        func=handle_playbooks_get_full_by_environment_command
    )

    get_env_parser = subparsers.add_parser(
        "get-by-environment",
        help="Get playbook metadata filtered by environment access",
    )
    _add_playbook_identifier_arg(get_env_parser)
    get_env_parser.set_defaults(
        func=handle_playbooks_get_by_environment_command
    )

    list_env_parser = subparsers.add_parser(
        "list-by-environment",
        help="List playbooks filtered by environment access",
    )
    _add_playbook_types_arg(list_env_parser)
    add_as_list_arg(list_env_parser)
    list_env_parser.set_defaults(
        func=handle_playbooks_list_by_environment_command
    )

    export_parser = subparsers.add_parser(
        "export", help="Export playbooks to a ZIP file"
    )
    export_parser.add_argument(
        "--playbook-identifiers",
        nargs="+",
        required=True,
        dest="playbook_identifiers",
        help="Identifiers of the playbooks to export",
    )
    export_parser.add_argument(
        "--output-file",
        required=True,
        dest="output_file",
        help="Path to write the exported ZIP file to",
    )
    export_parser.set_defaults(func=handle_playbooks_export_command)

    import_parser = subparsers.add_parser(
        "import", help="Import playbooks from a ZIP file"
    )
    import_parser.add_argument(
        "--input-file",
        required=True,
        dest="input_file",
        help="Path to the ZIP file to import",
    )
    import_parser.set_defaults(func=handle_playbooks_import_command)


def _setup_playbook_write_commands(subparsers):
    """Set up write-oriented playbook commands."""
    save_parser = subparsers.add_parser(
        "save", help="Save a playbook definition"
    )
    _add_definition_arg(save_parser)
    save_parser.set_defaults(func=handle_playbooks_save_command)

    clone_parser = subparsers.add_parser(
        "clone", help="Clone a playbook definition"
    )
    _add_definition_arg(clone_parser, allow_identifier=True)
    clone_parser.set_defaults(func=handle_playbooks_clone_command)

    duplicate_parser = subparsers.add_parser(
        "duplicate", help="Duplicate a playbook definition"
    )
    _add_definition_arg(duplicate_parser, allow_identifier=True)
    duplicate_parser.set_defaults(func=handle_playbooks_duplicate_command)

    duplicate_many_parser = subparsers.add_parser(
        "duplicate-many",
        help="Duplicate multiple playbooks in one request",
    )
    duplicate_many_parser.add_argument(
        "--playbook-identifiers",
        nargs="+",
        required=True,
        dest="playbook_identifiers",
        help="Identifiers of the playbooks to duplicate",
    )
    duplicate_many_parser.add_argument(
        "--priority",
        type=int,
        required=True,
        dest="priority",
        help="Priority for the duplicated playbooks",
    )
    duplicate_many_parser.add_argument(
        "--category-id",
        type=int,
        dest="category_id",
        help="Category ID for the duplicated playbooks",
    )
    duplicate_many_parser.add_argument(
        "--environments",
        nargs="+",
        dest="environments",
        help="Environments for the duplicated playbooks",
    )
    duplicate_many_parser.set_defaults(
        func=handle_playbooks_duplicate_many_command
    )

    delete_parser = subparsers.add_parser("delete", help="Delete a playbook")
    _add_playbook_identifier_arg(delete_parser)
    delete_parser.set_defaults(func=handle_playbooks_delete_command)

    delete_many_parser = subparsers.add_parser(
        "delete-many", help="Delete multiple playbooks"
    )
    delete_many_parser.add_argument(
        "--playbook-identifiers",
        nargs="+",
        required=True,
        dest="playbook_identifiers",
        help="Identifiers of the playbooks to delete",
    )
    delete_many_parser.set_defaults(func=handle_playbooks_delete_many_command)


def _setup_playbook_helper_commands(subparsers):
    """Set up helper and utility playbook commands."""
    approval_parser = subparsers.add_parser(
        "apply-approval", help="Apply a playbook approval decision"
    )
    approval_parser.add_argument(
        "--encrypted-data",
        required=True,
        dest="encrypted_data",
        help="Encrypted data value from the approval link",
    )
    approval_parser.add_argument(
        "--hashed-encrypted-data",
        required=True,
        dest="hashed_encrypted_data",
        help="Hashed encrypted data value from the approval link",
    )
    approval_parser.add_argument(
        "--is-approved",
        choices=["true", "false"],
        dest="is_approved",
        help="Whether the approval link should be approved or rejected",
    )
    approval_parser.set_defaults(func=handle_playbooks_apply_approval_command)

    check_name_parser = subparsers.add_parser(
        "check-name", help="Check whether a playbook name is available"
    )
    check_name_parser.add_argument(
        "--name",
        required=True,
        dest="name",
        help="Playbook name to check",
    )
    check_name_parser.set_defaults(func=handle_playbooks_check_name_command)

    enabled_parser = subparsers.add_parser(
        "enabled", help="List enabled playbooks"
    )
    enabled_parser.add_argument(
        "--case-environment",
        dest="case_environment",
        help="Environment to filter enabled playbooks by",
    )
    add_as_list_arg(enabled_parser)
    enabled_parser.set_defaults(func=handle_playbooks_enabled_command)

    enabled_names_parser = subparsers.add_parser(
        "enabled-names", help="List names of enabled playbooks"
    )
    add_as_list_arg(enabled_names_parser)
    enabled_names_parser.set_defaults(
        func=handle_playbooks_enabled_names_command
    )

    trigger_tags_parser = subparsers.add_parser(
        "trigger-tags", help="List playbook trigger tags"
    )
    trigger_tags_parser.add_argument(
        "--search-term",
        dest="search_term",
        help="Search term to filter trigger tags",
    )
    trigger_tags_parser.add_argument(
        "--requested-page",
        type=int,
        dest="requested_page",
        help="Requested page number",
    )
    trigger_tags_parser.add_argument(
        "--page-size",
        type=int,
        dest="page_size",
        help="Number of items to return",
    )
    add_as_list_arg(trigger_tags_parser)
    trigger_tags_parser.set_defaults(func=handle_playbooks_trigger_tags_command)

    stats_parser = subparsers.add_parser(
        "stats", help="Get execution statistics for a playbook"
    )
    _add_playbook_identifier_arg(stats_parser)
    stats_parser.add_argument(
        "--from-unix-time-ms",
        dest="from_unix_time_ms",
        help="Start time in Unix milliseconds",
    )
    stats_parser.add_argument(
        "--to-unix-time-ms",
        dest="to_unix_time_ms",
        help="End time in Unix milliseconds",
    )
    stats_parser.set_defaults(func=handle_playbooks_stats_command)

    overview_template_parser = subparsers.add_parser(
        "overview-template", help="Get a single overview template"
    )
    overview_template_parser.add_argument(
        "--template-identifier",
        required=True,
        dest="template_identifier",
        help="Identifier of the overview template",
    )
    overview_template_parser.set_defaults(
        func=handle_playbooks_overview_template_command
    )

    overview_templates_parser = subparsers.add_parser(
        "overview-templates", help="List overview templates for a playbook"
    )
    _add_playbook_identifier_arg(overview_templates_parser)
    add_as_list_arg(overview_templates_parser)
    overview_templates_parser.set_defaults(
        func=handle_playbooks_overview_templates_command
    )

    html_presets_parser = subparsers.add_parser(
        "html-view-presets", help="List HTML view presets"
    )
    add_as_list_arg(html_presets_parser)
    html_presets_parser.set_defaults(
        func=handle_playbooks_html_view_presets_command
    )

    remove_permissions_parser = subparsers.add_parser(
        "remove-permissions",
        help="Remove all explicit permissions from a playbook",
    )
    _add_playbook_identifier_arg(remove_permissions_parser)
    remove_permissions_parser.set_defaults(
        func=handle_playbooks_remove_permissions_command
    )

    permission_options_parser = subparsers.add_parser(
        "permission-options",
        help="List playbook permission options for environments",
    )
    permission_options_parser.add_argument(
        "--environments",
        nargs="+",
        required=True,
        dest="environments",
        help="Environments to fetch permission options for",
    )
    permission_options_parser.set_defaults(
        func=handle_playbooks_permission_options_command
    )

    containing_action_parser = subparsers.add_parser(
        "list-containing-action",
        help="List playbooks containing the supplied action name",
    )
    containing_action_parser.add_argument(
        "--action-name",
        required=True,
        dest="action_name",
        help="Action name to search for",
    )
    add_as_list_arg(containing_action_parser)
    containing_action_parser.set_defaults(
        func=handle_playbooks_list_containing_action_command
    )

    involving_actions_parser = subparsers.add_parser(
        "list-involving-actions",
        help="List playbooks that involve the supplied action ID",
    )
    involving_actions_parser.add_argument(
        "--action-id",
        required=True,
        dest="action_id",
        help="Action ID to search for",
    )
    add_as_list_arg(involving_actions_parser)
    involving_actions_parser.set_defaults(
        func=handle_playbooks_list_involving_actions_command
    )

    action_widget_parser = subparsers.add_parser(
        "action-widget-template",
        help="Get widget templates for playbook actions",
    )
    action_widget_parser.add_argument(
        "--action-identifiers",
        nargs="+",
        dest="action_identifiers",
        help="Action identifiers to fetch widget templates for",
    )
    action_widget_parser.add_argument(
        "--search-term",
        dest="search_term",
        help="Search term to filter widget templates",
    )
    action_widget_parser.add_argument(
        "--requested-page",
        type=int,
        dest="requested_page",
        help="Requested page number",
    )
    action_widget_parser.add_argument(
        "--page-size",
        type=int,
        dest="page_size",
        help="Number of items to return",
    )
    add_as_list_arg(action_widget_parser)
    action_widget_parser.set_defaults(
        func=handle_playbooks_action_widget_template_command
    )

    verify_transformer_parser = subparsers.add_parser(
        "verify-transformer",
        help="Verify a transformer expression using example input",
    )
    verify_transformer_parser.add_argument(
        "--json-input",
        required=True,
        dest="json_input",
        help="Input JSON string or a file path containing the JSON",
    )
    verify_transformer_parser.add_argument(
        "--pipe",
        required=True,
        dest="pipe",
        help="Transformer pipe expression or a file path containing it",
    )
    verify_transformer_parser.set_defaults(
        func=handle_playbooks_verify_transformer_command
    )


def _add_playbook_identifier_arg(parser):
    """Add the standard playbook identifier argument."""
    parser.add_argument(
        "--playbook-identifier",
        required=True,
        dest="playbook_identifier",
        help="Identifier of the playbook",
    )


def _add_playbook_types_arg(parser):
    """Add playbook type filtering arguments."""
    parser.add_argument(
        "--playbook-types",
        nargs="+",
        choices=[playbook_type.value for playbook_type in PlaybookType],
        dest="playbook_types",
        help="Playbook types to include in the response",
    )


def _add_definition_arg(parser, allow_identifier=False):
    """Add playbook definition input arguments."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--definition",
        dest="definition",
        help="Playbook definition as a JSON string or file path",
    )
    if allow_identifier:
        group.add_argument(
            "--playbook-identifier",
            dest="playbook_identifier",
            help=(
                "Identifier of an existing playbook to load before "
                "the request"
            ),
        )


def _resolve_playbook_definition(args, chronicle):
    """Resolve a playbook definition from CLI arguments."""
    if getattr(args, "definition", None):
        definition = load_json_or_file(args.definition)
        if not isinstance(definition, dict):
            raise ValueError("Playbook definition must be a JSON object")
        return definition

    if getattr(args, "playbook_identifier", None):
        return chronicle.get_playbook_full(args.playbook_identifier)

    raise ValueError("A playbook definition or playbook identifier is required")


def _parse_optional_bool(value):
    """Parse a CLI true/false value into a boolean."""
    if value is None:
        return None
    return value.lower() == "true"


def _write_bytes_output(file_path, data):
    """Write binary output to disk and return a summary dict."""
    output_path = Path(file_path).expanduser()
    output_path.write_bytes(data)
    return {"output_file": str(output_path), "bytes_written": len(data)}


def _read_bytes_input(file_path):
    """Read binary input from disk."""
    return Path(file_path).expanduser().read_bytes()


def handle_playbooks_list_command(args, chronicle):
    """Handle playbooks list command."""
    try:
        out = chronicle.list_playbooks(
            playbook_types=args.playbook_types,
            as_list=args.as_list,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error listing playbooks: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_get_command(args, chronicle):
    """Handle playbooks get command."""
    try:
        out = chronicle.get_playbook(args.playbook_identifier)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error getting playbook: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_get_full_command(args, chronicle):
    """Handle playbooks get-full command."""
    try:
        out = chronicle.get_playbook_full(args.playbook_identifier)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error getting full playbook definition: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_get_full_by_environment_command(args, chronicle):
    """Handle playbooks get-full-by-environment command."""
    try:
        out = chronicle.get_playbook_full_by_environment(
            args.playbook_identifier
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(
            f"Error getting full playbook definition by environment: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def handle_playbooks_get_by_environment_command(args, chronicle):
    """Handle playbooks get-by-environment command."""
    try:
        out = chronicle.get_playbook_by_environment(args.playbook_identifier)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error getting playbook by environment: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_list_by_environment_command(args, chronicle):
    """Handle playbooks list-by-environment command."""
    try:
        out = chronicle.list_playbooks_by_environment(
            playbook_types=args.playbook_types,
            as_list=args.as_list,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error listing playbooks by environment: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_export_command(args, chronicle):
    """Handle playbooks export command."""
    try:
        data = chronicle.export_playbooks(args.playbook_identifiers)
        out = _write_bytes_output(args.output_file, data)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error exporting playbooks: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_import_command(args, chronicle):
    """Handle playbooks import command."""
    try:
        out = chronicle.import_playbooks(_read_bytes_input(args.input_file))
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error importing playbooks: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_save_command(args, chronicle):
    """Handle playbooks save command."""
    try:
        out = chronicle.save_playbook(
            _resolve_playbook_definition(args, chronicle)
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error saving playbook: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_clone_command(args, chronicle):
    """Handle playbooks clone command."""
    try:
        out = chronicle.clone_playbook(
            _resolve_playbook_definition(args, chronicle)
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error cloning playbook: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_duplicate_command(args, chronicle):
    """Handle playbooks duplicate command."""
    try:
        out = chronicle.duplicate_playbook(
            _resolve_playbook_definition(args, chronicle)
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error duplicating playbook: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_duplicate_many_command(args, chronicle):
    """Handle playbooks duplicate-many command."""
    try:
        out = chronicle.duplicate_playbooks(
            identifiers=args.playbook_identifiers,
            priority=args.priority,
            category_id=args.category_id,
            environments=args.environments,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error duplicating playbooks: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_delete_command(args, chronicle):
    """Handle playbooks delete command."""
    try:
        playbook_definition = chronicle.get_playbook_full(
            args.playbook_identifier
        )
        chronicle.delete_playbook(playbook_definition)
        print(f"Playbook {args.playbook_identifier} deleted successfully")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error deleting playbook: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_delete_many_command(args, chronicle):
    """Handle playbooks delete-many command."""
    try:
        out = chronicle.delete_playbooks(args.playbook_identifiers)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error deleting playbooks: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_apply_approval_command(args, chronicle):
    """Handle playbooks apply-approval command."""
    try:
        out = chronicle.apply_playbook_approval(
            encrypted_data=args.encrypted_data,
            hashed_encrypted_data=args.hashed_encrypted_data,
            is_approved=_parse_optional_bool(args.is_approved),
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error applying playbook approval: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_check_name_command(args, chronicle):
    """Handle playbooks check-name command."""
    try:
        out = chronicle.check_playbook_name_availability(args.name)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(
            f"Error checking playbook name availability: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def handle_playbooks_enabled_command(args, chronicle):
    """Handle playbooks enabled command."""
    try:
        out = chronicle.list_enabled_playbooks(
            case_environment=args.case_environment,
            as_list=args.as_list,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error listing enabled playbooks: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_enabled_names_command(args, chronicle):
    """Handle playbooks enabled-names command."""
    try:
        out = chronicle.list_enabled_playbook_names(as_list=args.as_list)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error listing enabled playbook names: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_trigger_tags_command(args, chronicle):
    """Handle playbooks trigger-tags command."""
    try:
        out = chronicle.list_playbook_trigger_tags(
            search_term=args.search_term,
            requested_page=args.requested_page,
            page_size=args.page_size,
            as_list=args.as_list,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error listing playbook trigger tags: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_stats_command(args, chronicle):
    """Handle playbooks stats command."""
    try:
        out = chronicle.get_playbook_stats(
            playbook_identifier=args.playbook_identifier,
            from_unix_time_ms=args.from_unix_time_ms,
            to_unix_time_ms=args.to_unix_time_ms,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error getting playbook stats: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_overview_template_command(args, chronicle):
    """Handle playbooks overview-template command."""
    try:
        out = chronicle.get_overview_template(args.template_identifier)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error getting overview template: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_overview_templates_command(args, chronicle):
    """Handle playbooks overview-templates command."""
    try:
        out = chronicle.get_overview_templates(
            playbook_identifier=args.playbook_identifier,
            as_list=args.as_list,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error getting overview templates: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_html_view_presets_command(args, chronicle):
    """Handle playbooks html-view-presets command."""
    try:
        out = chronicle.list_html_view_presets(as_list=args.as_list)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error listing HTML view presets: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_remove_permissions_command(args, chronicle):
    """Handle playbooks remove-permissions command."""
    try:
        chronicle.remove_playbook_permissions(args.playbook_identifier)
        print(
            "Removed permissions for playbook "
            f"{args.playbook_identifier} successfully"
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error removing playbook permissions: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_permission_options_command(args, chronicle):
    """Handle playbooks permission-options command."""
    try:
        out = chronicle.list_playbook_permission_options(args.environments)
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(
            f"Error listing playbook permission options: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def handle_playbooks_list_containing_action_command(args, chronicle):
    """Handle playbooks list-containing-action command."""
    try:
        out = chronicle.list_playbooks_containing_action(
            action_name=args.action_name,
            as_list=args.as_list,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(
            "Error listing playbooks containing action "
            f"{args.action_name}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def handle_playbooks_list_involving_actions_command(args, chronicle):
    """Handle playbooks list-involving-actions command."""
    try:
        out = chronicle.list_playbooks_involving_actions(
            action_id=args.action_id,
            as_list=args.as_list,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(
            f"Error listing playbooks involving action {args.action_id}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def handle_playbooks_action_widget_template_command(args, chronicle):
    """Handle playbooks action-widget-template command."""
    try:
        out = chronicle.get_action_widget_template(
            action_identifiers=args.action_identifiers,
            search_term=args.search_term,
            requested_page=args.requested_page,
            page_size=args.page_size,
            as_list=args.as_list,
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error getting action widget template: {e}", file=sys.stderr)
        sys.exit(1)


def handle_playbooks_verify_transformer_command(args, chronicle):
    """Handle playbooks verify-transformer command."""
    try:
        out = chronicle.verify_transformer_example(
            json=load_string_or_file(args.json_input),
            pipe=load_string_or_file(args.pipe),
        )
        output_formatter(out, getattr(args, "output", "json"))
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error verifying transformer example: {e}", file=sys.stderr)
        sys.exit(1)
