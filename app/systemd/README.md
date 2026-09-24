# Teletube systemd services

These units run the Teletube apps as system services and, importantly,
order startup so that **nothing is drawn to the screen until every app is
ready**.

## Why the ordering matters

`hook-monitor` publishes the current handset state (`lifted` / `hung_up`)
as soon as it starts. The display, video player, and keypad apps react to
that message. If `hook-monitor` started first, its initial message could be
sent before the consumers had subscribed (ZeroMQ's "slow joiner" problem),
and the screen could react before the system was fully up.

To avoid this, `teletube-hook-monitor.service` is ordered `After=` all the
consumer services and waits a short settle period (`ExecStartPre`) so their
subscriptions are established before the first hook state is published.

## Services

| Unit | Purpose |
|------|---------|
| `teletube-broker.service` | ZeroMQ message broker (starts first) |
| `teletube-keypad-monitor.service` | Reads the keypad, plays DTMF + speech |
| `teletube-video-player.service` | Plays videos for the entered year |
| `teletube-display-monitor.service` | Draws prompts to the screen |
| `teletube-hook-monitor.service` | Publishes handset state (starts last) |
| `teletube-ringer-monitor.service` | Rings the bell when left hung up |
| `teletube.target` | Groups all of the above |

## Prerequisites

The unit files assume:

- The project lives at `/home/pi/teletube`
- `uv` is installed at `/home/pi/.local/bin/uv`
- The services run as user `pi`

If any of these differ, edit `User=`, `WorkingDirectory=`, `Environment=`,
and `ExecStart=` in the unit files before installing.

## Install

Copy (or symlink) the units into the system unit directory, reload systemd,
and enable the target so everything starts at boot:

```bash
cd /home/pi/teletube/app/systemd

# Copy the unit files into place
sudo cp teletube-*.service teletube.target /etc/systemd/system/

# Reload so systemd picks up the new units
sudo systemctl daemon-reload

# Enable at boot and start now
sudo systemctl enable --now teletube.target
```

Symlinking instead of copying keeps the units in the repo as the source of
truth (re-run `daemon-reload` after editing):

```bash
cd /etc/systemd/system
sudo ln -s /home/pi/teletube/app/systemd/teletube-*.service .
sudo ln -s /home/pi/teletube/app/systemd/teletube.target .
sudo systemctl daemon-reload
sudo systemctl enable --now teletube.target
```

## Operate

```bash
# Start / stop / restart everything
sudo systemctl start teletube.target
sudo systemctl stop teletube.target
sudo systemctl restart teletube.target

# Status of all services at a glance
systemctl status 'teletube-*'

# Follow logs (all services, live)
journalctl -f -u 'teletube-*'

# Logs for a single service
journalctl -u teletube-keypad-monitor.service -f

# Restart just one service
sudo systemctl restart teletube-display-monitor.service
```

Stopping the target stops every service because each unit is `PartOf=` the
target.

## Uninstall

```bash
sudo systemctl disable --now teletube.target
sudo rm /etc/systemd/system/teletube-*.service /etc/systemd/system/teletube.target
sudo systemctl daemon-reload
```

## Relationship to `start.sh` / `stop.sh`

`start.sh` and `stop.sh` remain useful for running the apps by hand during
development. Do not run them at the same time as the systemd services —
both would try to bind the broker's sockets and conflict.
