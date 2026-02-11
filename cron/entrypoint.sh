#!/bin/bash
set -e

# Export current env so cron jobs inherit it
printenv | grep -v '^_' > /tmp/cronenv

# Create crontab
# Format: min hour dom month dow user command
# dow: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
cat > /etc/cron.d/blockhaus101 << 'CRONTAB'
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

# Le mardi à 14h52
52 14 * * 2 root . /tmp/cronenv && cd /app && uv run manage.py generate_tweet --type tweet1 >> /proc/1/fd/1 2>&1

# Le vendredi à 14h03
3 14 * * 5 root . /tmp/cronenv && cd /app && uv run manage.py generate_tweet --type tweet2 >> /proc/1/fd/1 2>&1
CRONTAB

chmod 0644 /etc/cron.d/blockhaus101

exec cron -f
