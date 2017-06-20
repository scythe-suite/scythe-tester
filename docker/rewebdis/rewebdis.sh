#!/bin/sh
set -e

chown -R redis .
su-exec redis webdis /etc/webdis.prod.json 
exec su-exec redis redis-server --appendonly yes
