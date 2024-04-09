mode = prod

PYTHON = python3
ifeq (, $(shell which python3 ))
	PYTHON=python
endif

.PHONY: clean virtualenv test docker dist dist-upload

clean:
	find . -name '*.py[co]' -delete

virtualenv:
	virtualenv --prompt '|> tenet <|' env
	@echo
	@echo "VirtualENV Setup Complete. Now run: source env/bin/activate"
	@echo

install:
	pip install .[test]

test:
	${PYTHON} -m pytest \
		-v \
		--cov=tenet \
		--cov-report=term \
		--cov-report=html:coverage-report \
		tests/

docker: clean
	docker build --progress=plain --target $(mode) -t tenet:latest .

dist: clean
	rm -rf dist/*
	${PYTHON} setup.py sdist
	${PYTHON} setup.py bdist_wheel

dist-upload:
	twine upload dist/*
