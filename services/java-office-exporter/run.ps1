$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$buildScript = Join-Path $root 'build.ps1'
$buildDir = & powershell -ExecutionPolicy Bypass -File $buildScript
$artifactsDir = Join-Path $root 'artifacts'
New-Item -ItemType Directory -Force -Path $artifactsDir | Out-Null
$argsList = @('-cp', $buildDir, 'report.system.exporter.JavaOfficeExporterServer', '--host', '127.0.0.1', '--port', '18500', '--artifacts-dir', $artifactsDir)
& java @argsList
