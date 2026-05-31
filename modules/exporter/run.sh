#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JAR="$SCRIPT_DIR/target/report-exporter-0.1.0.jar"

if [ ! -f "$JAR" ]; then
    echo "JAR not found. Building first..."
    bash "$SCRIPT_DIR/build.sh"
fi

java -jar "$JAR" "$@"
