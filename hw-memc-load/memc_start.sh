#! /bin/bash

# Если запущены, удалим
killall memcached

# idfa
memcached -d -l 127.0.0.1:33013 -m 256 -u memcache

# gaid
memcached -d -l 127.0.0.1:33014 -m 256 -u memcache

# adid
memcached -d -l 127.0.0.1:33015 -m 256 -u memcache

# dvid
memcached -d -l 127.0.0.1:33016 -m 256 -u memcache

netstat -nap | grep memcached
