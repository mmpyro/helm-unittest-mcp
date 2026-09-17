"""Shared parameter types for tool signatures.

Declaring these as ``Literal`` puts the allowed values in the JSON schema as an
``enum`` instead of spelling them out in prose inside the tool description.
"""

from typing import Literal


OutputType = Literal["xunit", "junit", "nunit", "sonar"]
IncludeCases = Literal["failed_only", "all", "none"]
