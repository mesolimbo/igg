#!/bin/bash
mkdir -p dist/package || true
pipenv requirements > dist/requirements.txt
cp -r src/* dist/package

#export VOL="${PWD}/dist"
export VOL="$(cygpath -w "${PWD}/dist")"  # For Git Bash

docker build -t lambda-igg-build .
docker run --rm -v "${VOL}:/tmp/dist" lambda-igg-build \
sh -c "cd /app/package && zip -r /tmp/dist/deployment-package.zip ."
