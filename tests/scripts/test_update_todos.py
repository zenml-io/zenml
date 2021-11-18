import os

import pytest


@pytest.fixture(scope="module", autouse=True)
def setup_environment():
    os.environ["JIRA_BASE_URL"] = ""
    os.environ["JIRA_USERNAME"] = ""
    os.environ["JIRA_API_TOKEN"] = ""

    os.environ["JIRA_BOARD_ID"] = ""
    os.environ["JIRA_ISSUE_TYPE_ID"] = ""
    os.environ["JIRA_DONE_STATUS_CATEGORY_ID"] = "-1"
    os.environ["JIRA_ISSUE_LABEL"] = ""


def test_todo_detection(tmp_path):
    """Tests that only correctly specified todos are detected."""
    from scripts.update_todos import find_todos

    file = tmp_path / "test.py"

    file.write_text(
        """
            # TODO [LOW]: valid todo

            # TODO: missing priority

            # TODO [MEDIU]: invalid priority

            # TODO[MEDIUM]: multiline
            #  todo

            # TODO[HIGH]: invalid multiline
            # todo (no indentation)

            # TODO [ABC-123]: valid issue key

            # TODO [123-ABC]: invalid issue key

            # TODO [LOWEST]:
            # TODO [HIGHEST]: invalid multiline
                #  over-indented
        """
    )
    todos_without_issue, todos_with_issue = find_todos(file)

    assert len(todos_with_issue) == 1
    assert todos_with_issue[0].issue_key == "ABC-123"
    assert todos_with_issue[0].filepath == str(file)
    assert todos_with_issue[0].description == "valid issue key"

    assert len(todos_without_issue) == 5
    expected_priorities = ["LOW", "MEDIUM", "HIGH", "LOWEST", "HIGHEST"]
    expected_descriptions = [
        "valid todo",
        "multiline todo",
        "invalid multiline",
        "",
        "invalid multiline",
    ]

    for todo, expected_priority, expected_description in zip(
        todos_without_issue, expected_priorities, expected_descriptions
    ):
        assert todo.priority == expected_priority
        assert todo.filepath == str(file)
        assert todo.description == expected_description


def test_todo_issue_key_insertion(tmp_path):
    """Tests that todo priorities are correctly replaced by jira issue keys."""
    from scripts.update_todos import Todo, update_file_with_issue_keys

    file = tmp_path / "test.py"

    file.write_text(
        """
            # TODO [LOW]: some valid todo

            # TODO [ABC-123]: todo with existing issue key

            # TODO: missing priority

            # TODO [HIGHEST]: another
            #  valid todo
        """
    )

    todos = [
        Todo(
            filepath=str(file),
            description="some valid todo",
            priority="LOW",
            issue_key="TEST-1",
        ),
        Todo(
            filepath=str(file),
            description="another valid todo",
            priority="HIGHEST",
            issue_key="TEST-2",
        ),
    ]

    update_file_with_issue_keys(file, todos)

    expected_file_content = """
            # TODO [TEST-1]: some valid todo

            # TODO [ABC-123]: todo with existing issue key

            # TODO: missing priority

            # TODO [TEST-2]: another
            #  valid todo
        """

    assert file.read_text() == expected_file_content


def test_removing_of_closed_todos(tmp_path):
    """Tests that todos that reference closed jira issues get deleted."""

    from scripts.update_todos import (
        JiraIssue,
        Todo,
        remove_todos_for_closed_issues,
    )

    file = tmp_path / "test.py"

    file.write_text(
        """
            # TODO [LOW]: todo without issue reference

            # TODO [TEST-1]: todo for
            #  closed issue
            # TODO: missing priority

            # TODO [TEST-2]: todo with open issue
        """
    )

    todos = [
        Todo(
            filepath=str(file),
            description="todo for closed issue",
            issue_key="TEST-1",
        ),
        Todo(
            filepath=str(file),
            description="todo with open issue",
            issue_key="TEST-2",
        ),
    ]

    issues = [
        JiraIssue(key="TEST-1", done=True),
        JiraIssue(key="TEST-2", done=False),
    ]

    remove_todos_for_closed_issues(file, todos, issues)

    expected_file_content = """
            # TODO [LOW]: todo without issue reference

            # TODO: missing priority

            # TODO [TEST-2]: todo with open issue
        """

    assert file.read_text() == expected_file_content
