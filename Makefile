PYPI_URL = https://pypi.python.org/pypi
tarball = `ls -1rt ./dist/*.tar* | tail -1`

all: flakes README.rst smoke

test: tox-command README.txt
	@tox

smoke: coverage-command
	@coverage erase
	@coverage run test_jeni.py --failfast
	@coverage report --show-missing --include=*jeni*

flakes: pyflakes-command
	@pyflakes *.py

dist: README.txt flakes
	python setup.py sdist --formats=bztar
	@echo
	@echo 'Use `make publish` to publish to PyPI.'
	@echo
	@echo Tarball for manual distribution:
	@echo $(tarball)

publish: README.txt flakes
	python setup.py sdist --formats=bztar,zip upload -r $(PYPI_URL)

publish-test: README.txt flakes
	python setup.py register -r $(PYPI_URL)
	python setup.py sdist --formats=bztar,zip upload -r $(PYPI_URL)

# Set a test PYPI_URL for the publish-test target.
publish-test : PYPI_URL = https://testpypi.python.org/pypi

develop: README.txt
	python setup.py develop

install: README.txt
	python setup.py install

clean:
	rm -fr __pycache__ build dist .tox *.egg-info
	rm -f *.pyc MANIFEST README.txt .coverage .in_virtualenv.py

# README.rst is for repository distribution.
# README.txt is for source distribution.

RST_WARNING = 'DO NOT EDIT THIS FILE. EDIT README.rst.in.' # README.rst warning
README.rst: README.rst.in jeni.py bin/build_rst.py
	@RST_WARNING=$(RST_WARNING) python bin/build_rst.py README.rst.in > $@

README.txt: README.rst.in jeni.py bin/build_rst.py
	@python bin/build_rst.py README.rst.in > $@

tox-command: virtualenv
	@which tox >/dev/null 2>&1 || pip install tox

coverage-command: virtualenv
	@which coverage >/dev/null 2>&1 || pip install coverage

pyflakes-command: virtualenv
	@which pyflakes >/dev/null 2>&1 || pip install pyflakes

virtualenv: .in_virtualenv.py
	@python $<

.in_virtualenv.py: Makefile
	@echo '# Generated by Makefile, written by rduplain.'             >  $@
	@echo 'import sys'                                                >> $@
	@echo 'if hasattr(sys, "real_prefix"):'                           >> $@
	@echo '    sys.exit(0)'                                           >> $@
	@echo 'else:'                                                     >> $@
	@echo '    sys.stderr.write("Use a virtualenv, 2.7 or 3.2+.\\n")' >> $@
	@echo '    sys.exit(1)'                                           >> $@

.PHONY: dist
