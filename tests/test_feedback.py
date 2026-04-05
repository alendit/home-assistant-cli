"""Tests for the feedback CLI plugin."""

import json
from unittest import mock

from click.testing import CliRunner

import homeassistant_cli.cli as cli


def test_feedback_retrieve_returns_unresolved_items_by_default() -> None:
    """Retrieve should hide completed feedback unless --all is requested."""
    with mock.patch(
        "homeassistant_cli.remote.get_config_entries",
        return_value=[
            {
                "entry_id": "entry-1",
                "domain": "local_todo",
                "title": "Codex Feedback",
            }
        ],
    ):
        with mock.patch(
            "homeassistant_cli.remote.get_entities",
            return_value=[
                {"entity_id": "todo.codex_feedback", "config_entry_id": "entry-1"}
            ],
        ):
            with mock.patch(
                "homeassistant_cli.remote.get_todo_items",
                return_value=[
                    {
                        "uid": "fb-2",
                        "summary": "Already fixed",
                        "status": "completed",
                        "description": json.dumps(
                            {"created_at": "2026-04-05T01:00:00+00:00", "source": "agent"}
                        ),
                        "completed": "2026-04-05T02:00:00+00:00",
                    },
                    {
                        "uid": "fb-1",
                        "summary": "Wrong entity id used",
                        "status": "needs_action",
                        "description": json.dumps(
                            {
                                "created_at": "2026-04-05T03:00:00+00:00",
                                "source": "agent",
                                "suggestions": ["Check the full entity id first."],
                            }
                        ),
                    },
                ],
            ):
                runner = CliRunner()
                result = runner.invoke(
                    cli.cli,
                    ["--output=json", "feedback", "retrieve"],
                    catch_exceptions=False,
                )

    assert result.exit_code == 0
    assert json.loads(result.output) == [
        {
            "feedback_id": "fb-1",
            "issue": "Wrong entity id used",
            "status": "needs_action",
            "created_at": "2026-04-05T03:00:00+00:00",
            "completed_at": None,
            "source": "agent",
            "session_key": None,
            "turn_id": None,
            "profile": None,
            "details": None,
            "suggestions": ["Check the full entity id first."],
            "suggestions_text": "Check the full entity id first.",
            "entity_id": "todo.codex_feedback",
        }
    ]


def test_feedback_submit_creates_local_todo_list_if_needed() -> None:
    """Submit should provision the Local To-do list on first use."""
    with mock.patch(
        "homeassistant_cli.remote.get_config_entries",
        side_effect=[
            [],
            [
                {
                    "entry_id": "entry-1",
                    "domain": "local_todo",
                    "title": "Codex Feedback",
                }
            ],
        ],
    ):
        with mock.patch(
            "homeassistant_cli.remote.get_config_entry_flow_handlers",
            return_value=["local_todo", "mqtt"],
        ) as handlers:
            with mock.patch(
                "homeassistant_cli.remote.init_config_entry_flow",
                return_value={"type": "form", "flow_id": "flow-1"},
            ) as init_flow:
                with mock.patch(
                    "homeassistant_cli.remote.continue_config_entry_flow",
                    return_value={"type": "create_entry"},
                ) as continue_flow:
                    with mock.patch(
                        "homeassistant_cli.remote.get_entities",
                        return_value=[
                            {
                                "entity_id": "todo.codex_feedback",
                                "config_entry_id": "entry-1",
                            }
                        ],
                    ):
                        with mock.patch(
                            "homeassistant_cli.remote.call_service",
                            return_value=[],
                        ) as call_service:
                            with mock.patch(
                                "homeassistant_cli.remote.get_todo_items",
                                return_value=[
                                    {
                                        "uid": "fb-1",
                                        "summary": "Wrong entity id used",
                                        "status": "needs_action",
                                        "description": json.dumps(
                                            {
                                                "created_at": "2026-04-05T03:00:00+00:00",
                                                "source": "agent",
                                                "session_key": "conversation:test",
                                            }
                                        ),
                                    }
                                ],
                            ):
                                with mock.patch(
                                    "homeassistant_cli.plugins.feedback.datetime"
                                ) as mocked_datetime:
                                    mocked_datetime.now.return_value.isoformat.return_value = (
                                        "2026-04-05T03:00:00+00:00"
                                    )
                                    mocked_datetime.now.return_value = mock.Mock(
                                        isoformat=mock.Mock(
                                            return_value="2026-04-05T03:00:00+00:00"
                                        )
                                    )
                                    mocked_datetime.now.side_effect = lambda tz=None: mock.Mock(
                                        isoformat=mock.Mock(
                                            return_value="2026-04-05T03:00:00+00:00"
                                        )
                                    )

                                    runner = CliRunner()
                                    result = runner.invoke(
                                        cli.cli,
                                        [
                                            "--output=json",
                                            "feedback",
                                            "submit",
                                            "Wrong entity id used",
                                            "--session-key",
                                            "conversation:test",
                                        ],
                                        catch_exceptions=False,
                                    )

    assert result.exit_code == 0
    handlers.assert_called_once()
    init_flow.assert_called_once_with(mock.ANY, "local_todo")
    continue_flow.assert_called_once_with(
        mock.ANY, "flow-1", {"todo_list_name": "Codex Feedback"}
    )
    call_service.assert_called_once()
    payload = call_service.call_args.args[3]
    assert payload["entity_id"] == "todo.codex_feedback"
    assert payload["item"] == "Wrong entity id used"
    assert json.loads(payload["description"]) == {
        "created_at": "2026-04-05T03:00:00+00:00",
        "details": None,
        "profile": None,
        "session_key": "conversation:test",
        "source": "agent",
        "suggestions": [],
        "turn_id": None,
    }


def test_feedback_mark_done_updates_requested_ids() -> None:
    """Mark-done should mark each requested feedback item as completed."""
    with mock.patch(
        "homeassistant_cli.remote.get_config_entries",
        return_value=[
            {
                "entry_id": "entry-1",
                "domain": "local_todo",
                "title": "Codex Feedback",
            }
        ],
    ):
        with mock.patch(
            "homeassistant_cli.remote.get_entities",
            return_value=[
                {"entity_id": "todo.codex_feedback", "config_entry_id": "entry-1"}
            ],
        ):
            with mock.patch(
                "homeassistant_cli.remote.get_todo_items",
                return_value=[
                    {
                        "uid": "fb-1",
                        "summary": "Wrong entity id used",
                        "status": "needs_action",
                        "description": json.dumps(
                            {"created_at": "2026-04-05T03:00:00+00:00"}
                        ),
                    },
                    {
                        "uid": "fb-2",
                        "summary": "Missing reload step",
                        "status": "needs_action",
                        "description": json.dumps(
                            {"created_at": "2026-04-05T04:00:00+00:00"}
                        ),
                    },
                ],
            ):
                with mock.patch(
                    "homeassistant_cli.remote.call_service",
                    return_value=[],
                ) as call_service:
                    runner = CliRunner()
                    result = runner.invoke(
                        cli.cli,
                        [
                            "--output=json",
                            "feedback",
                            "mark-done",
                            "fb-1",
                            "fb-2",
                        ],
                        catch_exceptions=False,
                    )

    assert result.exit_code == 0
    assert call_service.call_count == 2
    assert json.loads(result.output) == {
        "updated_ids": ["fb-1", "fb-2"],
        "count": 2,
        "entity_id": "todo.codex_feedback",
    }
