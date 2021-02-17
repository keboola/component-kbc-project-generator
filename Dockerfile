FROM python:3.7.2-slim
ENV PYTHONIOENCODING utf-8

COPY src/ /code/src/
COPY src/tests/ /code/tests/
COPY flake8.cfg /code/flake8.cfg
COPY requirements.txt /code/requirements.txt

# install gcc to be able to build packages - e.g. required by regex, dateparser, also required for pandas
RUN apt-get update && apt-get install -y build-essential && apt-get install -y git

RUN pip install flake8

RUN pip install -r /code/requirements.txt

WORKDIR /code/


CMD ["python", "-u", "/code/src/component.py"]
