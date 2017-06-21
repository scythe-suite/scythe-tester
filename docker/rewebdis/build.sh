#!/bin/bash -e

export VERSION=$(grep VERSION ../../src/st/__init__.py  | cut -d "'" -f2)
export REPO=scythe/rewebdis
export TAG='latest'
export COMMIT=$(git rev-parse HEAD | cut -b -8)

docker build -t $REPO:$COMMIT .
docker tag $REPO:$COMMIT $REPO:$TAG
docker tag $REPO:$COMMIT $REPO:$VERSION
if [ ! -z $1 ]; then
    docker push $REPO
fi
