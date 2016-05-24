FROM ubuntu:14.04
MAINTAINER David Goldberg <goodwordalchemy@gmail.com>

ADD . /code
WORKDIR /code

# dependencies for the cryptography package
RUN apt-get update && apt-get install -y \
	gcc \ 
	libffi-dev \ 
	libssl-dev
RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "run.py"]

