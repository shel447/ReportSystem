$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$jar = Join-Path $root 'target\report-exporter-0.1.0.jar'

if (-not (Test-Path $jar)) {
    Write-Output 'JAR not found. Building first...'
    & (Join-Path $root 'build.ps1')
}

& java -jar $jar @args
