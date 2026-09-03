import pytest

from landsearch.atlas import CoverageError, resolve_county
from landsearch.cli import main


def test_unknown_county_raises():
    with pytest.raises(CoverageError, match="No coverage"):
        resolve_county("IL", "Cook")


def test_missing_state_raises():
    with pytest.raises(CoverageError, match="required"):
        resolve_county("", "Kane")


def test_cli_no_coverage_exit_code():
    assert main(["lookup", "Jane Doe", "--state", "IL", "--county", "Cook"]) == 2


def test_cli_no_state():
    with pytest.raises(SystemExit):
        main(["lookup", "Jane Doe"])


def test_coverage_lists_verified():
    assert main(["coverage"]) == 0
