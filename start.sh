#!/bin/bash
set -e

mkdir -p /data/.hermes/sessions /data/.hermes/skills /data/.hermes/workspace /data/.hermes/pairing

# The volume mounted at /data hides image-time files, so sync the managed skill
# on every boot while leaving all other user-installed skills untouched.
rm -rf /data/.hermes/skills/render-tool
cp -R /app/skills/render-tool /data/.hermes/skills/render-tool

exec python /app/server.py
