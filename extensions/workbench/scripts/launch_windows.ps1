param([string]$Model = 'prism-ml/bonsai-27b', [string]$VisionModel = 'workbench-vision-gemma',
      [ValidateSet('cuda','cpu')][string]$AsrDevice = 'cuda', [switch]$CameraTools,
      [ValidateRange(1024,65535)][int]$BrowserPort = 8876,
      [ValidateRange(1024,65535)][int]$SimPort = 8875,
      [ValidateRange(1024,65535)][int]$McpPort = 8801)
$ErrorActionPreference = 'Stop'
$extensionPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$linuxPath = (& wsl -d Ubuntu -- wslpath -a $extensionPath).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot access Ubuntu. Check wsl --list --verbose.' }
$visionArgument = if ([string]::IsNullOrWhiteSpace($VisionModel)) { 'none' } else { $VisionModel }
$controllerArgument = if ($CameraTools) { 'camera' } else { 'baseline' }
if ($CameraTools) {
    if (-not $PSBoundParameters.ContainsKey('BrowserPort')) { $BrowserPort = 8886 }
    if (-not $PSBoundParameters.ContainsKey('SimPort')) { $SimPort = 8885 }
    if (-not $PSBoundParameters.ContainsKey('McpPort')) { $McpPort = 8802 }
}
& wsl -d Ubuntu -- bash "$linuxPath/scripts/launch_wsl.sh" $Model $visionArgument $AsrDevice $controllerArgument $BrowserPort $SimPort $McpPort
exit $LASTEXITCODE
