#!/bin/bash
docker run --rm -d --name postgres -p 5432:5432 -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=password postgres:13
