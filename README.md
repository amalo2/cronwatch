# cronwatch

Lightweight daemon that monitors cron job execution times and alerts on drift or silent failures.

## Installation

```bash
pip install cronwatch
```

Or install from source:

```bash
git clone https://github.com/youruser/cronwatch.git && cd cronwatch && pip install .
```

## Usage

Define your jobs in `cronwatch.yaml`:

```yaml
jobs:
  daily-backup:
    schedule: "0 2 * * *"
    expected_duration: 120s
    alert_on_drift: 30s
    alert_on_silence: 6h

  hourly-sync:
    schedule: "0 * * * *"
    expected_duration: 45s
    alert_on_silence: 2h
```

Start the daemon:

```bash
cronwatch --config cronwatch.yaml
```

Wrap your existing cron commands to report execution:

```bash
# In your crontab
0 2 * * * cronwatch-run daily-backup -- /usr/local/bin/backup.sh
```

Alerts are sent via the configured notifier (email, Slack, or webhook):

```bash
cronwatch --config cronwatch.yaml --notifier slack
```

## Configuration

| Key | Description | Default |
|-----|-------------|---------|
| `schedule` | Cron expression for expected run time | required |
| `expected_duration` | How long the job should take | `null` |
| `alert_on_drift` | Tolerance before a duration alert fires | `60s` |
| `alert_on_silence` | Time without a check-in before alerting | `2x schedule interval` |

## License

MIT