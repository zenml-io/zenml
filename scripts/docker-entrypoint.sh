#!/bin/bash
ulimit -n 65535
exec "$@"