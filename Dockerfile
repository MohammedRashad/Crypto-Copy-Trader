FROM python:latest

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]

RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev python-dev

RUN apt-get install -y  build-essential autoconf libtool pkg-config python-pyrex  idle-python2.7 qt4-dev-tools qt4-designer libqtgui4 libqtcore4 libqt4-xml libqt4-test libqt4-script libqt4-network libqt4-dbus python-qt4 python-qt4-gl libgle3 python-dev libssl-dev

RUN pip3 install --no-cache-dir Cython
# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install --no-cache-dir Cython

RUN pip3 install -r requirements.txt


COPY . /app

EXPOSE 5000

ENTRYPOINT [ "python3" ]

CMD [ "api.py" ]
