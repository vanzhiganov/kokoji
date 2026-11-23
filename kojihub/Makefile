PACKAGE = kojihub
PYFILES = $(wildcard *.py)
SUBDIRS = models migrations migrations/versions
PKGDIR = $(shell $(PYTHON) ../devtools/get_site_packages.py )/$(PACKAGE)

SERVERDIR = /usr/share/koji-hub

_default:
	@echo "nothing to make.  try make install"

clean:
	rm -f *.o *.so *.pyc *~
	rm -rf __pycache__
	for d in $(SUBDIRS) ; do rm -rf $$d/__pycache__ ; done

install:
	@if [ "$(DESTDIR)" = "" ]; then \
		echo " "; \
		echo "ERROR: A destdir is required"; \
		exit 1; \
	fi

        # python module
	mkdir -p $(DESTDIR)/$(PKGDIR)
	for p in $(PYFILES) ; do \
		install -p -m 644 $$p $(DESTDIR)/$(PKGDIR)/$$p; \
	done
	for d in $(SUBDIRS) ; do \
		mkdir -p $(DESTDIR)/$(PKGDIR)/$$d; \
		install -p -m 644 $$d/*.py $(DESTDIR)/$(PKGDIR)/$$d/; \
	done
	install -p -m 644 migrations/alembic.ini migrations/script.py.mako \
		$(DESTDIR)/$(PKGDIR)/migrations/

	$(PYTHON) -c "import compileall; compileall.compile_dir('$(DESTDIR)/$(PKGDIR)', 1, '$(PYDIR)', 1)"

        # application files
	mkdir -p $(DESTDIR)/etc/httpd/conf.d
	install -p -m 644 app/httpd.conf $(DESTDIR)/etc/httpd/conf.d/kojihub.conf

	mkdir -p $(DESTDIR)/etc/koji-hub
	install -p -m 644 app/hub.conf $(DESTDIR)/etc/koji-hub/hub.conf
	mkdir -p $(DESTDIR)/etc/koji-hub/hub.conf.d


	mkdir -p $(DESTDIR)/$(SERVERDIR)
	install -p -m 644 app/kojiapp.py $(DESTDIR)/$(SERVERDIR)/kojiapp.py
	$(PYTHON) -c "import compileall; compileall.compile_dir('$(DESTDIR)/$(SERVERDIR)', 1, '$(PYDIR)', 1)"
