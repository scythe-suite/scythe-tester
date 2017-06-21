#!/bin/bash -e

cp ../../release/st .

export VERSION=$(grep VERSION ../../src/st/__init__.py  | cut -d "'" -f2)
export REPO=scythe/testrunner
export TAG='latest'
export COMMIT=$(git rev-parse HEAD | cut -b -8)

last_release_url=$(curl -sLo /dev/null -w '%{url_effective}' "https://github.com/scythe-suite/sim-fun-i/releases/latest")
SIM_FUN_I_VERSION="${last_release_url##*/}"

if [ ! -r sf ]; then
    curl -sLO "https://github.com/scythe-suite/sim-fun-i/releases/download/$SIM_FUN_I_VERSION/sf"
fi

docker build -t $REPO:$COMMIT .
docker tag $REPO:$COMMIT $REPO:$TAG
docker tag $REPO:$COMMIT $REPO:$VERSION
if [ ! -z $1 ]; then
    docker push $REPO
fi

rm -f sf st

echo "st tool: $(docker run -t --rm scythe/testrunner version)"
echo "sf tool: $(docker run -t --rm --entrypoint sf scythe/testrunner version)"
