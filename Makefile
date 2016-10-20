.PHONY: all venv deps run clean

all: clean venv deps run

clean:
	rm -rf venv

venv:
	virtualenv venv

deps:
	source venv/bin/activate && \
		pip install -r requirements.txt

run:
	source venv/bin/activate && \
		python ./top.py
