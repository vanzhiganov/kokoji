#!/bin/bash
set -e

# Substitute the hub server URL and authentication from environment variables.
sed -i "s|^server=.*|server=${KOJIRA_SERVER:-http://hub/kojihub}|" /etc/kojira/kojira.conf
sed -i "s|^topdir=.*|topdir=${KOJIRA_TOPDIR:-/mnt/koji}|" /etc/kojira/kojira.conf
sed -i "s/^user=.*/user=${KOJIRA_USER:-kojira}/" /etc/kojira/kojira.conf
sed -i "s/^password=.*/password=${KOJIRA_PASSWORD:-kojira}/" /etc/kojira/kojira.conf

mkdir -p /mnt/koji

echo "Starting kojira..."
# Run in the foreground (-f). Set the user/password explicitly so that
# the hub password authentication is used.
#
# --force-lock reclaims a stale exclusive session. makeExclusive() refuses
# when any unclosed exclusive session exists for the user, and that check does
# not consider expiry, so a kojira container that is killed rather than shut
# down cleanly leaves a session row behind and every later start fails with
# AuthLockError. Harmless for a single-instance deployment.
exec /usr/local/bin/kojira -f --force-lock \
    --user "${KOJIRA_USER:-kojira}" --password "${KOJIRA_PASSWORD:-kojira}" \
    --server "${KOJIRA_SERVER:-http://hub/kojihub}"
