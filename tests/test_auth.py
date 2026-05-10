from __future__ import annotations

import pytest

from workforceiq.auth import RoleName, parse_role
from workforceiq.errors import ValidationError


def test_parse_role_accepts_known_role():
    assert parse_role("HR_MANAGER") == RoleName.HR_MANAGER


def test_parse_role_rejects_missing_role():
    with pytest.raises(ValidationError, match="required"):
        parse_role(None)


def test_parse_role_rejects_unknown_role():
    with pytest.raises(ValidationError, match="invalid"):
        parse_role("CEO")
