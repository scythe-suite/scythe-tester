FROM openjdk:8-jdk-alpine
MAINTAINER Massimo Santini "santini@di.unimi.it"
RUN apk add --no-cache --update python
COPY sf /bin
COPY st /bin
RUN chmod a+rx /bin/sf /bin/st
ENV PYTHONPATH=/bin/sf:/bin/st
ENTRYPOINT [ "/bin/st" ]
CMD [ "process", "-c", "-w", "8" ]
