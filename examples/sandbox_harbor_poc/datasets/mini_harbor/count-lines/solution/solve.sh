#!/usr/bin/env bash
wc -l < /app/input.txt | tr -d ' ' > /app/result.txt
