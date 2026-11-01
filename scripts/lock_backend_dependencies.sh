#!/bin/sh
# Regenerates backend/requirements.txt and requirements-dev.txt, the whole dependency tree with
# its hashes (issue #82). Versions already in those files are kept unless a .in file asks for
# another one. To raise an indirect dependency, pass --upgrade-package <name>.
#
# It runs in the Python image of the Dockerfile, on Linux, because the tree is resolved for the
# system that compiles it and that is where it gets installed.
set -eu

repository=$(cd "$(dirname "$0")/.." && pwd)
python_image=$(sed -n 's/^FROM \(python:[^ ]*\).*/\1/p' "$repository/Dockerfile")
pip_tools=$(grep '^pip-tools==' "$repository/backend/requirements-dev.in")
compile="pip-compile --quiet --generate-hashes --allow-unsafe --strip-extras"

docker run --rm \
    --env PIP_ROOT_USER_ACTION=ignore \
    --volume "$repository/backend:/backend" \
    --workdir /backend \
    "$python_image" \
    sh -c "pip install --quiet '$pip_tools' \
        && $compile --output-file=requirements.txt \"\$@\" requirements.in \
        && $compile --output-file=requirements-dev.txt \"\$@\" requirements-dev.in" \
    lock "$@"
