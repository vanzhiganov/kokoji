# Base image for Koji components.
# Provides the shared koji library and common Python runtime.
FROM rockylinux/rockylinux:10

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1

# Runtime dependencies shared across components.
# - python3-rpm: the RPM python bindings required by koji-hub (imported at module load)
# - libpq-devel: postgres client headers for building psycopg2
# - curl-minimal: already present in the base; installing `curl` would conflict with it
RUN dnf install -y --setopt=install_weak_deps=0 \
        gcc \
        python3-devel \
        python3-pip \
        python3-setuptools \
        python3-rpm \
        libpq-devel \
        pkgconf-pkg-config \
        subversion \
        git \
        curl-minimal \
        rsync \
        openssl \
        ca-certificates \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Install base koji library + cli (shared across all components)
WORKDIR /build
COPY . /build

# Install the koji python package and its deps
RUN python3 -m pip install --no-cache-dir . \
    && python3 -m pip install --no-cache-dir \
        psycopg2-binary \
        Cheetah3 \
        python-dateutil

WORKDIR /

# Config for the cli
COPY containers/base/koji.conf /etc/koji.conf

CMD ["/bin/bash"]