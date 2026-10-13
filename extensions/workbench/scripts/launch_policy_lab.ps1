param([ValidateRange(0,3600)][int]$DurationSeconds = 0)
$ErrorActionPreference = 'Stop'
$extensionPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$linuxPath = (& wsl -d Ubuntu -- wslpath -a $extensionPath).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot access Ubuntu.' }
$models = (& lms ps --json | ConvertFrom-Json)
$restoreVision = @($models | Where-Object identifier -eq 'workbench-vision-gemma').Count -gt 0
try {
    if ($restoreVision) {
        Write-Host 'Temporarily freeing the local vision model for the GPU policy. Workbench voice/tools remain available.'
        & lms unload workbench-vision-gemma
        if ($LASTEXITCODE -ne 0) { throw 'Vision unload failed; policy lab was not started.' }
    }
    & wsl -d Ubuntu -- bash "$linuxPath/scripts/launch_policy_lab.sh" $DurationSeconds
    $labExitCode = $LASTEXITCODE
} finally {
    if ($restoreVision) {
        Write-Host 'Restoring the workbench vision model.'
        & lms load google/gemma-4-31b --identifier workbench-vision-gemma --gpu max --context-length 4096 --parallel 1 --yes
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Vision restoration failed; inspect LM Studio before using camera assistance.' }
    }
}
if ($null -ne $labExitCode) { exit $labExitCode }
