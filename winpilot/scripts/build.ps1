$ErrorActionPreference = 'Stop'
$env:MSBuildEnableWorkloadResolver = 'false'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$tool = Join-Path $PSScriptRoot '../tool'
dotnet publish (Join-Path $tool 'WindowsPilot.csproj') -c Release -r win-x64 --self-contained true -o (Join-Path $tool 'artifacts/app') -p:DebugType=None -p:DebugSymbols=false
if ($LASTEXITCODE -ne 0) { throw 'WinPilot 빌드 실패' }
& (Join-Path $tool 'artifacts/app/windows-pilot.exe') --self-test
if ($LASTEXITCODE -ne 0) { throw 'WinPilot 자체 검사 실패' }
