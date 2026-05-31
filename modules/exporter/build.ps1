$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Push-Location $root
try {
    if (Get-Command mvn -ErrorAction SilentlyContinue) {
        & mvn clean package -q -DskipTests
    } elseif (Test-Path .\mvnw.cmd) {
        & .\mvnw.cmd clean package -q -DskipTests
    } else {
        Write-Error 'Maven not found. Install Maven or add mvnw.cmd to this directory.'
        exit 1
    }
    Write-Output "Build complete: target\report-exporter-0.1.0.jar"
} finally {
    Pop-Location
}
