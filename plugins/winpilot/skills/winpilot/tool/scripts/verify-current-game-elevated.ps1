# 사용자가 승인한 경우에만 실행한다. 드라이버·서비스를 설치하지 않는다.
param([string]$Plan)
$ErrorActionPreference = 'Stop'
$pilotRoot = Split-Path -Parent $PSScriptRoot
$pilotExe = if ($env:WINDOWS_PILOT_EXE) { $env:WINDOWS_PILOT_EXE } else { Join-Path $pilotRoot 'artifacts\app\windows-pilot.exe' }
if (-not (Test-Path -LiteralPath $pilotExe)) {
    throw '검토한 실행 파일을 찾지 못했습니다.'
}
$pilotGames = @(Get-Process -Name MabinogiMobile -ErrorAction Stop)
if ($pilotGames.Count -ne 1) { throw '마비노기 모바일 프로세스가 정확히 하나여야 합니다.' }
$pilotPid = $pilotGames[0].Id
$pilotStarted = $pilotGames[0].StartTime.ToUniversalTime().Ticks
$pilotArguments = @('--verify-game', "$pilotPid", "$pilotStarted")
if ($Plan) {
    $pilotPlanPath = (Resolve-Path -LiteralPath $Plan).Path
    $pilotPlan = Get-Content -LiteralPath $pilotPlanPath -Raw | ConvertFrom-Json
    if ($pilotPlan.window.pid -ne $pilotPid -or $pilotPlan.window.started -ne $pilotStarted) {
        throw '관찰한 게임 프로세스가 변경됐습니다.'
    }
    $pilotArguments = @('--verify-game-click', ('"{0}"' -f $pilotPlanPath))
}
# 콘솔은 숨기고 작은 상태 알림만 표시한다. UAC 이후 대상 확인과 검증은 자동 진행한다.
Start-Process -FilePath $pilotExe -Verb RunAs -WindowStyle Hidden -PassThru -ArgumentList $pilotArguments
