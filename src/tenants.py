from __future__ import annotations

import sys
from dataclasses import dataclass
from glob import glob
from pathlib import Path
from typing import Optional

import yaml


@dataclass(frozen=True)
class TenantRecord:
    tenant_name: str
    org: str
    env: str
    host: str
    source_file: str


def parse_tenant_name(tenant_name: str, domain_base: str) -> Optional[tuple[str, str, str]]:
    """Return (org, env, host) for an -accept/-prod tenant, else None.

    Only accept and prod are monitored (test/demo are intentionally skipped).
    Host derivation mirrors the Nextcloud-base ApplicationSet: prod has no env
    segment (`<org>.<domain>`), accept is `<org>.accept.<domain>`.
    """
    for suffix, env in (("-accept", "accept"), ("-prod", "prod")):
        if tenant_name.endswith(suffix):
            org = tenant_name[: -len(suffix)]
            if not org:
                return None
            host = f"{org}.{domain_base}" if env == "prod" else f"{org}.{env}.{domain_base}"
            return org, env, host
    return None


def load_tenants(tenants_glob: str, domain_base: str) -> list[TenantRecord]:
    records: list[TenantRecord] = []
    matched_files = sorted(glob(tenants_glob))

    if not matched_files:
        print(f"WARNING: no tenant files matched glob '{tenants_glob}'.", file=sys.stderr)
        return records

    for file_path in matched_files:
        tenant = _load_tenant(file_path)
        name = (tenant or {}).get("name")
        if not isinstance(name, str) or not name.strip():
            print(f"WARNING: tenant.name missing in '{file_path}', skipping.", file=sys.stderr)
            continue
        name = name.strip()

        parsed = parse_tenant_name(name, domain_base)
        if not parsed:
            # test/demo or unknown suffix — not monitored.
            continue
        org, env, host = parsed

        # Explicit host override wins (migrate / external / non-canonical domains
        # like open.<gemeente>.nl), so the monitored URL matches the real ingress.
        override = tenant.get("hostname")
        if isinstance(override, str) and override.strip():
            host = override.strip()

        records.append(
            TenantRecord(
                tenant_name=name,
                org=org,
                env=env,
                host=host,
                source_file=str(Path(file_path)),
            )
        )

    return records


def _load_tenant(file_path: str) -> Optional[dict]:
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            content = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        print(f"WARNING: invalid YAML in '{file_path}': {exc}", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"WARNING: could not read '{file_path}': {exc}", file=sys.stderr)
        return None

    tenant = content.get("tenant")
    return tenant if isinstance(tenant, dict) else None
