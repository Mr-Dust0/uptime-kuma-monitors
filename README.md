# Uptime Kuma — monitors as code

Run [Uptime Kuma](https://github.com/louislam/uptime-kuma) and manage **which
servers it monitors from a file** (`monitors.yaml`) instead of clicking around
the web UI.

Uptime Kuma has no native config-file import — its monitors live in a SQLite
database. This repo works around that with a small **provisioner** sidecar that
reads `monitors.yaml` and pushes each entry into Kuma through its API. Edit the
file, re-run one command, done.

## Layout

```
.
├── docker-compose.yml      # Kuma + the provisioner sidecar
├── monitors.yaml           # <-- your monitored servers live here
├── .env.example            # copy to .env, set admin credentials
└── provisioner/
    ├── Dockerfile
    └── provision.py         # reads monitors.yaml, calls the Kuma API
```

## Quick start

```bash
# 1. Set admin credentials (used to create the account on first run)
cp .env.example .env
$EDITOR .env

# 2. Edit the list of servers you want to monitor
$EDITOR monitors.yaml

# 3. Start Kuma
docker compose up -d uptime-kuma

# 4. Apply your monitors
docker compose run --rm provisioner
```

The dashboard is at <http://localhost:3001> (log in with the credentials from
`.env`).

## Changing what's monitored

Edit `monitors.yaml`, then re-apply:

```bash
docker compose run --rm provisioner
```

- Monitors are matched by **`name`**.
- An existing name is **updated** in place.
- A new name is **created**.
- Removing an entry from the file does **not** delete the monitor (delete those
  in the UI, to avoid accidental data loss).

## `monitors.yaml` reference

Each list entry is one monitor. `name` and `type` are required; the rest depend
on the type.

| type     | required fields            | notes                                   |
|----------|----------------------------|-----------------------------------------|
| `http`   | `url`                      | HTTP(s) status check                    |
| `port`   | `hostname`, `port`         | raw TCP connect                         |
| `ping`   | `hostname`                 | ICMP ping                               |
| `dns`    | `hostname`                 | DNS resolution                          |
| `keyword`| `url`, `keyword`           | HTTP + body must contain keyword        |
| `docker` | `docker_container`         | needs the `docker.sock` mount (below)   |

`interval` (seconds between checks) is optional and applies to any type.

```yaml
- name: My Website
  type: http
  url: https://example.com
  interval: 60

- name: Postgres
  type: port
  hostname: 10.0.0.5
  port: 5432
```

Any extra field accepted by the
[uptime-kuma-api `add_monitor`](https://uptime-kuma-api.readthedocs.io/en/latest/api.html#uptime_kuma_api.UptimeKumaApi.add_monitor)
method can be added to an entry (e.g. `retryInterval`, `maxretries`,
`accepted_statuscodes`).

## Monitoring Docker containers

The `docker` monitor type needs Kuma to see the host's Docker socket. The
compose file mounts it by default:

```yaml
- /var/run/docker.sock:/var/run/docker.sock
```

This grants the container root-equivalent control of the host. If you don't use
the `docker` monitor type, **remove that line** from `docker-compose.yml`.

## Notes

- Data persists in the `uptime-kuma-data` named volume, so monitors, history and
  settings survive `docker compose down` (but not `down -v`).
- `.env` holds your admin password and is gitignored — never commit it.
- The provisioner only adds/updates. It is safe to run repeatedly.
