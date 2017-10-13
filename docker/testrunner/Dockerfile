FROM openjdk:8-jdk-alpine
MAINTAINER Massimo Santini "santini@di.unimi.it"
RUN apk add --no-cache --update python
COPY sf /bin
COPY st /bin
COPY wait-for /bin
RUN chmod a+rx /bin/sf /bin/st /bin/wait-for
ENV PYTHONPATH=/bin/sf:/bin/st
CMD [ "sh", "-c", "/bin/wait-for $SCYTHE_REDIS_HOST:6379 -- /bin/st process -c -w 8" ]
