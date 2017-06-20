#!/bin/bash -e

cp ../../release/st .

export VERSION=$(grep VERSION ../../src/st/__init__.py  | cut -d "'" -f2)
export REPO=scythe/testrunner
export TAG='latest'
export COMMIT=$(git rev-parse HEAD | cut -b -8)

last_release_url=$(curl -sLo /dev/null -w '%{url_effective}' "https://github.com/scythe-suite/sim-fun-i/releases/latest")
SIM_FUN_I_VERSION="${last_release_url##*/}"

docker build -f Dockerfile --build-arg userid="$(id -u)" --build-arg version="$SIM_FUN_I_VERSION" -t $REPO:$COMMIT .
docker tag $REPO:$COMMIT $REPO:$TAG
docker tag $REPO:$COMMIT $REPO:$VERSION
if [ ! -z $1 ]; then
    docker push $REPO
fi

rm -f st
