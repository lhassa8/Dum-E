$ErrorActionPreference = 'Stop'
$extension = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runPath = Join-Path $extension ('runs/mink-live-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $runPath | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'launch_mink_experiment.sh') -Destination (Join-Path $runPath 'launcher.sh')
$linuxExtension = (& wsl -d Ubuntu -- wslpath -a $extension).Trim()
$linuxRun = (& wsl -d Ubuntu -- wslpath -a $runPath).Trim()
$gatewayLine = (& wsl -d Ubuntu -- ip -4 route show default).Trim()
$gateway = ($gatewayLine -split '\s+')[2]
if (-not $gateway) { throw 'No WSL default gateway; launch did not start.' }
Write-Host "Experimental workbench: http://127.0.0.1:8896; evidence: $runPath"
& wsl -d Ubuntu -- bash "$linuxRun/launcher.sh" $linuxExtension $linuxRun "http://${gateway}:1234"
exit $LASTEXITCODE
