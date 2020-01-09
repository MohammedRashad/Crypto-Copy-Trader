FROM phusion/baseimage:latest

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]

RUN apt-get update -y
RUN apt-get install -y python3 python-dev python3-dev  build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev python3-pip
 
# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install --no-cache-dir Cython

RUN pip3 install -r requirements.txt


COPY . /app

EXPOSE 5000

ENTRYPOINT [ "python3" ]

CMD [ "api.py" ]
