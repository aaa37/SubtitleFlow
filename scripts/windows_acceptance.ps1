param([Parameter(Mandatory=$true)][string]$AppFolder,
      [Parameter(Mandatory=$true)][string]$ModelFile,
      [Parameter(Mandatory=$true)][string]$SpeechFile,
      [string]$EvidenceFolder = "$env:TEMP/SubtitleFlowAcceptance")
$ErrorActionPreference = 'Stop'
$exe = Join-Path (Resolve-Path $AppFolder).Path 'SubtitleFlow.exe'
New-Item -ItemType Directory -Force $EvidenceFolder | Out-Null
$EvidenceFolder = (Resolve-Path $EvidenceFolder).Path
$env:SUBTITLEFLOW_HOME = Join-Path $EvidenceFolder 'app-data'
function Run-Test([string[]]$Arguments, [int]$Timeout) {
    $quoted = $Arguments | ForEach-Object { '"{0}"' -f $_ }
    $process = Start-Process -FilePath $exe -ArgumentList $quoted -PassThru
    if (-not $process.WaitForExit($Timeout)) { $process.Kill(); throw 'Test timed out' }
    if ($process.ExitCode -ne 0) { throw "Test failed: $($process.ExitCode)" }
}
Run-Test @('--smoke-test', (Join-Path $EvidenceFolder 'windows-smoke.json')) 60000
Run-Test @('--self-test', (Resolve-Path $SpeechFile).Path, (Resolve-Path $ModelFile).Path,
    (Join-Path $EvidenceFolder 'frozen-e2e')) 600000
$os = Get-CimInstance Win32_OperatingSystem
$signature = Get-AuthenticodeSignature -FilePath $exe
@{
    os = $os.Caption
    build = $os.BuildNumber
    arch = $os.OSArchitecture
    exe_sha256 = (Get-FileHash -Algorithm SHA256 -Path $exe).Hash.ToLower()
    signature_status = $signature.Status.ToString()
    tested_at = (Get-Date).ToUniversalTime().ToString('o')
    note = 'Automated startup and ASR only; GUI layout and DLL replacement need separate checks.'
} | ConvertTo-Json | Set-Content (Join-Path $EvidenceFolder 'machine.json') -Encoding utf8
Write-Output "Evidence: $EvidenceFolder"
