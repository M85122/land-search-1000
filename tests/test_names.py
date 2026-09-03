from landsearch.match.names import canonical_tokens, normalize_name, owner_group_key, score_owner


def test_normalize_case_and_punct():
    assert normalize_name("  Doe, Jane-Ann  ") == "DOE, JANE ANN"


def test_last_first_tokens():
    assert canonical_tokens("DOE, JANE") == ["DOE", "JANE"]
    assert canonical_tokens("Jane Doe") == ["JANE", "DOE"]


def test_strips_llc_trust_tr_et_al():
    assert canonical_tokens("SMITH, JOHN TRUST") == ["SMITH", "JOHN"]
    assert canonical_tokens("ACME HOLDINGS LLC") == ["ACME", "HOLDINGS"]
    assert canonical_tokens("DOE, JANE ET AL") == ["DOE", "JANE"]
    assert canonical_tokens("DOE, JANE TR") == ["DOE", "JANE"]


def test_score_reorder_and_exact():
    assert score_owner("Jane Doe", "DOE, JANE") == 1.0
    assert score_owner("Jane Doe", "DOE, JANE TRUST") == 1.0
    assert score_owner("Acme LLC", "ACME LLC") == 1.0


def test_score_partial_and_collision_band():
    john = score_owner("Smith", "SMITH, JOHN A")
    mary = score_owner("Smith", "SMITH, MARY L TRUST")
    other = score_owner("Smith", "JONES, SMITH")
    assert john > 0.3 and mary > 0.3
    assert abs(john - mary) < 0.2
    assert john != 1.0
    assert other < john


def test_group_key_collapses_suffix():
    assert owner_group_key("DOE, JANE ET AL") == owner_group_key("Jane Doe")
