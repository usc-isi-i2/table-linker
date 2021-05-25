FROM python:3.7.9-slim

RUN apt-get update && apt-get install -y \
  gcc \
  pv \
  git

RUN pip install jupyter
RUN pip install jupyterlab

RUN git clone https://github.com/usc-isi-i2/table-linker

RUN pip install -e table-linker

