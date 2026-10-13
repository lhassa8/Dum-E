param([string]$Model = 'prism-ml/bonsai-27b', [string]$VisionModel = 'workbench-vision-gemma',
      [ValidateSet('cuda','cpu')][string]$AsrDevice = 'cuda')
$ErrorActionPreference = 'Stop'
$extensionPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$linuxPath = (& wsl -d Ubuntu -- wslpath -a $extensionPath).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot access Ubuntu. Check wsl --list --verbose.' }
$visionArgument = if ([string]::IsNullOrWhiteSpace($VisionModel)) { 'none' } else { $VisionModel }
& wsl -d Ubuntu -- bash "$linuxPath/scripts/launch_wsl.sh" $Model $visionArgument $AsrDevice
exit $LASTEXITCODE
