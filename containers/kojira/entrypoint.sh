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
exec /usr/local/bin/kojira -f --user "${KOJIRA_USER:-kojira}" --password "${KOJIRA_PASSWORD:-kojira}" --server "${KOJIRA_SERVER:-http://hub/kojihub}"
