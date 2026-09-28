# Koji CLI image.
# Provides the 'koji' command-line client.
FROM koji-base:latest
# To build against a base published to a registry instead, swap the line above
# for: FROM git.org.ru/platformos/koji-base:latest
# and push containers/base separately: docker compose build base

ENTRYPOINT ["/usr/local/bin/koji"]
