# Read-only readiness report. This does not install or configure anything.
$ErrorActionPreference = "Continue"
$report = [ordered]@{
    platform = "Windows workstation"
    scope = "GPU and WSL availability; no model or robot executed"
    gpu = $null
    wsl = $null
}
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $report.gpu = @(& nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader)
}
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    $report.wsl = @(& wsl --list --verbose)
}
$report | ConvertTo-Json -Depth 3
