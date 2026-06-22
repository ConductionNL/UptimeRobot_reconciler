from tenants import load_tenants, parse_tenant_name


def test_parse_tenant_name_accept() -> None:
    org, env, host = parse_tenant_name("zuiddrecht-accept", "commonground.nu") or ("", "", "")
    assert org == "zuiddrecht"
    assert env == "accept"
    assert host == "zuiddrecht.accept.commonground.nu"


def test_parse_tenant_name_prod() -> None:
    org, env, host = parse_tenant_name("zuiddrecht-prod", "commonground.nu") or ("", "", "")
    assert org == "zuiddrecht"
    assert env == "prod"
    assert host == "zuiddrecht.commonground.nu"


def test_parse_tenant_name_test_is_skipped() -> None:
    # Only accept/prod are monitored; test/demo are not.
    assert parse_tenant_name("lansingerland-test", "commonground.nu") is None
    assert parse_tenant_name("conduction-demo", "commonground.nu") is None


def test_parse_tenant_name_unknown_suffix() -> None:
    assert parse_tenant_name("zuiddrecht-dev", "commonground.nu") is None


def _write(tmp_path, name, fname, hostname=None):
    body = f"tenant:\n  name: {name}\n"
    if hostname:
        body += f"  hostname: {hostname}\n"
    (tmp_path / fname).write_text(body, encoding="utf-8")


def test_load_tenants_only_accept_prod(tmp_path) -> None:
    _write(tmp_path, "almere-accept", "tenant-almere-accept.yaml")
    _write(tmp_path, "almere-prod", "tenant-almere-prod.yaml")
    _write(tmp_path, "almere-test", "tenant-almere-test.yaml")  # skipped
    recs = load_tenants(str(tmp_path / "tenant-*.yaml"), "commonground.nu")
    names = sorted(r.tenant_name for r in recs)
    assert names == ["almere-accept", "almere-prod"]


def test_load_tenants_honours_hostname_override(tmp_path) -> None:
    _write(tmp_path, "vng-backend-accept", "tenant-vng-backend-accept.yaml",
           hostname="backend.accept.opencatalogi.nl")
    recs = load_tenants(str(tmp_path / "tenant-*.yaml"), "commonground.nu")
    assert len(recs) == 1
    assert recs[0].host == "backend.accept.opencatalogi.nl"
