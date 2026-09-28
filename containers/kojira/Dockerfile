# Koji Repository Administrator (kojira) image.
# Extends the base image which installs the kojira script.
FROM koji-base:latest
# To build against a base published to a registry instead, swap the line above
# for: FROM git.org.ru/platformos/koji-base:latest
# and push containers/base separately: docker compose build base

USER root

# kojira config
RUN mkdir -p /etc/kojira
COPY containers/kojira/kojira.conf /etc/kojira/kojira.conf

# Make the shared koji top directory available
RUN mkdir -p /mnt/koji

COPY containers/kojira/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
