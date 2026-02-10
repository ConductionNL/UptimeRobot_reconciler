from __future__ import annotations

from dataclasses import dataclass
from glob import glob
from pathlib import Path
from typing import Optional
import sys

import yaml


@dataclass(frozen=True)
class TenantRecord:
    tenant_name: str
    org: str
    env: str
    host: str
    source_file: str


def parse_tenant_name(tenant_name: str, domain_base: str) -> Optional[tuple[str, str, str]]:
    suffix_to_env = {
        "-accept": "accept",
        "-test": "test",
        "-prod": "prod",
    }
    for suffix, env in suffix_to_env.items():
        if tenant_name.endswith(suffix):
            org = tenant_name[: -len(suffix)]
            if not org:
                return None
            if env == "prod":
                host = f"{org}.{domain_base}"
            else:
                host = f"{org}.{env}.{domain_base}"
            return org, env, host
    return None


def load_tenants(tenants_glob: str, domain_base: str) -> list[TenantRecord]:
    records: list[TenantRecord] = []
    matched_files = sorted(glob(tenants_glob))

    if not matched_files:
        print(
            f"WARNING: no tenant files matched glob '{tenants_glob}'.",
            file=sys.stderr,
        )
        return records

    for file_path in matched_files:
        tenant_name = _extract_tenant_name(file_path)
        if not tenant_name:
            print(
                f"WARNING: tenant.name missing in '{file_path}', skipping.",
                file=sys.stderr,
            )
            continue

        parsed = parse_tenant_name(tenant_name, domain_base)
        if not parsed:
            print(
                f"WARNING: unknown tenant suffix for '{tenant_name}' in '{file_path}', skipping.",
                file=sys.stderr,
            )
            continue

        org, env, host = parsed
        records.append(
            TenantRecord(
                tenant_name=tenant_name,
                org=org,
                env=env,
                host=host,
                source_file=str(Path(file_path)),
            )
        )

    return records


def _extract_tenant_name(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            content = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        print(f"WARNING: invalid YAML in '{file_path}': {exc}", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"WARNING: could not read '{file_path}': {exc}", file=sys.stderr)
        return None

    tenant_data = content.get("tenant")
    if not isinstance(tenant_data, dict):
        return None

    name = tenant_data.get("name")
    if not isinstance(name, str):
        return None

    normalized = name.strip()
    return normalized or None
