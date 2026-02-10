from tenants import parse_tenant_name


def test_parse_tenant_name_accept() -> None:
    org, env, host = parse_tenant_name("zuiddrecht-accept", "commonground.nu") or ("", "", "")
    assert org == "zuiddrecht"
    assert env == "accept"
    assert host == "zuiddrecht.accept.commonground.nu"


def test_parse_tenant_name_test() -> None:
    org, env, host = parse_tenant_name("lansingerland-test", "commonground.nu") or ("", "", "")
    assert org == "lansingerland"
    assert env == "test"
    assert host == "lansingerland.test.commonground.nu"


def test_parse_tenant_name_prod() -> None:
    org, env, host = parse_tenant_name("zuiddrecht-prod", "commonground.nu") or ("", "", "")
    assert org == "zuiddrecht"
    assert env == "prod"
    assert host == "zuiddrecht.commonground.nu"


def test_parse_tenant_name_unknown_suffix() -> None:
    assert parse_tenant_name("zuiddrecht-dev", "commonground.nu") is None
