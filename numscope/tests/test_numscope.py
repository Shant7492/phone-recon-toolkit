"""Offline unit tests. No network access is needed or attempted."""
from unittest import mock

import pytest

from core.analyzer import PhoneAnalyzer
from core.config import Config
from core.models import PhoneMetadata
from modules.dorks import CATEGORIES, DorkGenerator
from modules.providers import load_providers
from modules.providers.numverify import NumverifyProvider
from modules.risk import RiskScorer, level_for, longest_run

UK = "+442083661177"


def analyze(raw, region=None):
    return PhoneAnalyzer(default_region=region).analyze(raw)


def test_valid_uk_number_metadata():
    m = analyze(UK)
    assert m.parsed and m.is_valid and m.is_possible
    assert m.e164 == UK
    assert m.region_code == "GB"
    assert m.number_type == "FIXED_LINE"
    assert "Europe/London" in m.timezones


def test_national_format_needs_region():
    assert analyze("02083661177").parse_error_kind == "missing_region"
    assert analyze("02083661177", "GB").e164 == UK


def test_bad_plus_country_code_is_malformed():
    assert analyze("+999123456").parse_error_kind == "malformed"


def test_missing_region_is_not_penalised_as_unparseable():
    risk = RiskScorer().assess(analyze("02083661177"))
    assert all(f.name != "Unparseable" for f in risk.factors)
    assert any("No country code" in n for n in risk.notes)


def test_malformed_input_is_penalised():
    risk = RiskScorer().assess(analyze("+999123456"))
    assert any(f.name == "Unparseable" for f in risk.factors)


def test_voip_range_flagged():
    risk = RiskScorer().assess(analyze("+445612345678"))
    assert any(f.name == "Line type: VOIP" for f in risk.factors)


def test_caribbean_area_code_flagged_only_for_nanp():
    risk = RiskScorer("US").assess(analyze("+18095551234"))
    names = [f.name for f in risk.factors]
    assert "Callback-scam area code" in names
    assert "International origin" in names


def test_clean_number_scores_low():
    risk = RiskScorer("GB").assess(analyze(UK))
    assert risk.score == 0 and risk.level == "LOW"


def test_score_is_capped_and_levelled():
    assert level_for(0) == "LOW"
    assert level_for(20) == "MEDIUM"
    assert level_for(45) == "HIGH"
    assert level_for(70) == "CRITICAL"
    risk = RiskScorer().assess(analyze("1" * 30))
    assert risk.score <= 100


def test_longest_run():
    assert longest_run("5555555", 0) == 7
    assert longest_run("1234567", 1) == 7
    assert longest_run("7654321", -1) == 7
    assert longest_run("1357913", 1) == 1


def test_dorks_cover_all_categories_and_encode_urls():
    dorks = DorkGenerator(analyze(UK)).generate()
    assert {d.category for d in dorks} == set(CATEGORIES)
    url = dorks[0].url("google")
    assert url.startswith("https://www.google.com/search?q=")
    assert " " not in url and '"' not in url


def test_dorks_empty_for_junk_input():
    assert DorkGenerator(analyze("12")).generate() == []


def test_regional_directories_used():
    dorks = DorkGenerator(analyze(UK)).generate(["directories"])
    assert any("yell.com" in d.query for d in dorks)


def test_providers_skipped_without_key():
    active, skipped = load_providers(Config())
    assert active == [] and skipped == ["numverify"]


def test_unknown_provider_rejected():
    with pytest.raises(ValueError):
        load_providers(Config(), ["nope"])


def _resp(payload):
    r = mock.Mock()
    r.json.return_value = payload
    return r


def test_numverify_success_parsed():
    cfg = Config(numverify_api_key="SECRET")
    payload = {"valid": True, "line_type": "landline", "carrier": "X",
               "location": "London", "country_name": "UK"}
    with mock.patch("requests.get", return_value=_resp(payload)) as get:
        res = NumverifyProvider(cfg).lookup(analyze(UK))
    assert res.ok and res.data["line_type"] == "landline"
    assert get.call_args[0][0].startswith("https://")


def test_numverify_https_restriction_hint_and_no_downgrade():
    cfg = Config(numverify_api_key="SECRET")
    payload = {"success": False,
               "error": {"code": 105, "type": "https_access_restricted",
                         "info": "Your plan does not support HTTPS"}}
    with mock.patch("requests.get", return_value=_resp(payload)) as get:
        res = NumverifyProvider(cfg).lookup(analyze(UK))
    assert not res.ok and any("NUMVERIFY_ALLOW_HTTP" in n for n in res.notes)
    assert get.call_count == 1  # never silently retried over HTTP


def test_numverify_key_never_leaks_in_errors():
    import requests
    cfg = Config(numverify_api_key="SECRET")
    boom = requests.ConnectionError("failed: http://x/?access_key=SECRET")
    with mock.patch("requests.get", side_effect=boom):
        res = NumverifyProvider(cfg).lookup(analyze(UK))
    assert not res.ok and "SECRET" not in (res.error or "")


def test_numverify_skips_unparsed():
    cfg = Config(numverify_api_key="SECRET")
    res = NumverifyProvider(cfg).lookup(PhoneMetadata("x", parsed=False))
    assert not res.ok
