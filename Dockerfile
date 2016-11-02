FROM python:3.5
RUN apt-get update && apt-get install -y less
COPY . shellish
WORKDIR shellish
RUN python ./setup.py install
ENTRYPOINT ["python"]
