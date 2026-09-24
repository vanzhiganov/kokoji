#!/bin/bash
set -e

# Substitute database connection settings from environment variables.
# These must not contain special regex characters.

sed -i "s/^DBName = .*/DBName = ${DB_NAME:-koji}/" /etc/koji-hub/hub.conf
sed -i "s/^DBUser = .*/DBUser = ${DB_USER:-koji}/" /etc/koji-hub/hub.conf
sed -i "s/^DBHost = .*/DBHost = ${DB_HOST:-db}/" /etc/koji-hub/hub.conf
sed -i "s/^DBPort = .*/DBPort = ${DB_PORT:-5432}/" /etc/koji-hub/hub.conf
sed -i "s/^DBPass = .*/DBPass = ${DB_PASS:-koji}/" /etc/koji-hub/hub.conf

# Ensure the koji top directory exists and is writable by the web server user
mkdir -p /mnt/koji
chown -R apache:apache /mnt/koji || true

echo "Starting koji-hub..."
exec httpd -DFOREGROUND
