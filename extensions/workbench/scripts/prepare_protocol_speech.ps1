param([Parameter(Mandatory=$true)][string]$Protocol,
      [Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = 'Stop'
$recipe = Get-Content -LiteralPath $Protocol -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $Output -ErrorAction Stop | Out-Null
$outputDirectory = (Resolve-Path -LiteralPath $Output).Path
Copy-Item -LiteralPath $Protocol -Destination (Join-Path $outputDirectory 'protocol.json')
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if (-not $synth.Voice) { throw 'No accessible installed Windows synthesis voice.' }
    @{voice=$synth.Voice.Name;rate=$synth.Rate;volume=$synth.Volume} |
        ConvertTo-Json | Set-Content (Join-Path $outputDirectory 'voice.json')
    foreach ($entry in $recipe.source_text.PSObject.Properties) {
        if ($entry.Name -notmatch '^[a-z][a-z-]*$') { throw 'Invalid source filename.' }
        $synth.SetOutputToWaveFile((Join-Path $outputDirectory ($entry.Name + '.wav')))
        $prompt = $synth.SpeakAsync([string]$entry.Value)
        $deadline = (Get-Date).AddSeconds(30)
        while (-not $prompt.IsCompleted -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 20
        }
        if (-not $prompt.IsCompleted) {
            $synth.SpeakAsyncCancelAll()
            throw ('Timed out synthesizing ' + $entry.Name)
        }
        if ($prompt.Exception) { throw $prompt.Exception }
        $synth.SetOutputToNull()
        $generated = Get-Item -LiteralPath (Join-Path $outputDirectory ($entry.Name + '.wav'))
        if ($generated.Length -le 44) { throw ('No audio generated for ' + $entry.Name) }
    }
} finally { $synth.Dispose() }
Write-Output "Generated protocol speech at $outputDirectory; no microphone or speaker output."
