"""Case E29: what the errors of the domain guarantee by themselves."""

from __future__ import annotations

import pytest

from app.constants import Environment
from app.domain.errors import DomainError, ForbiddenError, TestDataNotAllowedError


def test_the_base_error_cannot_be_raised_without_a_category() -> None:
    with pytest.raises(TypeError):
        DomainError("something_expected")


def test_the_error_of_the_test_data_script_is_declared_with_the_others() -> None:
    error = TestDataNotAllowedError(Environment.DEMO)

    assert isinstance(error, ForbiddenError)
    assert error.code == "test_data_not_allowed"
    assert error.environment is Environment.DEMO
