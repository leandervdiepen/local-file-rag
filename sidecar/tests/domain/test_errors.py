from __future__ import annotations

import pytest

from sidecar.domain.errors import DomainError, NotFoundError, ValidationError


def test_domain_error_carries_message_and_default_code() -> None:
    error = DomainError("something is wrong")

    assert error.message == "something is wrong"
    assert error.code == "domain_error"
    assert str(error) == "something is wrong"


def test_not_found_error_has_its_own_code_and_is_a_domain_error() -> None:
    error = NotFoundError("page 7 does not exist")

    assert error.code == "not_found"
    assert isinstance(error, DomainError)


def test_validation_error_has_its_own_code_and_is_a_domain_error() -> None:
    error = ValidationError("folder path is empty")

    assert error.code == "invalid_request"
    assert isinstance(error, DomainError)


def test_domain_errors_are_raisable_and_catchable_by_the_base_type() -> None:
    with pytest.raises(DomainError):
        raise NotFoundError("missing")
