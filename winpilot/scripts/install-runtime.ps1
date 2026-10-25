param(
    [string]$Archive,
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'WinPilot'),
    [switch]$Stdio
)
$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../runtime/distribution.json') -Raw | ConvertFrom-Json
if ($manifest.version -notmatch '^\d+\.\d+\.\d+$' -or $manifest.sha256 -notmatch '^[a-f0-9]{64}$') { throw '잘못된 배포 manifest입니다.' }
$root = [IO.Path]::GetFullPath($InstallRoot)
$destination = Join-Path $root $manifest.version

function Get-Sha256([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}

function Assert-Runtime([string]$Directory) {
    $base = [IO.Path]::GetFullPath($Directory).TrimEnd('\') + '\'
    $expected = @($manifest.files.PSObject.Properties)
    $actual = @(Get-ChildItem -LiteralPath $Directory -File -Recurse)
    if ($actual.Count -ne $expected.Count) { throw '설치 파일 목록이 배포본과 다릅니다.' }
    foreach ($entry in $expected) {
        $path = [IO.Path]::GetFullPath((Join-Path $Directory $entry.Name))
        if (-not $path.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) { throw '배포 파일 경로가 설치 폴더를 벗어납니다.' }
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-Sha256 $path) -ne $entry.Value) { throw "설치 파일 해시 불일치: $($entry.Name)" }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Directory 'windows-pilot.exe'))) { throw '실행 파일이 없습니다.' }
}

if (Test-Path -LiteralPath $destination) {
    Assert-Runtime $destination
} else {
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    $stage = Join-Path $root ('.staging-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage | Out-Null
    try {
        $zip = Join-Path $stage 'runtime.zip'
        if ($Archive) { Copy-Item -LiteralPath $Archive -Destination $zip }
        else {
            $url = "https://github.com/oozoofrog/oozoofrog-plugin/releases/download/winpilot-v$($manifest.version)/winpilot-$($manifest.version)-win-x64.zip"
            Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zip
        }
        if ((Get-Sha256 $zip) -ne $manifest.sha256) { throw '배포 ZIP 해시가 일치하지 않습니다.' }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $archiveFile = [IO.Compression.ZipFile]::OpenRead($zip)
        try {
            foreach ($entry in $archiveFile.Entries) {
                if ($entry.FullName -match '(^[/\\]|(^|[/\\])\.\.([/\\]|$)|:)' ) { throw '안전하지 않은 ZIP 경로입니다.' }
            }
        } finally { $archiveFile.Dispose() }
        $unpacked = Join-Path $stage 'app'
        [IO.Compression.ZipFile]::ExtractToDirectory($zip, $unpacked)
        Assert-Runtime $unpacked
        [IO.Directory]::Move($unpacked, $destination)
    } finally {
        $resolvedStage = [IO.Path]::GetFullPath($stage)
        if ($resolvedStage.StartsWith($root.TrimEnd('\') + '\.staging-', [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $resolvedStage -Recurse -Force
        }
    }
}
$exe = Join-Path $destination 'windows-pilot.exe'
if ($Stdio) { & $exe --stdio; exit $LASTEXITCODE }
else { $exe }
