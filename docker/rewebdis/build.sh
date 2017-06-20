#!/bin/bash -e

export REPO=scythe/rewebdis
if [ ! -z $TRAVIS ]; then
    export TAG=$(if [ "$TRAVIS_BRANCH" == "master" ]; then echo 'latest'; else echo "$TRAVIS_BRANCH"; fi)
    docker login -e $DOCKER_EMAIL -u $DOCKER_USER -p $DOCKER_PASS
else
    export TAG='latest'
    export COMMIT=$(git rev-parse HEAD | cut -b -8)
fi

last_release_url=$(curl -sLo /dev/null -w '%{url_effective}' "https://github.com/scythe-suite/scythe-tester/releases/latest")
SCYTHE_TESTER_VERSION="${last_release_url##*/v}"

docker build -f Dockerfile -t $REPO:$COMMIT .
docker tag $REPO:$COMMIT $REPO:$TAG
docker tag $REPO:$COMMIT $REPO:$SCYTHE_TESTER_VERSION
if [ ! -z $TRAVIS ]; then
    docker tag $REPO:$COMMIT $REPO:travis-$TRAVIS_BUILD_NUMBER
fi
if [ ! -z $1 ]; then
    docker push $REPO
fi
