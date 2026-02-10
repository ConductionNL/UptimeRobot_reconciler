# UptimeRobot GitOps Reconciler

Deze repository bevat een pure GitHub Actions reconciler die UptimeRobot HTTP monitors synchroniseert op basis van tenant YAML bestanden uit een andere (public) GitHub repo.

## Wat het doet

- Leest tenant files met een glob (default: `nextcloud-platform/values/tenants/tenant-*.yaml`) uit een bronrepo.
- Verwacht per file minimaal `tenant.name`.
- Leidt hostname af op basis van conventie:
  - `-accept` -> `<org>.accept.<DOMAIN_BASE>`
  - `-test` -> `<org>.test.<DOMAIN_BASE>`
  - `-prod` -> `<org>.<DOMAIN_BASE>`
- Maakt gewenste URL: `https://{host}{HEALTH_PATH}`.
- Reconcilet UptimeRobot monitors:
  - create als monitor ontbreekt
  - update als `url` of `interval` afwijkt
  - delete als een eerder beheerde monitor niet meer gewenst is

## Safety model (prefix ownership)

Alleen monitors waarvan de `friendly_name` start met `FRIENDLY_PREFIX` worden door deze tool beheerd, aangepast of verwijderd.

Primary key / identiteit:

- `friendly_name = FRIENDLY_PREFIX + tenant_name`

Hierdoor kan de reconciler nooit per ongeluk monitors verwijderen die niet door deze tool worden "owned".

## Benodigde GitHub configuratie

### Secret

- `UPTIMEROBOT_API_KEY` (repo secret)

### Repository variables

- `SOURCE_REPO` is standaard vastgezet op `https://github.com/ConductionNL/Nextcloud-base`
- `SOURCE_REF` (optioneel, default `main`)
- `TENANTS_GLOB` (optioneel, default `nextcloud-platform/values/tenants/tenant-*.yaml`)
- `DOMAIN_BASE` (optioneel, default `commonground.nu`)
- `HEALTH_PATH` (optioneel, default `/status.php`)
- `INTERVAL_SECONDS` (optioneel, default `60`)
- `FRIENDLY_PREFIX` (optioneel, default `[gitops] nextcloud `)
- `DRY_RUN` (optioneel, default `false`)

## Workflow gedrag

Workflow: `.github/workflows/sync.yml`

- Triggers:
  - push naar `main`
  - pull requests naar `main`
  - nightly schedule
  - handmatig via `workflow_dispatch`
- `concurrency` staat op 1 actieve sync tegelijk.
- PR runs forceren altijd `DRY_RUN=true` (plan/output-only, geen mutaties).
- Push/schedule/workflow_dispatch gebruiken `DRY_RUN` uit repo vars (default `false`).

## Lokaal draaien

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Zet daarna env vars, minimaal:

```bash
export UPTIMEROBOT_API_KEY=xxxx
```

`SOURCE_REPO` hoeft lokaal niet gezet te worden tenzij je wilt overriden; default is:
`https://github.com/ConductionNL/Nextcloud-base`.

Voor lokaal testen met een geclonede bronrepo kun je bijvoorbeeld:

```bash
export TENANTS_GLOB=../bronrepo/nextcloud-platform/values/tenants/tenant-*.yaml
python src/sync_uptimerobot.py
```

Dry-run voorbeeld:

```bash
export DRY_RUN=true
python src/sync_uptimerobot.py
```

## Output

De sync print acties en sluit af met:

- `Summary: created=X, updated=Y, deleted=Z, unchanged=Q`

Bij API-fouten of ongeldige verplichte configuratie exit het script non-zero met context.

## Ontwikkelen / testen

```bash
pip install -r requirements-dev.txt
PYTHONPATH=src pytest -q
```
