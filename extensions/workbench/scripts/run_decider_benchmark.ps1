param(
    [Parameter(Mandatory=$true)][string]$RuntimePython,
    [Parameter(Mandatory=$true)][string]$CheckpointPath,
    [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$extensionPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$linuxPath = (& wsl -d Ubuntu -- wslpath -a $extensionPath).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the extension in WSL.' }
foreach ($simPort in @(8875,8885)) {
    $simState = Invoke-RestMethod -Uri "http://127.0.0.1:$simPort/state" -TimeoutSec 5
    if ($simState.busy) { throw "Simulator $simPort is busy; benchmark did not start." }
}
$modelInventory = (& lms ps --json | ConvertFrom-Json)
$restoreVision = @($modelInventory | Where-Object identifier -eq 'workbench-vision-gemma').Count -gt 0
try {
    if ($restoreVision) {
        Write-Host 'Temporarily freeing the vision model for read-only decision evaluation.'
        & lms unload workbench-vision-gemma
        if ($LASTEXITCODE -ne 0) { throw 'Vision unload failed; benchmark did not start.' }
    }
    & wsl -d Ubuntu -- env HF_HUB_DISABLE_IMPLICIT_TOKEN=1 HF_HUB_DISABLE_XET=1 HF_HUB_OFFLINE=1 $RuntimePython "$linuxPath/scripts/benchmark_decider.py" --checkpoint $CheckpointPath --output $OutputPath
    $benchmarkExitCode = $LASTEXITCODE
} finally {
    if ($restoreVision) {
        Write-Host 'Restoring the workbench vision model.'
        & lms load google/gemma-4-31b --identifier workbench-vision-gemma --gpu max --context-length 4096 --parallel 1 --yes
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Vision restoration failed; inspect LM Studio.' }
    }
}
if ($null -ne $benchmarkExitCode) { exit $benchmarkExitCode }
