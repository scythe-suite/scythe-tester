FROM openjdk:8-jdk-alpine
MAINTAINER Massimo Santini "santini@di.unimi.it"
ARG userid=1000
ARG sf_version=
ARG st_version=
RUN apk add --update python && rm -rf /var/cache/apk/*
RUN adduser -D -g "" -u $userid scythe
ADD https://github.com/scythe-suite/sim-fun-i/releases/download/v$sf_version/sf /bin
ADD https://github.com/scythe-suite/scythe-tester/releases/download/v$st_version/st /bin
RUN chmod a+rx /bin/sf /bin/st
USER scythe
ENV PYTHONPATH=/bin/sf:/bin/st
ENTRYPOINT [ "/bin/st" ]
CMD [ "start", "-c", "-w", "8" ]
