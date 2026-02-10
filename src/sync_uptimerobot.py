from __future__ import annotations

from dataclasses import dataclass
import os
import sys

from tenants import TenantRecord, load_tenants
from uptimerobot import Monitor, UptimeRobotApiError, UptimeRobotClient


@dataclass(frozen=True)
class DesiredMonitor:
    tenant_name: str
    friendly_name: str
    url: str
    interval: int


def main() -> int:
    try:
        config = load_config_from_env()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    records = load_tenants(config["TENANTS_GLOB"], config["DOMAIN_BASE"])
    desired_by_name = build_desired_map(
        records=records,
        health_path=config["HEALTH_PATH"],
        interval=config["INTERVAL_SECONDS"],
        friendly_prefix=config["FRIENDLY_PREFIX"],
    )

    dry_run = config["DRY_RUN"]
    print(f"Sync start (dry_run={dry_run})")
    print(f"Desired tenants: {len(desired_by_name)}")

    client = UptimeRobotClient(config["UPTIMEROBOT_API_KEY"])
    try:
        existing = client.get_monitors()
    except UptimeRobotApiError as exc:
        print(f"ERROR: unable to list monitors: {exc}", file=sys.stderr)
        return 1

    managed_existing = {
        monitor.friendly_name: monitor
        for monitor in existing
        if monitor.friendly_name.startswith(config["FRIENDLY_PREFIX"])
    }

    created = 0
    updated = 0
    deleted = 0
    unchanged = 0

    for friendly_name, desired in sorted(desired_by_name.items()):
        current = managed_existing.get(friendly_name)
        if current is None:
            print(f"CREATE {friendly_name} -> {desired.url} interval={desired.interval}")
            if not dry_run:
                try:
                    client.create_http_monitor(
                        friendly_name=desired.friendly_name,
                        url=desired.url,
                        interval=desired.interval,
                    )
                except UptimeRobotApiError as exc:
                    print(
                        f"ERROR: failed to create '{friendly_name}': {exc}",
                        file=sys.stderr,
                    )
                    return 1
            created += 1
            continue

        if _needs_update(current, desired):
            print(
                f"UPDATE {friendly_name} "
                f"url: {current.url} -> {desired.url}, "
                f"interval: {current.interval} -> {desired.interval}"
            )
            if not dry_run:
                try:
                    client.edit_http_monitor(
                        monitor_id=current.monitor_id,
                        url=desired.url,
                        interval=desired.interval,
                    )
                except UptimeRobotApiError as exc:
                    print(
                        f"ERROR: failed to update '{friendly_name}' (id={current.monitor_id}): {exc}",
                        file=sys.stderr,
                    )
                    return 1
            updated += 1
        else:
            unchanged += 1

    desired_names = set(desired_by_name.keys())
    for friendly_name, current in sorted(managed_existing.items()):
        if friendly_name in desired_names:
            continue
        print(f"DELETE {friendly_name} (id={current.monitor_id})")
        if not dry_run:
            try:
                client.delete_monitor(current.monitor_id)
            except UptimeRobotApiError as exc:
                print(
                    f"ERROR: failed to delete '{friendly_name}' (id={current.monitor_id}): {exc}",
                    file=sys.stderr,
                )
                return 1
        deleted += 1

    print(
        "Summary: "
        f"created={created}, updated={updated}, deleted={deleted}, unchanged={unchanged}"
    )
    return 0


def load_config_from_env() -> dict[str, object]:
    source_repo = os.getenv(
        "SOURCE_REPO", "https://github.com/ConductionNL/Nextcloud-base"
    ).strip()
    if not source_repo:
        raise ValueError("SOURCE_REPO may not be empty.")

    api_key = _required_env("UPTIMEROBOT_API_KEY")
    source_ref = os.getenv("SOURCE_REF", "main")

    tenants_glob = os.getenv(
        "TENANTS_GLOB",
        "nextcloud-platform/values/tenants/tenant-*.yaml",
    )
    domain_base = os.getenv("DOMAIN_BASE", "commonground.nu").strip()
    health_path = os.getenv("HEALTH_PATH", "/status.php").strip()
    interval_seconds = int(os.getenv("INTERVAL_SECONDS", "60"))
    friendly_prefix = os.getenv("FRIENDLY_PREFIX", "[gitops] nextcloud ")
    dry_run = _parse_bool(os.getenv("DRY_RUN", "false"))

    if not health_path.startswith("/"):
        raise ValueError("HEALTH_PATH must start with '/'.")
    if interval_seconds <= 0:
        raise ValueError("INTERVAL_SECONDS must be > 0.")
    if not domain_base:
        raise ValueError("DOMAIN_BASE may not be empty.")
    if not friendly_prefix:
        raise ValueError("FRIENDLY_PREFIX may not be empty.")

    return {
        "SOURCE_REPO": source_repo,
        "SOURCE_REF": source_ref,
        "TENANTS_GLOB": tenants_glob,
        "DOMAIN_BASE": domain_base,
        "HEALTH_PATH": health_path,
        "INTERVAL_SECONDS": interval_seconds,
        "FRIENDLY_PREFIX": friendly_prefix,
        "DRY_RUN": dry_run,
        "UPTIMEROBOT_API_KEY": api_key,
    }


def build_desired_map(
    records: list[TenantRecord],
    health_path: str,
    interval: int,
    friendly_prefix: str,
) -> dict[str, DesiredMonitor]:
    desired: dict[str, DesiredMonitor] = {}
    for record in records:
        friendly_name = f"{friendly_prefix}{record.tenant_name}"
        url = f"https://{record.host}{health_path}"
        desired[friendly_name] = DesiredMonitor(
            tenant_name=record.tenant_name,
            friendly_name=friendly_name,
            url=url,
            interval=interval,
        )
    return desired


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise ValueError(f"required environment variable '{name}' is missing.")
    return value.strip()


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _needs_update(current: Monitor, desired: DesiredMonitor) -> bool:
    return current.url != desired.url or current.interval != desired.interval


if __name__ == "__main__":
    raise SystemExit(main())
