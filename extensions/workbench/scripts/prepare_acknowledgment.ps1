$ErrorActionPreference = 'Stop'
$extensionDirectory = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$outputDirectory = Join-Path $extensionDirectory '.cache/local-speech'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if (-not $synth.Voice) { throw 'No accessible installed Windows synthesis voice.' }
    $outputFile = Join-Path $outputDirectory 'acknowledgment.wav'
    $synth.SetOutputToWaveFile($outputFile)
    $prompt = $synth.SpeakAsync('Let me check.')
    $deadline = (Get-Date).AddSeconds(15)
    while (-not $prompt.IsCompleted -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 20
    }
    if (-not $prompt.IsCompleted) { $synth.SpeakAsyncCancelAll(); throw 'Acknowledgment synthesis timed out.' }
    if ($prompt.Exception) { throw $prompt.Exception }
    $synth.SetOutputToNull()
    if ((Get-Item -LiteralPath $outputFile).Length -le 44) { throw 'No acknowledgment audio generated.' }
    @{text='Let me check.';voice=$synth.Voice.Name;sha256=(Get-FileHash -LiteralPath $outputFile -Algorithm SHA256).Hash.ToLower()} |
        ConvertTo-Json | Set-Content (Join-Path $outputDirectory 'acknowledgment.json')
} finally { $synth.Dispose() }
Write-Output 'Prepared local acknowledgment audio; no microphone or speaker output.'
