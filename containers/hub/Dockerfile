# Koji Hub image.
# Runs the kojihub XMLRPC interface under httpd/mod_wsgi.
FROM koji-base:latest
# To build against a base published to a registry instead, swap the line above
# for: FROM git.org.ru/platformos/koji-base:latest
# and push containers/base separately: docker compose build base

USER root

# Install httpd and mod_wsgi (python3-mod_wsgi auto-registers its
# LoadModule via /etc/httpd/conf.modules.d/10-wsgi-python3.conf)
RUN dnf install -y --setopt=install_weak_deps=0 \
        httpd \
        python3-mod_wsgi \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Copy the kojihub python module into the site-packages next to the
# 'koji' package installed by pip (RHEL installs under /usr/local/lib).
WORKDIR /build
COPY . /build
RUN cd / && SITEDIR=$(python3 -c "import os, koji; print(os.path.dirname(os.path.dirname(koji.__file__)))") \
    && cp -r /build/kojihub "$SITEDIR/kojihub"

# WSGI entrypoint
RUN mkdir -p /usr/share/koji-hub \
    && cp kojihub/app/kojiapp.py /usr/share/koji-hub/kojiapp.py

# Hub config
RUN mkdir -p /etc/koji-hub
COPY containers/hub/hub.conf /etc/koji-hub/hub.conf

# httpd config for koji-hub
COPY containers/hub/koji-hub.conf /etc/httpd/conf.d/koji-hub.conf

# Koji top directory (build root / file hosting)
RUN mkdir -p /mnt/koji && chown -R apache:apache /mnt/koji

EXPOSE 80

COPY containers/hub/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]