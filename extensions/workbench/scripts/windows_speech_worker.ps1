$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
function Write-Reply($value) {
    [Console]::WriteLine(($value | ConvertTo-Json -Compress -Depth 4))
}
try {
    if (-not $synth.Voice) { throw 'No accessible installed Windows voice.' }
    Write-Reply @{kind='ready';voice=$synth.Voice.Name;rate=$synth.Rate;local=$true}
    while ($null -ne ($line = [Console]::ReadLine())) {
        $request = $null
        try {
            if ($line.Length -gt 4096) { throw 'Speech request is too large.' }
            $request = $line | ConvertFrom-Json
            if ($request.id -notmatch '^[a-f0-9]{32}$') { throw 'Invalid speech request identity.' }
            if (-not ($request.text -is [string]) -or $request.text.Length -lt 1 -or $request.text.Length -gt 500) {
                throw 'Speech text must contain 1–500 characters.'
            }
            $timer = [Diagnostics.Stopwatch]::StartNew()
            $memory = New-Object IO.MemoryStream
            try {
                $synth.SetOutputToWaveStream($memory)
                $prompt = $synth.SpeakAsync($request.text)
                $deadline = (Get-Date).AddSeconds(10)
                while (-not $prompt.IsCompleted -and (Get-Date) -lt $deadline) {
                    Start-Sleep -Milliseconds 5
                }
                if (-not $prompt.IsCompleted) {
                    $synth.SpeakAsyncCancelAll()
                    throw 'Windows synthesis exceeded its deadline.'
                }
                if ($prompt.Exception) { throw $prompt.Exception }
                $synth.SetOutputToNull()
                $bytes = $memory.ToArray()
                if ($bytes.Length -le 44 -or $bytes.Length -gt 2000000) { throw 'Invalid synthesized audio size.' }
                Write-Reply @{kind='audio';id=$request.id;voice=$synth.Voice.Name;local=$true;
                    synthesis_ms=$timer.Elapsed.TotalMilliseconds;wav=[Convert]::ToBase64String($bytes)}
            } finally { $memory.Dispose() }
        } catch {
            $synth.SpeakAsyncCancelAll()
            $synth.SetOutputToNull()
            Write-Reply @{kind='error';id=$request.id;error=$_.Exception.Message}
        }
    }
} finally { $synth.Dispose() }
