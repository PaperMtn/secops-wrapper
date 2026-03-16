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
"""Tests for Chronicle playbook functions."""

from unittest.mock import Mock, patch

import pytest

from secops.chronicle.client import ChronicleClient
from secops.chronicle.models import APIVersion, PlaybookType
from secops.chronicle.playbook.playbooks import (
    _extract_list,
    export_playbooks,
    import_playbooks,
    list_playbooks,
    get_playbook,
    save_playbook,
    clone_playbook,
    duplicate_playbook,
    duplicate_playbooks,
    delete_playbook,
    delete_playbooks,
    get_playbook_full,
    get_playbook_full_by_environment,
    get_playbook_by_environment,
    list_playbooks_by_environment,
    apply_playbook_approval,
    check_playbook_name_availability,
    list_enabled_playbooks,
    list_enabled_playbook_names,
    list_playbook_trigger_tags,
    get_playbook_stats,
    get_overview_template,
    get_overview_templates,
    list_html_view_presets,
    remove_playbook_permissions,
    list_playbook_permission_options,
    list_playbooks_containing_action,
    list_playbooks_involving_actions,
    get_action_widget_template,
    verify_transformer_example,
)
from secops.exceptions import APIError


@pytest.fixture
def chronicle_client():
    """Create a Chronicle client for testing."""
    with patch("secops.auth.SecOpsAuth") as mock_auth:
        mock_session = Mock()
        mock_session.headers = {}
        mock_auth.return_value.session = mock_session
        return ChronicleClient(
            customer_id="test-customer",
            project_id="test-project",
        )


@pytest.fixture
def mock_response() -> Mock:
    """Create a mock API response object."""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {}
    return mock


@pytest.fixture
def mock_error_response() -> Mock:
    """Create a mock error API response object."""
    mock = Mock()
    mock.status_code = 400
    mock.text = "Error message"
    mock.raise_for_status.side_effect = Exception("API Error")
    return mock


# -- _extract_list tests --


class TestExtractList:
    """Tests for the _extract_list helper function."""

    def test_extract_list_as_list_true_dict_with_key(self):
        """Test _extract_list returns the list under the key."""
        data = {"payload": [{"id": "1"}, {"id": "2"}]}
        result = _extract_list(data, as_list=True)
        assert result == [{"id": "1"}, {"id": "2"}]

    def test_extract_list_as_list_true_dict_missing_key(self):
        """Test _extract_list returns empty list when key is missing."""
        data = {"other": "value"}
        result = _extract_list(data, as_list=True)
        assert result == []

    def test_extract_list_as_list_true_custom_key(self):
        """Test _extract_list with a custom key."""
        data = {"objectsList": ["tag1", "tag2"]}
        result = _extract_list(data, as_list=True, key="objectsList")
        assert result == ["tag1", "tag2"]

    def test_extract_list_as_list_true_non_dict(self):
        """Test _extract_list returns data as-is when not a dict."""
        data = [{"id": "1"}]
        result = _extract_list(data, as_list=True)
        assert result == [{"id": "1"}]

    def test_extract_list_as_list_false(self):
        """Test _extract_list returns original dict when as_list=False."""
        data = {"payload": [{"id": "1"}], "metadata": "extra"}
        result = _extract_list(data, as_list=False)
        assert result == data

    def test_extract_list_as_list_false_non_dict(self):
        """Test _extract_list returns original non-dict when as_list=False."""
        data = "raw-string"
        result = _extract_list(data, as_list=False)
        assert result == "raw-string"


# -- export_playbooks tests --


def test_export_playbooks_success(chronicle_client):
    """Test export_playbooks returns raw bytes."""
    expected = b"PK\x03\x04fake-zip-data"

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request_bytes",
        return_value=expected,
    ) as mock_request:
        result = export_playbooks(
            chronicle_client, ["playbook-1", "playbook-2"]
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path="legacyPlaybooks:legacyExportDefinitions",
            api_version=APIVersion.V1ALPHA,
            params={
                "identifiers": "playbook-1,playbook-2",
                "alt": "media",
            },
            headers={
                "Accept": "application/zip, application/json",
            },
        )


def test_export_playbooks_error(chronicle_client):
    """Test export_playbooks propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request_bytes",
        side_effect=APIError("Failed to export playbooks"),
    ):
        with pytest.raises(APIError) as exc_info:
            export_playbooks(chronicle_client, ["playbook-1"])

        assert "Failed to export playbooks" in str(exc_info.value)


# -- import_playbooks tests --


def test_import_playbooks_success(chronicle_client):
    """Test import_playbooks returns expected result."""
    expected = {
        "workflowIdentifiers": ["playbook-1"],
        "mediaInfo": {"mediaType": "application/zip"},
    }

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_multipart_upload",
        return_value=expected,
    ) as mock_upload:
        result = import_playbooks(
            chronicle_client, b"PK\x03\x04fake-zip-data"
        )

        assert result == expected

        mock_upload.assert_called_once_with(
            chronicle_client,
            endpoint_path="legacyPlaybooks:legacyImportDefinitions",
            file_data=b"PK\x03\x04fake-zip-data",
            file_content_type="application/zip",
            api_version=APIVersion.V1ALPHA_UPLOAD,
        )


def test_import_playbooks_error(chronicle_client):
    """Test import_playbooks propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_multipart_upload",
        side_effect=APIError("Failed to import playbooks"),
    ):
        with pytest.raises(APIError) as exc_info:
            import_playbooks(chronicle_client, b"bad-data")

        assert "Failed to import playbooks" in str(exc_info.value)


# -- list_playbooks tests --


def test_list_playbooks_success(chronicle_client):
    """Test list_playbooks returns expected dict."""
    expected = {"payload": [{"name": "pb1"}, {"name": "pb2"}]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = list_playbooks(chronicle_client)

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyGetWorkflowMenuCards"
            ),
            api_version=APIVersion.V1ALPHA,
            json={
                "legacyPayload": [
                    PlaybookType.REGULAR.value,
                    PlaybookType.NESTED.value,
                ]
            },
        )


def test_list_playbooks_as_list(chronicle_client):
    """Test list_playbooks with as_list=True extracts payload."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={
            "payload": [{"name": "pb1"}],
        },
    ):
        result = list_playbooks(chronicle_client, as_list=True)

        assert result == [{"name": "pb1"}]


def test_list_playbooks_custom_types(chronicle_client):
    """Test list_playbooks with custom playbook types."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": []},
    ) as mock_request:
        list_playbooks(
            chronicle_client,
            playbook_types=[PlaybookType.REGULAR],
        )

        mock_request.assert_called_once()
        call_json = mock_request.call_args.kwargs["json"]
        assert call_json == {
            "legacyPayload": [PlaybookType.REGULAR.value],
        }


def test_list_playbooks_string_types(chronicle_client):
    """Test list_playbooks with string playbook types."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": []},
    ) as mock_request:
        list_playbooks(
            chronicle_client,
            playbook_types=["CUSTOM_TYPE"],
        )

        call_json = mock_request.call_args.kwargs["json"]
        assert call_json == {"legacyPayload": ["CUSTOM_TYPE"]}


def test_list_playbooks_error(chronicle_client):
    """Test list_playbooks propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed to list playbooks"),
    ):
        with pytest.raises(APIError) as exc_info:
            list_playbooks(chronicle_client)

        assert "Failed to list playbooks" in str(exc_info.value)


# -- get_playbook tests --


def test_get_playbook_success(chronicle_client):
    """Test get_playbook returns expected result."""
    expected = {"name": "pb1", "identifier": "test-id"}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = get_playbook(chronicle_client, "test-id")

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:legacyGetWorkflowMenuCard"
            ),
            api_version=APIVersion.V1ALPHA,
            params={"workflowIdentifier": "test-id"},
        )


def test_get_playbook_error(chronicle_client):
    """Test get_playbook propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed to get playbook"),
    ):
        with pytest.raises(APIError) as exc_info:
            get_playbook(chronicle_client, "test-id")

        assert "Failed to get playbook" in str(exc_info.value)


# -- save_playbook tests --


def test_save_playbook_success(chronicle_client):
    """Test save_playbook returns saved definition."""
    playbook_def = {"name": "pb1", "steps": []}
    expected = {"name": "pb1", "steps": [], "version": 2}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = save_playbook(chronicle_client, playbook_def)

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacySaveWorkflowDefinitions"
            ),
            api_version=APIVersion.V1ALPHA,
            json=playbook_def,
        )


def test_save_playbook_error(chronicle_client):
    """Test save_playbook propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed to save playbook"),
    ):
        with pytest.raises(APIError) as exc_info:
            save_playbook(chronicle_client, {"name": "pb1"})

        assert "Failed to save playbook" in str(exc_info.value)


# -- clone_playbook tests --


def test_clone_playbook_success(chronicle_client):
    """Test clone_playbook returns cloned definition."""
    playbook_def = {"name": "pb1"}
    expected = {"name": "pb1-clone"}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = clone_playbook(chronicle_client, playbook_def)

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path="legacyPlaybooks:legacyCloneWorkflow",
            api_version=APIVersion.V1ALPHA,
            json=playbook_def,
        )


def test_clone_playbook_error(chronicle_client):
    """Test clone_playbook propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed to clone playbook"),
    ):
        with pytest.raises(APIError) as exc_info:
            clone_playbook(chronicle_client, {"name": "pb1"})

        assert "Failed to clone playbook" in str(exc_info.value)


# -- duplicate_playbook tests --


def test_duplicate_playbook_success(chronicle_client):
    """Test duplicate_playbook returns duplicated definition."""
    playbook_def = {"name": "pb1"}
    expected = {"name": "pb1-dup"}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = duplicate_playbook(chronicle_client, playbook_def)

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyDuplicateWorkflow"
            ),
            api_version=APIVersion.V1ALPHA,
            json=playbook_def,
        )


def test_duplicate_playbook_error(chronicle_client):
    """Test duplicate_playbook propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed to duplicate playbook"),
    ):
        with pytest.raises(APIError) as exc_info:
            duplicate_playbook(chronicle_client, {"name": "pb1"})

        assert "Failed to duplicate playbook" in str(exc_info.value)


# -- duplicate_playbooks tests --


def test_duplicate_playbooks_required_fields(chronicle_client):
    """Test duplicate_playbooks with required fields only."""
    expected = {"payload": [{"name": "dup1"}, {"name": "dup2"}]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = duplicate_playbooks(
            chronicle_client,
            identifiers=["pb1", "pb2"],
            priority=1,
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyDuplicateWorkflows"
            ),
            api_version=APIVersion.V1ALPHA,
            json={
                "identifiers": ["pb1", "pb2"],
                "priority": 1,
            },
        )


def test_duplicate_playbooks_all_fields(chronicle_client):
    """Test duplicate_playbooks with all optional fields."""
    expected = {"payload": []}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = duplicate_playbooks(
            chronicle_client,
            identifiers=["pb1"],
            priority=2,
            category_id=10,
            environments=["env1", "env2"],
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyDuplicateWorkflows"
            ),
            api_version=APIVersion.V1ALPHA,
            json={
                "identifiers": ["pb1"],
                "priority": 2,
                "categoryId": 10,
                "environments": ["env1", "env2"],
            },
        )


def test_duplicate_playbooks_error(chronicle_client):
    """Test duplicate_playbooks propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed to duplicate playbooks"),
    ):
        with pytest.raises(APIError) as exc_info:
            duplicate_playbooks(
                chronicle_client, identifiers=["pb1"], priority=1
            )

        assert "Failed to duplicate playbooks" in str(exc_info.value)


# -- delete_playbook tests --


def test_delete_playbook_success(chronicle_client):
    """Test delete_playbook completes without error."""
    playbook_def = {"name": "pb1"}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
    ) as mock_request:
        delete_playbook(chronicle_client, playbook_def)

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyDeleteWorkflow"
            ),
            api_version=APIVersion.V1ALPHA,
            json=playbook_def,
            expected_status={200, 204},
        )


def test_delete_playbook_error(chronicle_client):
    """Test delete_playbook propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed to delete playbook"),
    ):
        with pytest.raises(APIError) as exc_info:
            delete_playbook(chronicle_client, {"name": "pb1"})

        assert "Failed to delete playbook" in str(exc_info.value)


# -- delete_playbooks tests --


def test_delete_playbooks_success(chronicle_client):
    """Test delete_playbooks returns expected result."""
    expected = {"results": [{"identifier": "pb1", "status": "OK"}]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = delete_playbooks(chronicle_client, ["pb1", "pb2"])

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyDeleteWorkflows"
            ),
            api_version=APIVersion.V1ALPHA,
            json={"identifiers": ["pb1", "pb2"]},
        )


def test_delete_playbooks_error(chronicle_client):
    """Test delete_playbooks propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed to delete playbooks"),
    ):
        with pytest.raises(APIError) as exc_info:
            delete_playbooks(chronicle_client, ["pb1"])

        assert "Failed to delete playbooks" in str(exc_info.value)


# -- get_playbook_full tests --


def test_get_playbook_full_success(chronicle_client):
    """Test get_playbook_full returns full definition."""
    expected = {
        "name": "pb1",
        "steps": [{"action": "act1"}],
        "connections": [],
    }

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = get_playbook_full(chronicle_client, "test-id")

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:"
                "legacyGetWorkflowFullInfoByIdentifier"
            ),
            api_version=APIVersion.V1ALPHA,
            params={"workflowIdentifier": "test-id"},
        )


def test_get_playbook_full_error(chronicle_client):
    """Test get_playbook_full propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed to get full playbook"),
    ):
        with pytest.raises(APIError) as exc_info:
            get_playbook_full(chronicle_client, "test-id")

        assert "Failed to get full playbook" in str(exc_info.value)


# -- get_playbook_full_by_environment tests --


def test_get_playbook_full_by_environment_success(chronicle_client):
    """Test get_playbook_full_by_environment returns result."""
    expected = {"name": "pb1", "environment": "prod"}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = get_playbook_full_by_environment(
            chronicle_client, "test-id"
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:"
                "legacyGetWorkflowFullInfoWithEnvFilterByIdentifier"
            ),
            api_version=APIVersion.V1ALPHA,
            params={"workflowIdentifier": "test-id"},
        )


def test_get_playbook_full_by_environment_error(chronicle_client):
    """Test get_playbook_full_by_environment propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            get_playbook_full_by_environment(
                chronicle_client, "test-id"
            )


# -- get_playbook_by_environment tests --


def test_get_playbook_by_environment_success(chronicle_client):
    """Test get_playbook_by_environment returns result."""
    expected = {"name": "pb1", "environment": "staging"}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = get_playbook_by_environment(
            chronicle_client, "test-id"
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:"
                "legacyGetWorkflowMenuCardWithEnvFilter"
            ),
            api_version=APIVersion.V1ALPHA,
            params={"workflowIdentifier": "test-id"},
        )


def test_get_playbook_by_environment_error(chronicle_client):
    """Test get_playbook_by_environment propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            get_playbook_by_environment(
                chronicle_client, "test-id"
            )


# -- list_playbooks_by_environment tests --


def test_list_playbooks_by_environment_success(chronicle_client):
    """Test list_playbooks_by_environment returns dict."""
    expected = {"payload": [{"name": "pb1"}]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = list_playbooks_by_environment(chronicle_client)

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:"
                "legacyGetWorkflowMenuCardsWithEnvFilter"
            ),
            api_version=APIVersion.V1ALPHA,
            json={
                "legacyPayload": [
                    PlaybookType.REGULAR.value,
                    PlaybookType.NESTED.value,
                ]
            },
        )


def test_list_playbooks_by_environment_as_list(chronicle_client):
    """Test list_playbooks_by_environment with as_list=True."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": [{"name": "pb1"}]},
    ):
        result = list_playbooks_by_environment(
            chronicle_client, as_list=True
        )

        assert result == [{"name": "pb1"}]


def test_list_playbooks_by_environment_custom_types(chronicle_client):
    """Test list_playbooks_by_environment with custom types."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": []},
    ) as mock_request:
        list_playbooks_by_environment(
            chronicle_client,
            playbook_types=[PlaybookType.NESTED],
        )

        call_json = mock_request.call_args.kwargs["json"]
        assert call_json == {
            "legacyPayload": [PlaybookType.NESTED.value],
        }


def test_list_playbooks_by_environment_error(chronicle_client):
    """Test list_playbooks_by_environment propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            list_playbooks_by_environment(chronicle_client)


# -- apply_playbook_approval tests --


def test_apply_playbook_approval_success(chronicle_client):
    """Test apply_playbook_approval returns result."""
    expected = {
        "status": "APPROVED",
        "caseId": "case-1",
        "actionName": "manual-action",
        "approvalLinkActionType": "APPROVE",
    }

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = apply_playbook_approval(
            chronicle_client,
            encrypted_data="enc-data",
            hashed_encrypted_data="hash-data",
            is_approved=True,
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyApplyApprovalLink"
            ),
            api_version=APIVersion.V1ALPHA,
            json={
                "encryptedData": "enc-data",
                "hashedEncryptedData": "hash-data",
                "isApproved": True,
            },
        )


def test_apply_playbook_approval_without_is_approved(chronicle_client):
    """Test apply_playbook_approval without optional is_approved."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"status": "PENDING"},
    ) as mock_request:
        apply_playbook_approval(
            chronicle_client,
            encrypted_data="enc-data",
            hashed_encrypted_data="hash-data",
        )

        call_json = mock_request.call_args.kwargs["json"]
        assert "isApproved" not in call_json


def test_apply_playbook_approval_error(chronicle_client):
    """Test apply_playbook_approval propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            apply_playbook_approval(
                chronicle_client,
                encrypted_data="enc",
                hashed_encrypted_data="hash",
            )


# -- check_playbook_name_availability tests --


def test_check_playbook_name_availability_available(chronicle_client):
    """Test check_playbook_name_availability with available name."""
    expected = {}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = check_playbook_name_availability(
            chronicle_client, "MyPlaybook"
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:"
                "legacyCheckWorkflowNameInDifferentEnvironments"
            ),
            api_version=APIVersion.V1ALPHA,
            json={"wfName": "MyPlaybook"},
        )


def test_check_playbook_name_availability_taken(chronicle_client):
    """Test check_playbook_name_availability with taken name."""
    expected = {"payload": "existing-id"}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ):
        result = check_playbook_name_availability(
            chronicle_client, "TakenPlaybook"
        )

        assert result["payload"] == "existing-id"


def test_check_playbook_name_availability_error(chronicle_client):
    """Test check_playbook_name_availability propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            check_playbook_name_availability(
                chronicle_client, "MyPlaybook"
            )


# -- list_enabled_playbooks tests --


def test_list_enabled_playbooks_success(chronicle_client):
    """Test list_enabled_playbooks returns dict."""
    expected = {"payload": [{"name": "pb1"}]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = list_enabled_playbooks(chronicle_client)

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyGetEnabledWFCards"
            ),
            api_version=APIVersion.V1ALPHA,
            json={},
        )


def test_list_enabled_playbooks_with_environment(chronicle_client):
    """Test list_enabled_playbooks with case_environment."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": []},
    ) as mock_request:
        list_enabled_playbooks(
            chronicle_client, case_environment="prod"
        )

        call_json = mock_request.call_args.kwargs["json"]
        assert call_json == {"caseEnvironment": "prod"}


def test_list_enabled_playbooks_as_list(chronicle_client):
    """Test list_enabled_playbooks with as_list=True."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": [{"name": "pb1"}]},
    ):
        result = list_enabled_playbooks(
            chronicle_client, as_list=True
        )

        assert result == [{"name": "pb1"}]


def test_list_enabled_playbooks_error(chronicle_client):
    """Test list_enabled_playbooks propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            list_enabled_playbooks(chronicle_client)


# -- list_enabled_playbook_names tests --


def test_list_enabled_playbook_names_success(chronicle_client):
    """Test list_enabled_playbook_names returns dict."""
    expected = {"payload": ["Playbook A", "Playbook B"]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = list_enabled_playbook_names(chronicle_client)

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:legacyGetEnabledWFNames"
            ),
            api_version=APIVersion.V1ALPHA,
        )


def test_list_enabled_playbook_names_as_list(chronicle_client):
    """Test list_enabled_playbook_names with as_list=True."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": ["Playbook A"]},
    ):
        result = list_enabled_playbook_names(
            chronicle_client, as_list=True
        )

        assert result == ["Playbook A"]


def test_list_enabled_playbook_names_error(chronicle_client):
    """Test list_enabled_playbook_names propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            list_enabled_playbook_names(chronicle_client)


# -- list_playbook_trigger_tags tests --


def test_list_playbook_trigger_tags_success(chronicle_client):
    """Test list_playbook_trigger_tags returns dict."""
    expected = {
        "objectsList": ["tag1", "tag2"],
        "totalCount": 2,
    }

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = list_playbook_trigger_tags(chronicle_client)

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyGetTriggerTags"
            ),
            api_version=APIVersion.V1ALPHA,
            json={},
        )


def test_list_playbook_trigger_tags_with_options(chronicle_client):
    """Test list_playbook_trigger_tags with optional parameters."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"objectsList": ["tag1"]},
    ) as mock_request:
        list_playbook_trigger_tags(
            chronicle_client,
            search_term="malware",
            requested_page=1,
            page_size=10,
        )

        call_json = mock_request.call_args.kwargs["json"]
        assert call_json == {
            "searchTerm": "malware",
            "requestedPage": 1,
            "pageSize": 10,
        }


def test_list_playbook_trigger_tags_as_list(chronicle_client):
    """Test list_playbook_trigger_tags with as_list=True."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"objectsList": ["tag1", "tag2"]},
    ):
        result = list_playbook_trigger_tags(
            chronicle_client, as_list=True
        )

        assert result == ["tag1", "tag2"]


def test_list_playbook_trigger_tags_error(chronicle_client):
    """Test list_playbook_trigger_tags propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            list_playbook_trigger_tags(chronicle_client)


# -- get_playbook_stats tests --


def test_get_playbook_stats_success(chronicle_client):
    """Test get_playbook_stats returns expected result."""
    expected = {"stepsStatsMap": {}, "flowsStatsMap": {}}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = get_playbook_stats(chronicle_client, "test-pb")

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyGetPlaybookStatsMap"
            ),
            api_version=APIVersion.V1ALPHA,
            json={
                "originalWorkflowIdentifier": "test-pb",
            },
        )


def test_get_playbook_stats_with_time_range(chronicle_client):
    """Test get_playbook_stats with time range parameters."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={},
    ) as mock_request:
        get_playbook_stats(
            chronicle_client,
            "test-pb",
            from_unix_time_ms="1000",
            to_unix_time_ms="2000",
        )

        call_json = mock_request.call_args.kwargs["json"]
        assert call_json == {
            "originalWorkflowIdentifier": "test-pb",
            "fromUnixTimeMs": "1000",
            "toUnixTimeMs": "2000",
        }


def test_get_playbook_stats_error(chronicle_client):
    """Test get_playbook_stats propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            get_playbook_stats(chronicle_client, "test-pb")


# -- get_overview_template tests --


def test_get_overview_template_success(chronicle_client):
    """Test get_overview_template returns expected result."""
    expected = {"identifier": "tmpl-1", "name": "Overview"}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = get_overview_template(chronicle_client, "tmpl-1")

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:legacyGetOverviewTemplate"
            ),
            api_version=APIVersion.V1ALPHA,
            params={"templateIdentifier": "tmpl-1"},
        )


def test_get_overview_template_error(chronicle_client):
    """Test get_overview_template propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            get_overview_template(chronicle_client, "tmpl-1")


# -- get_overview_templates tests --


def test_get_overview_templates_success(chronicle_client):
    """Test get_overview_templates returns dict."""
    expected = {"payload": [{"identifier": "tmpl-1"}]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = get_overview_templates(chronicle_client, "pb-1")

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyGetOverviewTemplates"
            ),
            api_version=APIVersion.V1ALPHA,
            json={"playbookIdentifier": "pb-1"},
        )


def test_get_overview_templates_as_list(chronicle_client):
    """Test get_overview_templates with as_list=True."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": [{"identifier": "tmpl-1"}]},
    ):
        result = get_overview_templates(
            chronicle_client, "pb-1", as_list=True
        )

        assert result == [{"identifier": "tmpl-1"}]


def test_get_overview_templates_error(chronicle_client):
    """Test get_overview_templates propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            get_overview_templates(chronicle_client, "pb-1")


# -- list_html_view_presets tests --


def test_list_html_view_presets_success(chronicle_client):
    """Test list_html_view_presets returns dict."""
    expected = {
        "payload": [
            {"name": "preset-1", "identifier": "p1"},
        ]
    }

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = list_html_view_presets(chronicle_client)

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:legacyGetHtmlViewPresets"
            ),
            api_version=APIVersion.V1ALPHA,
        )


def test_list_html_view_presets_as_list(chronicle_client):
    """Test list_html_view_presets with as_list=True."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={
            "payload": [{"name": "preset-1"}],
        },
    ):
        result = list_html_view_presets(
            chronicle_client, as_list=True
        )

        assert result == [{"name": "preset-1"}]


def test_list_html_view_presets_error(chronicle_client):
    """Test list_html_view_presets propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            list_html_view_presets(chronicle_client)


# -- remove_playbook_permissions tests --


def test_remove_playbook_permissions_success(chronicle_client):
    """Test remove_playbook_permissions completes without error."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
    ) as mock_request:
        remove_playbook_permissions(chronicle_client, "pb-orig-id")

        mock_request.assert_called_once_with(
            chronicle_client,
            method="DELETE",
            endpoint_path="legacyPlaybooks:legacyPermissions",
            api_version=APIVersion.V1ALPHA,
            params={
                "workflowOriginalIdentifier": "pb-orig-id",
            },
            expected_status={200, 204},
        )


def test_remove_playbook_permissions_error(chronicle_client):
    """Test remove_playbook_permissions propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            remove_playbook_permissions(
                chronicle_client, "pb-orig-id"
            )


# -- list_playbook_permission_options tests --


def test_list_playbook_permission_options_success(chronicle_client):
    """Test list_playbook_permission_options returns result."""
    expected = {
        "userOptions": [{"name": "user1"}],
        "socRolesOptions": [{"name": "role1"}],
    }

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = list_playbook_permission_options(
            chronicle_client, ["env1", "env2"]
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyPermissionsOptions"
            ),
            api_version=APIVersion.V1ALPHA,
            json={"legacyPayload": ["env1", "env2"]},
        )


def test_list_playbook_permission_options_error(chronicle_client):
    """Test list_playbook_permission_options propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            list_playbook_permission_options(
                chronicle_client, ["env1"]
            )


# -- list_playbooks_containing_action tests --


def test_list_playbooks_containing_action_success(chronicle_client):
    """Test list_playbooks_containing_action returns dict."""
    expected = {"payload": ["pb1", "pb2"]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = list_playbooks_containing_action(
            chronicle_client, "MyAction"
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:"
                "legacyGetWorkflowsContainsActionAsync"
            ),
            api_version=APIVersion.V1ALPHA,
            params={"actionName": "MyAction"},
        )


def test_list_playbooks_containing_action_as_list(chronicle_client):
    """Test list_playbooks_containing_action with as_list=True."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": ["pb1"]},
    ):
        result = list_playbooks_containing_action(
            chronicle_client, "MyAction", as_list=True
        )

        assert result == ["pb1"]


def test_list_playbooks_containing_action_error(chronicle_client):
    """Test list_playbooks_containing_action propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            list_playbooks_containing_action(
                chronicle_client, "MyAction"
            )


# -- list_playbooks_involving_actions tests --


def test_list_playbooks_involving_actions_success(chronicle_client):
    """Test list_playbooks_involving_actions returns dict."""
    expected = {"payload": [{"environment": "prod", "playbooks": []}]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = list_playbooks_involving_actions(
            chronicle_client, "action-id-1"
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:"
                "legacyGetWorkflowsInvolvingAction"
            ),
            api_version=APIVersion.V1ALPHA,
            json={"actionId": "action-id-1"},
        )


def test_list_playbooks_involving_actions_as_list(chronicle_client):
    """Test list_playbooks_involving_actions with as_list=True."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={
            "payload": [{"environment": "prod"}],
        },
    ):
        result = list_playbooks_involving_actions(
            chronicle_client, "action-id-1", as_list=True
        )

        assert result == [{"environment": "prod"}]


def test_list_playbooks_involving_actions_error(chronicle_client):
    """Test list_playbooks_involving_actions propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            list_playbooks_involving_actions(
                chronicle_client, "action-id-1"
            )


# -- get_action_widget_template tests --


def test_get_action_widget_template_success(chronicle_client):
    """Test get_action_widget_template returns dict."""
    expected = {"payload": [{"widget": "data"}]}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = get_action_widget_template(
            chronicle_client,
            action_identifiers=["act-1", "act-2"],
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:legacyActionWidgetTemplate"
            ),
            api_version=APIVersion.V1ALPHA,
            params={"actionIdentifiers": "act-1,act-2"},
        )


def test_get_action_widget_template_with_search(chronicle_client):
    """Test get_action_widget_template with search and pagination."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": []},
    ) as mock_request:
        get_action_widget_template(
            chronicle_client,
            search_term="email",
            requested_page=2,
            page_size=5,
        )

        call_params = mock_request.call_args.kwargs["params"]
        assert call_params == {
            "searchTerm": "email",
            "requestedPage": 2,
            "pageSize": 5,
        }


def test_get_action_widget_template_no_params(chronicle_client):
    """Test get_action_widget_template with no optional params."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": []},
    ) as mock_request:
        get_action_widget_template(chronicle_client)

        mock_request.assert_called_once_with(
            chronicle_client,
            method="GET",
            endpoint_path=(
                "legacyPlaybooks:legacyActionWidgetTemplate"
            ),
            api_version=APIVersion.V1ALPHA,
            params=None,
        )


def test_get_action_widget_template_as_list(chronicle_client):
    """Test get_action_widget_template with as_list=True."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value={"payload": [{"widget": "data"}]},
    ):
        result = get_action_widget_template(
            chronicle_client,
            action_identifiers=["act-1"],
            as_list=True,
        )

        assert result == [{"widget": "data"}]


def test_get_action_widget_template_error(chronicle_client):
    """Test get_action_widget_template propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            get_action_widget_template(chronicle_client)


# -- test_transformer_example tests --


def test_test_transformer_example_success(chronicle_client):
    """Test test_transformer_example returns result."""
    expected = {"payload": '{"result": "transformed"}'}

    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        return_value=expected,
    ) as mock_request:
        result = verify_transformer_example(
            chronicle_client,
            json='{"key": "value"}',
            pipe="key | upper",
        )

        assert result == expected

        mock_request.assert_called_once_with(
            chronicle_client,
            method="POST",
            endpoint_path=(
                "legacyPlaybooks:legacyTestPipeExample"
            ),
            api_version=APIVersion.V1ALPHA,
            json={
                "json": '{"key": "value"}',
                "pipe": "key | upper",
            },
        )


def test_test_transformer_example_error(chronicle_client):
    """Test test_transformer_example propagates APIError."""
    with patch(
        "secops.chronicle.playbook.playbooks.chronicle_request",
        side_effect=APIError("Failed"),
    ):
        with pytest.raises(APIError):
            verify_transformer_example(
                chronicle_client,
                json='{"key": "value"}',
                pipe="key | upper",
            )

