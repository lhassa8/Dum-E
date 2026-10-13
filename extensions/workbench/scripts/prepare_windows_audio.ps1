param([Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $Output -ErrorAction Stop | Out-Null
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$phrases = [ordered]@{
    fetch = 'Bring me the screwdriver.'
    question = 'What are you doing?'
    change = 'Actually bring me the wrench instead.'
    stop = 'Stop.'
    resume = 'Resume, please.'
    return = 'Put it back.'
}
try {
    foreach ($name in $phrases.Keys) {
        $synth.SetOutputToWaveFile((Join-Path $Output "$name.wav"))
        $synth.Speak($phrases[$name])
    }
} finally { $synth.Dispose() }
Write-Output "Saved local synthetic speech fixtures: $Output (no microphone used)."
