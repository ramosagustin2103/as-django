#!/bin/sh

set -o errexit
set -o pipefail
set -o nounset


celery -A adminsmart.taskapp beat -l INFO
