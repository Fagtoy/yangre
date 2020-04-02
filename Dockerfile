FROM debian:stretch AS build

RUN apt-get update \
  && apt-get -y install clang cmake libpcre3-dev git libxml2-dev \ 
  && cd /home; mkdir w3cgrep \
  && cd /home; git clone https://github.com/CESNET/libyang.git \
  && cd /home/libyang; mkdir build \
  && cd /home/libyang/build && cmake .. && make && make install

COPY w3cgrep.c /home/w3cgrep/.
RUN cd /home/w3cgrep \
  && clang w3cgrep.c -I/usr/include/libxml2 -lxml2 -o /usr/local/bin/w3cgrep

FROM python:3
ARG YANG_ID_GID

ENV YANG_ID_GID "$YANG_ID_GID"
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUNBUFFERED=1

ENV VIRTUAL_ENV=/yangre
RUN bash -c 'echo -e  ${YANG_ID_GID}'
RUN groupadd -g ${YANG_ID_GID} -r yang \
  && useradd --no-log-init -r -g yang -u ${YANG_ID_GID} -d $VIRTUAL_ENV yang

RUN apt-get update \
  && apt-get -y install libxml2 uwsgi uwsgi-plugin-python3 \
    wget \
    gnupg2

RUN rm -rf /var/lib/apt/lists/*

RUN pip install virtualenv \
  && virtualenv --system-site-packages $VIRTUAL_ENV \
  && mkdir /etc/yangcatalog

ENV PYTHONPATH=$VIRTUAL_ENV/bin/python
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY . $VIRTUAL_ENV
COPY config.py-dist $VIRTUAL_ENV/config.py
RUN pip install uwsgi flask

COPY --from=build /usr/local/bin/w3cgrep /home/yang/w3cgrep/
COPY --from=build /usr/local/bin/yangre /usr/bin/
COPY --from=build /usr/local/lib/ /usr/local/lib/
COPY yangre.ini-dist $VIRTUAL_ENV/yangre.ini

RUN mkdir /var/run/yang

RUN chown -R yang:yang /var/run/yang
RUN chown -R yang:yang $VIRTUAL_ENV

# Support arbitrary UIDs as per OpenShift guidelines

WORKDIR $VIRTUAL_ENV

CMD chown -R yang:yang /var/run/yang && uwsgi --ini yangre.ini
