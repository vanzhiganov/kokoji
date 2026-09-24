# Koji Web UI image.
# Runs the kojiweb WSGI application under httpd/mod_wsgi.
FROM koji-base:latest

USER root

# Install httpd and mod_wsgi (python3-mod_wsgi auto-registers its
# LoadModule via /etc/httpd/conf.modules.d/10-wsgi-python3.conf)
RUN dnf install -y --setopt=install_weak_deps=0 \
        httpd \
        python3-mod_wsgi \
    && dnf clean all \
    && rm -rf /var/cache/dnf

WORKDIR /build
COPY . /build

# Install the web application using the canonical koji-web layout:
#   /usr/share/koji-web/scripts/  -> index.py, wsgi_publisher.py, all .chtml + includes/
#   /usr/share/koji-web/lib/      -> the kojiweb helper library (LibPath)
#   /usr/share/koji-web/static/   -> static assets
RUN mkdir -p /usr/share/koji-web/scripts \
    && cp -r www/kojiweb/*.py /usr/share/koji-web/scripts/ \
    && cp -r www/kojiweb/*.chtml /usr/share/koji-web/scripts/ \
    && cp -r www/kojiweb/includes /usr/share/koji-web/scripts/includes \
    && mkdir -p /usr/share/koji-web/lib \
    && cp -r www/lib/kojiweb /usr/share/koji-web/lib/kojiweb \
    && mkdir -p /usr/share/koji-web/static \
    && cp -r www/static/* /usr/share/koji-web/static/

# Config
RUN mkdir -p /etc/kojiweb
COPY containers/web/web.conf /etc/kojiweb/web.conf

# httpd config
COPY containers/web/kojiweb.conf /etc/httpd/conf.d/kojiweb.conf

EXPOSE 80

COPY containers/web/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]