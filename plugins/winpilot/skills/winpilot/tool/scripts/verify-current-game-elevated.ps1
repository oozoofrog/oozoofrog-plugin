# 사용자가 승인한 경우에만 실행한다. 드라이버·서비스를 설치하지 않는다.
param([string]$Plan)
$ErrorActionPreference = 'Stop'
$pilotRoot = Split-Path -Parent $PSScriptRoot
$pilotExe = if ($env:WINDOWS_PILOT_EXE) { $env:WINDOWS_PILOT_EXE } else { Join-Path $pilotRoot 'artifacts\app\windows-pilot.exe' }
if (-not (Test-Path -LiteralPath $pilotExe)) {
    throw '검토한 실행 파일을 찾지 못했습니다.'
}
if ($Plan) {
    & $pilotExe --elevate-game-click (Resolve-Path -LiteralPath $Plan).Path
    if ($LASTEXITCODE -ne 0) { throw '네이티브 UAC 요청이 완료되지 않았습니다. 결과를 확인하고 자동 재시도하지 마세요.' }
    return
}
& $pilotExe --elevate-game
if ($LASTEXITCODE -ne 0) { throw '네이티브 UAC 요청이 완료되지 않았습니다. 결과를 확인하고 자동 재시도하지 마세요.' }
