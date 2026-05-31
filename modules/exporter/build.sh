#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if command -v mvn &>/dev/null; then
    mvn clean package -q -DskipTests
elif [ -f "./mvnw" ]; then
    ./mvnw clean package -q -DskipTests
else
    echo "ERROR: Maven not found. Install Maven or add mvnw to this directory." >&2
    echo "  brew install maven   # macOS" >&2
    echo "  apt install maven    # Ubuntu/Debian" >&2
    exit 1
fi

echo "Build complete: target/report-exporter-0.1.0.jar"
