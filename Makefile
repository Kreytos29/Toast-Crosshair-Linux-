PREFIX ?= $(HOME)/.local
DESTDIR ?=
PYTHON  ?= python3

.PHONY: help run test lint install uninstall desktop-files clean

help:
	@echo "make run              ejecuta Crosshair sin instalarlo"
	@echo "make test             ejecuta las pruebas"
	@echo "make lint             revisa el código con pyflakes, si está instalado"
	@echo "make install          instala el programa para el usuario actual"
	@echo "make uninstall        lo desinstala"
	@echo "make desktop-files    solo el icono y la entrada del menú (PREFIX=$(PREFIX))"
	@echo "make clean            borra los archivos generados"

run:
	$(PYTHON) run.py

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	@$(PYTHON) -m pyflakes crosshair/ tests/ run.py || echo "(pyflakes no está instalado)"

install:
	./install.sh

uninstall:
	./uninstall.sh

desktop-files:
	install -Dm644 data/crosshair.desktop \
		$(DESTDIR)$(PREFIX)/share/applications/crosshair.desktop
	install -Dm644 data/icons/crosshair.svg \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/crosshair.svg

clean:
	rm -rf build dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
