NAME=koji
SPECFILE = $(firstword $(wildcard *.spec))

ifndef PYTHON
export PYTHON=python3
endif

SUBDIRS = kojihub builder koji cli util www plugins vm schemas


ifdef DIST
DIST_DEFINES := --define "dist $(DIST)"
endif

ifndef VERSION
VERSION := $(shell rpm $(RPM_DEFINES) $(DIST_DEFINES) -q --qf "%{VERSION}\n" --specfile $(SPECFILE)| head -1)
endif
# the release of the package
ifndef RELEASE
RELEASE := $(shell rpm $(RPM_DEFINES) $(DIST_DEFINES) -q --qf "%{RELEASE}\n" --specfile $(SPECFILE)| head -1)
endif

ifndef WORKDIR
WORKDIR := $(shell pwd)
endif
## Override RPM_WITH_DIRS to avoid the usage of these variables.
ifndef SRCRPMDIR
SRCRPMDIR = $(WORKDIR)
endif
ifndef BUILDDIR
BUILDDIR = $(WORKDIR)
endif
ifndef RPMDIR
RPMDIR = $(WORKDIR)
endif
## SOURCEDIR is special; it has to match the CVS checkout directory,-
## because the CVS checkout directory contains the patch files. So it basically-
## can't be overridden without breaking things. But we leave it a variable
## for consistency, and in hopes of convincing it to work sometime.
ifndef SOURCEDIR
SOURCEDIR := $(shell pwd)
endif


# RPM with all the overrides in place;
ifndef RPM
RPM := $(shell if test -f /usr/bin/rpmbuild ; then echo rpmbuild ; else echo rpm ; fi)
endif
ifndef RPM_WITH_DIRS
RPM_WITH_DIRS = $(RPM) --define "_sourcedir $(SOURCEDIR)" \
		    --define "_builddir $(BUILDDIR)" \
		    --define "_srcrpmdir $(SRCRPMDIR)" \
		    --define "_rpmdir $(RPMDIR)"
endif

# tag to export, defaulting to current tag in the spec file
ifndef TAG
TAG=$(NAME)-$(VERSION)-$(RELEASE)
endif

.DEFAULT_GOAL := help

.PHONY: help _default clean git-clean test test3 test-tarball tarball sources srpm rpm test-rpm pypi pypi-upload flake8 bandit containers containers-base containers-cli containers-up containers-down tag force-tag install

_default: help

help: ## Show this help
	@echo "Koji development makefile - usage: make <target> [VARIABLE=value]"
	@echo ""
	@echo "Targets:"
	@grep -hE '^[a-zA-Z0-9_.-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Common variables:"
	@echo "  PYTHON                   python interpreter (default: python3)"
	@echo "  VERSION, RELEASE, DIST   override values read from the spec file"
	@echo "  DESTDIR                  install root (default: /), with TYPE=systemd|sysv"
	@echo "  CONTAINER_ENGINE, COMPOSE, COMPOSE_FILE  container tooling (default: docker compose)"
	@echo ""
	@echo "See docs/source/writing_koji_code.rst for more details."

clean: ## Remove generated files and build artifacts
	rm -f *.o *.so *.pyc *~ koji*.bz2 koji*.src.rpm
	rm -rf __pycache__
	rm -rf devtools/fakehubc devtools/fakewebc devtools/__pycache__
	rm -rf koji-$(VERSION)
	rm -rf build dist koji.egg-info
	find -name '*.pyi' -delete
	find -name py.typed -delete
	for d in $(SUBDIRS); do make -s -C $$d clean; done
	find ./tests -name "__pycache__" -exec rm -rf {} \; ||:
	find ./tests -name "*.pyc" -exec rm -f {} \;
	rm -rf docs/source/__pycache__ docs/source/*.pyc
	$(PYTHON) -m coverage erase ||:
	rm -rf htmlcov

git-clean: ## Remove all untracked and ignored files (git clean -dx)
	@git clean -d -q -x

test: ## Run the full test suite (tox -e py3)
	tox -e py3
	@echo Full coverage report at file://${CURDIR}/htmlcov/index.html

test3: test ## Alias for test (kept for compatibility)

test-tarball: ## Build a test tarball from the working tree
	@rm -rf .koji-$(VERSION)
	@mkdir .koji-$(VERSION)
	@cp -al [A-Za-z]* .koji-$(VERSION)
	@mv .koji-$(VERSION) koji-$(VERSION)
	tar --bzip2 --exclude '*.tar.bz2' --exclude '*.rpm' --exclude '.#*' \
	    -cpf koji-$(VERSION).tar.bz2 koji-$(VERSION)
	@rm -rf koji-$(VERSION)

tarball: clean ## Create the release tarball from HEAD via git archive
	@git archive --format=tar --prefix=$(NAME)-$(VERSION)/ HEAD |bzip2 > $(NAME)-$(VERSION).tar.bz2

sources: tarball ## Alias for tarball (used by rpm/koji builds)

srpm: tarball ## Build the source RPM
	$(RPM_WITH_DIRS) $(DIST_DEFINES) -bs $(SPECFILE)

rpm: tarball ## Build the binary RPM
	$(RPM_WITH_DIRS) $(DIST_DEFINES) -bb $(SPECFILE)

test-rpm: tarball ## Build the binary RPM with testbuild enabled
	$(RPM_WITH_DIRS) $(DIST_DEFINES) --define "testbuild 1" -bb $(SPECFILE)

pypi: ## Build sdist and python 3 wheel in dist/
	rm -rf dist
	$(PYTHON) setup.py sdist
	$(PYTHON) -m venv build_py3
	build_py3/bin/pip install --upgrade pip setuptools wheel
	build_py3/bin/python setup.py bdist_wheel
	rm -rf build_py3

pypi-upload: ## Upload dist/ artifacts to PyPI via twine
	twine upload dist/*

flake8: ## Run flake8 linting via tox
	tox -e flake8

bandit: ## Run bandit security checks via tox
	tox -e bandit

# Containers -----------------------------------------------------------------
# Every component image extends koji-base, so the base image has to exist
# locally before the others can build. compose tags it koji-base:latest, but
# the component Dockerfiles use FROM git.org.ru/platformos/koji-base:latest,
# so containers-base also tags it under that name to avoid a registry pull.
CONTAINER_ENGINE ?= docker
COMPOSE ?= $(CONTAINER_ENGINE) compose
COMPOSE_FILE ?= containers/compose.yml
BASE_IMAGE ?= git.org.ru/platformos/koji-base:latest
CLI_IMAGE ?= git.org.ru/platformos/koji-cli:latest

containers-base: ## Build the shared koji-base image (must come first)
	$(COMPOSE) -f $(COMPOSE_FILE) build base
	$(CONTAINER_ENGINE) tag koji-base:latest $(BASE_IMAGE)

containers-cli: containers-base ## Build the koji CLI image (not in compose.yml)
	$(CONTAINER_ENGINE) build -f containers/cli/Dockerfile -t $(CLI_IMAGE) .

containers: containers-base containers-cli ## Build all container images
	$(COMPOSE) -f $(COMPOSE_FILE) build

containers-up: ## Start the container stack in the background
	$(COMPOSE) -f $(COMPOSE_FILE) up -d

containers-down: ## Stop and remove the container stack
	$(COMPOSE) -f $(COMPOSE_FILE) down
# ----------------------------------------------------------------------------

tag:: ## Create the annotated git tag
	git tag -a $(TAG)
	@echo "Tagged with: $(TAG)"
	@echo

force-tag:: ## Force-create/replace the annotated git tag
	git tag -f -a $(TAG)
	@echo "Tagged with: $(TAG)"
	@echo

# If and only if "make build" fails, use "make force-tag" to 
# re-tag the version.
#force-tag: $(SPECFILE)
#	@$(MAKE) tag TAG_OPTS="-F $(TAG_OPTS)"

DESTDIR ?= /
TYPE = systemd
install: ## Install all subdirectories under DESTDIR
	@if [ "$(DESTDIR)" = "" ]; then \
		echo " "; \
		echo "ERROR: A destdir is required"; \
		exit 1; \
	fi

	mkdir -p $(DESTDIR)

	for d in $(SUBDIRS); do make DESTDIR=`cd $(DESTDIR); pwd` \
		-C $$d install TYPE=$(TYPE); [ $$? = 0 ] || exit 1; done
