.PHONY: all venv deps run clean lint

all: clean venv deps run

clean:
	rm -rf venv

venv:
	virtualenv venv

deps:
	venv/bin/pip install -r requirements.txt

run:
	venv/bin/python ./top.py

lint:
	venv/bin/flake8 ./top.py
