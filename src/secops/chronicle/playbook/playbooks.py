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
"""Playbook functionality for Chronicle."""

from typing import Any, TYPE_CHECKING

from secops.chronicle.models import APIVersion, PlaybookType

from secops.chronicle.utils.request_utils import (
    chronicle_request_bytes,
    chronicle_request,
    chronicle_multipart_upload,
)

if TYPE_CHECKING:
    from secops.chronicle.client import ChronicleClient


def _extract_list(
    data: dict[str, Any] | Any,
    as_list: bool,
    key: str = "payload",
) -> dict[str, Any] | list[Any]:
    """Conditionally extract a list from a response dict.

    When ``as_list`` is ``True``, returns the value found under ``key``
    (defaulting to an empty list). When ``False`` the original ``data``
    is returned unchanged.

    Args:
        data: The API response, typically a dict.
        as_list: Whether to extract the inner list.
        key: The dict key that holds the list items.

    Returns:
        Either the extracted list or the original response dict.
    """
    if as_list:
        if isinstance(data, dict):
            return data.get(key, [])
        return data

    return data


def export_playbooks(
    client: "ChronicleClient",
    playbook_identifiers: list[str],
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> bytes:
    """Export one or more playbook definitions as a ZIP file.

    Use this method to back up playbooks or share automation logic across
    different SecOps instances.

    Args:
        client: ChronicleClient instance.
        playbook_identifiers: List of playbook identifiers to export.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Raw bytes of the exported ZIP file.

    Raises:
        APIError: If the API request fails.
    """
    params = {
        "identifiers": ",".join(playbook_identifiers),
        "alt": "media",
    }

    headers = {
        "Accept": "application/zip, application/json",
    }

    data = chronicle_request_bytes(
        client,
        method="GET",
        endpoint_path="legacyPlaybooks:legacyExportDefinitions",
        api_version=api_version,
        params=params,
        headers=headers,
    )
    return data


def import_playbooks(
    client: "ChronicleClient",
    zip_data: bytes,
    api_version: APIVersion | None = APIVersion.V1ALPHA_UPLOAD,
) -> dict[str, Any]:
    """Import multiple playbook definitions from a ZIP file.

    Use this method for bulk deployment of response playbooks.

    Args:
        client: ChronicleClient instance.
        zip_data: Raw bytes of the ZIP file containing playbook definitions.
        api_version: API version to use for the request. Default is
            V1ALPHA_UPLOAD.

    Returns:
        Dict containing the following fields:
            - workflowIdentifiers: List of identifiers of the imported
              playbook definitions.
            - mediaInfo: Metadata about the media upload response.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_multipart_upload(
        client,
        endpoint_path="legacyPlaybooks:legacyImportDefinitions",
        file_data=zip_data,
        file_content_type="application/zip",
        api_version=api_version,
    )


def list_playbooks(
    client: "ChronicleClient",
    playbook_types: list[PlaybookType | str] | None = None,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    """List playbook definitions filtered by playbook type.

    Use this method to browse and select from the set of current automation
    playbooks.

    Args:
        client: ChronicleClient instance.
        playbook_types: List of playbook types to filter by. If omitted,
            defaults to all types: REGULAR and NESTED.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of playbook definitions instead of
            a dict with a payload list.

    Returns:
        If as_list is True: List of playbook definitions.
        If as_list is False: Dict with payload list of playbook definitions.

    Raises:
        APIError: If the API request fails.
    """
    if playbook_types is None:
        playbook_types = [PlaybookType.REGULAR, PlaybookType.NESTED]

    resolved_types = [
        t.value if isinstance(t, PlaybookType) else t for t in playbook_types
    ]

    data = chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyGetWorkflowMenuCards",
        api_version=api_version,
        json={"legacyPayload": resolved_types},
    )

    return _extract_list(data, as_list)


def get_playbook(
    client: "ChronicleClient",
    playbook_identifier: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Get a single playbook definition for the specified identifier.

    Use this method to retrieve metadata like category and version for a
    specific playbook.

    Args:
        client: ChronicleClient instance.
        playbook_identifier: Identifier of the playbook to retrieve.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing the playbook definition.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="GET",
        endpoint_path="legacyPlaybooks:legacyGetWorkflowMenuCard",
        api_version=api_version,
        params={"workflowIdentifier": playbook_identifier},
    )


def save_playbook(
    client: "ChronicleClient",
    playbook_definition: dict[str, Any],
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Save the configuration and step sequence of a playbook.

    Use this method to commit changes to a playbook's automation logic.

    Args:
        client: ChronicleClient instance.
        playbook_definition: Dict containing the playbook definition.
            to save.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing the saved playbook definition.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacySaveWorkflowDefinitions",
        api_version=api_version,
        json=playbook_definition,
    )


def clone_playbook(
    client: "ChronicleClient",
    playbook_definition: dict[str, Any],
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Create an exact copy of a playbook definition.

    Use this method to instantiate a new version of an existing playbook for
    modification or testing.

    Args:
        client: ChronicleClient instance.
        playbook_definition: Dict containing the ApiWorkflowDefinitionDataModel
            to clone.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing the cloned ApiWorkflowDefinitionDataModel.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyCloneWorkflow",
        api_version=api_version,
        json=playbook_definition,
    )


def duplicate_playbook(
    client: "ChronicleClient",
    playbook_definition: dict[str, Any],
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Create a duplicate of a playbook definition.

    Use this method to create a new playbook starting from an existing
    template.

    Args:
        client: ChronicleClient instance.
        playbook_definition: Dict containing the ApiWorkflowDefinitionDataModel
            to duplicate.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing the duplicated ApiWorkflowDefinitionDataModel.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyDuplicateWorkflow",
        api_version=api_version,
        json=playbook_definition,
    )


def duplicate_playbooks(
    client: "ChronicleClient",
    identifiers: list[str],
    priority: int,
    category_id: int | None = None,
    environments: list[str] | None = None,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Create duplicates of multiple playbook definitions in a single operation.

    Use this method for bulk creation of playbooks based on existing items.

    Args:
        client: ChronicleClient instance.
        identifiers: List of playbook identifiers to duplicate.
        priority: Priority of the duplicated playbooks.
        category_id: Category to assign the duplicated playbooks to. Optional.
        environments: List of environments to assign the duplicated playbooks
            to. Optional.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing a payload list of duplicated
        ApiWorkflowDefinitionDataModel instances.

    Raises:
        APIError: If the API request fails.
    """
    body = {
        "identifiers": identifiers,
        "priority": priority,
        "categoryId": category_id,
        "environments": environments,
    }

    # Remove keys with None values
    body = {k: v for k, v in body.items() if v is not None}

    return chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyDuplicateWorkflows",
        api_version=api_version,
        json=body,
    )


def delete_playbook(
    client: "ChronicleClient",
    playbook_definition: dict[str, Any],
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> None:
    """Permanently remove a single playbook definition.

    Args:
        client: ChronicleClient instance.
        playbook_definition: Dict containing the ApiWorkflowDefinitionDataModel
            to delete.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        None

    Raises:
        APIError: If the API request fails.
    """
    chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyDeleteWorkflow",
        api_version=api_version,
        json=playbook_definition,
        expected_status={200, 204},
    )


def delete_playbooks(
    client: "ChronicleClient",
    identifiers: list[str],
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Delete multiple playbook definitions in a single operation.

    Use this method for bulk removal of obsolete or redundant playbooks.

    Args:
        client: ChronicleClient instance.
        identifiers: List of playbook identifiers to delete.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing a results list of ApiDeleteWorkflowResult instances.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyDeleteWorkflows",
        api_version=api_version,
        json={"identifiers": identifiers},
    )


def get_playbook_full(
    client: "ChronicleClient",
    playbook_identifier: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Get the full configuration of a playbook, including its steps and
    connectivity logic.

    Args:
        client: ChronicleClient instance.
        playbook_identifier: Identifier of the playbook to retrieve.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing the full ApiWorkflowDefinitionDataModel.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="GET",
        endpoint_path="legacyPlaybooks:legacyGetWorkflowFullInfoByIdentifier",
        api_version=api_version,
        params={"workflowIdentifier": playbook_identifier},
    )


def get_playbook_full_by_environment(
    client: "ChronicleClient",
    playbook_identifier: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Get the full playbook definition, filtered by the user's accessible
    environments.

    Args:
        client: ChronicleClient instance.
        playbook_identifier: Identifier of the playbook to retrieve.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing the full ApiWorkflowDefinitionDataModel filtered by
        the user's accessible environments.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="GET",
        endpoint_path=(
            "legacyPlaybooks:"
            "legacyGetWorkflowFullInfoWithEnvFilterByIdentifier"
        ),
        api_version=api_version,
        params={"workflowIdentifier": playbook_identifier},
    )


def get_playbook_by_environment(
    client: "ChronicleClient",
    playbook_identifier: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Get a playbook definition with metadata adjusted according to the
    user's environment permissions.

    Args:
        client: ChronicleClient instance.
        playbook_identifier: Identifier of the playbook to retrieve.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing the ApiWorkflowMenuCardDefinitionDataModel filtered
        by the user's environment permissions.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="GET",
        endpoint_path=(
            "legacyPlaybooks:legacyGetWorkflowMenuCardWithEnvFilter"
        ),
        api_version=api_version,
        params={"workflowIdentifier": playbook_identifier},
    )


def list_playbooks_by_environment(
    client: "ChronicleClient",
    playbook_types: list[PlaybookType | str] | None = None,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    """List playbook definitions filtered by the user's accessible environments.

    Args:
        client: ChronicleClient instance.
        playbook_types: List of playbook types to filter by. If omitted,
            defaults to all types: REGULAR and NESTED.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of playbook definitions instead of
            a dict with a payload list.

    Returns:
        If as_list is True: List of playbook definitions.
        If as_list is False: Dict with payload list of playbook definitions.

    Raises:
        APIError: If the API request fails.
    """
    if playbook_types is None:
        playbook_types = [PlaybookType.REGULAR, PlaybookType.NESTED]

    resolved_types = [
        t.value if isinstance(t, PlaybookType) else t for t in playbook_types
    ]

    data = chronicle_request(
        client,
        method="POST",
        endpoint_path=(
            "legacyPlaybooks:legacyGetWorkflowMenuCardsWithEnvFilter"
        ),
        api_version=api_version,
        json={"legacyPayload": resolved_types},
    )

    return _extract_list(data, as_list)


def apply_playbook_approval(
    client: "ChronicleClient",
    encrypted_data: str,
    hashed_encrypted_data: str,
    is_approved: bool | None = None,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Process an analyst's decision from a manual approval link.

    Use this method to record the outcome of a manual action and continue
    the playbook's execution.

    Args:
        client: ChronicleClient instance.
        encrypted_data: The encrypted data from the approval link.
        hashed_encrypted_data: The hashed encrypted data from the approval
            link.
        is_approved: Whether the approval link is approved. Optional.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing the approval link result with the following fields:
            - status: The status of the approval link.
            - caseId: The case id.
            - actionName: The action name.
            - approvalLinkActionType: The type of the approval link action.

    Raises:
        APIError: If the API request fails.
    """
    body = {
        "encryptedData": encrypted_data,
        "hashedEncryptedData": hashed_encrypted_data,
        "isApproved": is_approved,
    }

    body = {k: v for k, v in body.items() if v is not None}

    return chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyApplyApprovalLink",
        api_version=api_version,
        json=body,
    )


def check_playbook_name_availability(
    client: "ChronicleClient",
    name: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Check if a playbook name is already in use within any environment.

    Use this method to prevent naming conflicts before creating or updating
    a playbook.

    Args:
        client: ChronicleClient instance.
        name: The playbook name to check.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing a payload field with the identifier of the existing
        playbook if the name is already in use, or empty if available.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="POST",
        endpoint_path=(
            "legacyPlaybooks:" "legacyCheckWorkflowNameInDifferentEnvironments"
        ),
        api_version=api_version,
        json={"wfName": name},
    )


def list_enabled_playbooks(
    client: "ChronicleClient",
    case_environment: str | None = None,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    """List all playbooks that are currently enabled and ready for execution.

    Args:
        client: ChronicleClient instance.
        case_environment: Environment to filter enabled playbooks by.
            Optional.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of playbook cards instead of a dict
            with a payload list.

    Returns:
        If as_list is True: List of ApiPlaybookCard instances.
        If as_list is False: Dict with payload list of ApiPlaybookCard
            instances.

    Raises:
        APIError: If the API request fails.
    """
    body = {"caseEnvironment": case_environment}
    body = {k: v for k, v in body.items() if v is not None}

    data = chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyGetEnabledWFCards",
        api_version=api_version,
        json=body,
    )

    return _extract_list(data, as_list)


def list_enabled_playbook_names(
    client: "ChronicleClient",
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[str]:
    """List the display names of all playbooks currently enabled in the
    instance.

    Args:
        client: ChronicleClient instance.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of playbook names instead of a dict
            with a payload list.

    Returns:
        If as_list is True: List of enabled playbook name strings.
        If as_list is False: Dict with payload list of enabled playbook name
            strings.

    Raises:
        APIError: If the API request fails.
    """
    data = chronicle_request(
        client,
        method="GET",
        endpoint_path="legacyPlaybooks:legacyGetEnabledWFNames",
        api_version=api_version,
    )

    return _extract_list(data, as_list)


def list_playbook_trigger_tags(
    client: "ChronicleClient",
    search_term: str | None = None,
    requested_page: int | None = None,
    page_size: int | None = None,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[str]:
    """List the tags configured as triggers for playbooks.

    Use this method to discover the security event attributes that currently
    initiate automated response playbooks.

    Args:
        client: ChronicleClient instance.
        search_term: Search term to filter trigger tags by. Optional.
        requested_page: Page number to retrieve. Optional.
        page_size: Number of items per page. Optional.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of trigger tag strings instead of a
            dict with objectsList and metadata.

    Returns:
        If as_list is True: List of trigger tag strings.
        If as_list is False: Dict containing objectsList and metadata.

    Raises:
        APIError: If the API request fails.
    """
    body = {
        "searchTerm": search_term,
        "requestedPage": requested_page,
        "pageSize": page_size,
    }

    body = {k: v for k, v in body.items() if v is not None}

    data = chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyGetTriggerTags",
        api_version=api_version,
        json=body,
    )

    return _extract_list(data, as_list, key="objectsList")


def get_playbook_stats(
    client: "ChronicleClient",
    playbook_identifier: str,
    from_unix_time_ms: str | None = None,
    to_unix_time_ms: str | None = None,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Get operational metrics for a playbook, including execution counts and
    performance distributions.

    Use this method to monitor the throughput and efficiency of automated
    response playbooks.

    Args:
        client: ChronicleClient instance.
        playbook_identifier: Identifier of the playbook to retrieve stats for.
        from_unix_time_ms: Start time for the stats in Unix time milliseconds.
            Optional.
        to_unix_time_ms: End time for the stats in Unix time milliseconds.
            Optional.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing steps and flows stats maps.

    Raises:
        APIError: If the API request fails.
    """
    body = {
        "originalWorkflowIdentifier": playbook_identifier,
        "fromUnixTimeMs": from_unix_time_ms,
        "toUnixTimeMs": to_unix_time_ms,
    }

    body = {k: v for k, v in body.items() if v is not None}

    return chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyGetPlaybookStatsMap",
        api_version=api_version,
        json=body,
    )


def get_overview_template(
    client: "ChronicleClient",
    template_identifier: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Get a specific overview template by its identifier.

    Args:
        client: ChronicleClient instance.
        template_identifier: Identifier of the overview template to retrieve.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing the LegacyPlaybookOverviewTemplateData.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="GET",
        endpoint_path="legacyPlaybooks:legacyGetOverviewTemplate",
        api_version=api_version,
        params={"templateIdentifier": template_identifier},
    )


def get_overview_templates(
    client: "ChronicleClient",
    playbook_identifier: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Get the overview templates associated with a specific playbook.

    Args:
        client: ChronicleClient instance.
        playbook_identifier: Identifier of the playbook to retrieve overview
            templates for.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of overview templates instead of a
            dict with a payload list.

    Returns:
        If as_list is True: List of LegacyPlaybookOverviewTemplateData
            instances.
        If as_list is False: Dict with payload list of
            LegacyPlaybookOverviewTemplateData instances.

    Raises:
        APIError: If the API request fails.
    """
    data = chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyGetOverviewTemplates",
        api_version=api_version,
        json={"playbookIdentifier": playbook_identifier},
    )

    return _extract_list(data, as_list)


def list_html_view_presets(
    client: "ChronicleClient",
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    """List predefined HTML view presets.

    Use this method to retrieve the available layout configurations for
    visualizing investigation data within the SecOps UI.

    Args:
        client: ChronicleClient instance.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of HTML view presets instead of a
            dict with a payload list.

    Returns:
        If as_list is True: List of HtmlViewPreset instances, each containing
            name, identifier, thumbnailBase64, htmlCode, and htmlHeight.
        If as_list is False: Dict with payload list of HtmlViewPreset
            instances.

    Raises:
        APIError: If the API request fails.
    """
    data = chronicle_request(
        client,
        method="GET",
        endpoint_path="legacyPlaybooks:legacyGetHtmlViewPresets",
        api_version=api_version,
    )

    return _extract_list(data, as_list)


def remove_playbook_permissions(
    client: "ChronicleClient",
    playbook_identifier: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> None:
    """Remove all access permissions for a playbook.

    After removal, the playbook will revert to the default permissions
    configured for the instance.

    Args:
        client: ChronicleClient instance.
        playbook_identifier: Original identifier of the playbook to remove
            permissions for.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        None

    Raises:
        APIError: If the API request fails.
    """
    chronicle_request(
        client,
        method="DELETE",
        endpoint_path="legacyPlaybooks:legacyPermissions",
        api_version=api_version,
        params={"workflowOriginalIdentifier": playbook_identifier},
        expected_status={200, 204},
    )


def list_playbook_permission_options(
    client: "ChronicleClient",
    environments: list[str],
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """List playbook access permission options for the given environments.

    Use this method to fetch permission options when creating a new playbook
    before a playbook identifier has been assigned.

    Args:
        client: ChronicleClient instance.
        environments: List of playbook environments to retrieve permission
            options for.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing userOptions and socRolesOptions lists.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyPermissionsOptions",
        api_version=api_version,
        json={"legacyPayload": environments},
    )


def list_playbooks_containing_action(
    client: "ChronicleClient",
    action_name: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[str]:
    """List all playbooks that include the specified action.

    Use this method to assess the impact of modifying or removing a shared
    security action.

    Args:
        client: ChronicleClient instance.
        action_name: Name of the action to search for.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of playbook identifiers instead of
            a dict with a payload list.

    Returns:
        If as_list is True: List of playbook identifier strings.
        If as_list is False: Dict with payload list of playbook identifier
            strings.

    Raises:
        APIError: If the API request fails.
    """
    data = chronicle_request(
        client,
        method="GET",
        endpoint_path=("legacyPlaybooks:legacyGetWorkflowsContainsActionAsync"),
        api_version=api_version,
        params={"actionName": action_name},
    )

    return _extract_list(data, as_list)


def list_playbooks_involving_actions(
    client: "ChronicleClient",
    action_id: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    """List all playbooks that include one or more of the specified actions.

    Use this method to understand the usage of individual automation steps
    across the playbook repository.

    Args:
        client: ChronicleClient instance.
        action_id: ID of the action to search for.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of playbooks by environment instead
            of a dict with a payload list.

    Returns:
        If as_list is True: List of ApiIntegrationPlaybookByEnvironment
            instances.
        If as_list is False: Dict with payload list of
            ApiIntegrationPlaybookByEnvironment instances.

    Raises:
        APIError: If the API request fails.
    """
    data = chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyGetWorkflowsInvolvingAction",
        api_version=api_version,
        json={"actionId": action_id},
    )

    return _extract_list(data, as_list)


def get_action_widget_template(
    client: "ChronicleClient",
    action_identifiers: list[str] | None = None,
    search_term: str | None = None,
    requested_page: int | None = None,
    page_size: int | None = None,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
    as_list: bool = False,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Get the action widget template for one or more action identifiers.

    Args:
        client: ChronicleClient instance.
        action_identifiers: List of action identifiers to retrieve widget
            templates for. Passed as a comma-separated string. Optional.
        search_term: Search term to filter widget templates by. Optional.
        requested_page: Page number to retrieve. Optional.
        page_size: Number of items per page. Optional.
        api_version: API version to use for the request. Default is V1ALPHA.
        as_list: If True, return a list of widget templates instead of a
            dict with a payload list.

    Returns:
        If as_list is True: List of LegacyPlaybookTemplateWidgetDefinition
            instances.
        If as_list is False: Dict with payload list of
            LegacyPlaybookTemplateWidgetDefinition instances.

    Raises:
        APIError: If the API request fails.
    """
    params = {
        "actionIdentifiers": (
            ",".join(action_identifiers)
            if action_identifiers is not None
            else None
        ),
        "searchTerm": search_term,
        "requestedPage": requested_page,
        "pageSize": page_size,
    }

    params = {k: v for k, v in params.items() if v is not None}

    data = chronicle_request(
        client,
        method="GET",
        endpoint_path="legacyPlaybooks:legacyActionWidgetTemplate",
        api_version=api_version,
        params=params if params else None,
    )

    return _extract_list(data, as_list)


def verify_transformer_example(
    client: "ChronicleClient",
    json: str,
    pipe: str,
    api_version: APIVersion | None = APIVersion.V1ALPHA,
) -> dict[str, Any]:
    """Verify the logical evaluation of a transformer using example input data.

    Use this method to test data transformation rules.

    Args:
        client: ChronicleClient instance.
        json: The JSON input data to test the transformer against.
        pipe: The transformer pipe expression to test.
        api_version: API version to use for the request. Default is V1ALPHA.

    Returns:
        Dict containing a payload field with the transformation result as a
        JSON string.

    Raises:
        APIError: If the API request fails.
    """
    return chronicle_request(
        client,
        method="POST",
        endpoint_path="legacyPlaybooks:legacyTestPipeExample",
        api_version=api_version,
        json={"json": json, "pipe": pipe},
    )
