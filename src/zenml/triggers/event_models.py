from typing import List

from pydantic import BaseModel


class Event(BaseModel):
    """BaseModel for all Events"""


# Just to help design the abstraction, a concrete Event
class GithubEvent(Event):
    """Model for all GithubEvents."""
    # For matching to triggers
    repo: str
    ref: str
    action: List[str]
    # Metadata for auditability, frontend?
    sender: str
    # Used to enable the Action
    commit: str

    def __eq__(self, other):
        if isinstance(other, GithubEvent):
            return (self.repo == other.repo
                    and self.ref == other.ref
                    and self.action == other.action)
        return False