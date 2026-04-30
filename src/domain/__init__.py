"""Release Pilot domain layer -- entities, enums, interfaces, and exceptions."""

from .entities import ChangeGroup, CommitDelta, ReleaseDraft, ReleaseSpec
from .enums import BumpKind, ChangeType, ReleaseStrategy, TriggerSource
from .exceptions import (
    ConfigurationError,
    GenerationError,
    GitHubAPIError,
    ReleasePilotError,
    TagResolutionError,
)
from .interfaces import (
    ICommitClassifier,
    IConfigLoader,
    IDeltaCalculator,
    IGitHubClient,
    INotesGenerator,
    ITagComparer,
)

__all__ = [
    # Enums
    "ChangeType",
    "ReleaseStrategy",
    "BumpKind",
    "TriggerSource",
    # Entities
    "CommitDelta",
    "ChangeGroup",
    "ReleaseSpec",
    "ReleaseDraft",
    # Interfaces
    "IGitHubClient",
    "ITagComparer",
    "IDeltaCalculator",
    "ICommitClassifier",
    "INotesGenerator",
    "IConfigLoader",
    # Exceptions
    "ReleasePilotError",
    "TagResolutionError",
    "GitHubAPIError",
    "GenerationError",
    "ConfigurationError",
]
