FROM alpine:3.6
MAINTAINER Massimo Santini "santini@di.unimi.it"

ENV WEBDIS_RELEASE 0.1.3
ENV WEBDIS_DOWNLOAD_URL https://github.com/nicolasff/webdis/archive/0.1.2.tar.gz
ENV WEBDIS_DOWNLOAD_SHA 8e46093af006e35354f6b3d58a70e3825cd0c074893be318f1858eddbe1cda86

RUN set -ex; \
	\
	apk add --no-cache --virtual .build-deps \
		coreutils \
		gcc \
		linux-headers \
		make \
		musl-dev \
		openssl \
		libevent-dev \
		bsd-compat-headers \
	; \
	\
	wget -O webdis.tar.gz "$WEBDIS_DOWNLOAD_URL"; \
	echo "$WEBDIS_DOWNLOAD_SHA *webdis.tar.gz" | sha256sum -c -; \
	mkdir -p /usr/src/webdis; \
	tar -xzf webdis.tar.gz -C /usr/src/webdis --strip-components=1; \
	rm webdis.tar.gz; \
	\
	make -C /usr/src/webdis -j "$(nproc)"; \
	make -C /usr/src/webdis install; \
	\
	rm -r /usr/src/webdis; \
	\
	apk del .build-deps; \
	apk add --no-cache libevent supervisor redis

RUN mkdir /data && chown redis:redis /data
VOLUME /data
WORKDIR /data

COPY supervisord.conf /etc/supervisord.conf

EXPOSE 7379
EXPOSE 6379

ENTRYPOINT	["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
