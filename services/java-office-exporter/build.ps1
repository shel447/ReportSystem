$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$srcDir = Join-Path $root 'src'
$buildDir = Join-Path $root 'build\classes'
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
$javaFiles = Get-ChildItem -Path $srcDir -Recurse -Filter *.java | ForEach-Object { $_.FullName }
if (-not $javaFiles) { throw 'No Java source files found.' }
& javac -encoding UTF-8 -d $buildDir $javaFiles
Write-Output $buildDir
