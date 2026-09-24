#!/bin/bash
set -e

# Substitute configuration from environment variables.

sed -i "s|^KojiHubURL = .*|KojiHubURL = ${HUB_URL:-http://hub/kojihub}|" /etc/kojiweb/web.conf
sed -i "s|^KojiFilesURL = .*|KojiFilesURL = ${FILES_URL:-http://hub/kojifiles}|" /etc/kojiweb/web.conf
sed -i "s|^Secret = .*|Secret = ${WEB_SECRET:-change-me-secret}|" /etc/kojiweb/web.conf

# Allow toggling self-registration
if [ "${ALLOW_REGISTRATION:-On}" = "On" ]; then
    sed -i "s/^AllowRegistration = .*/AllowRegistration = On/" /etc/kojiweb/web.conf
else
    sed -i "s/^AllowRegistration = .*/AllowRegistration = Off/" /etc/kojiweb/web.conf
fi

echo "Starting koji-web..."
exec httpd -DFOREGROUND
