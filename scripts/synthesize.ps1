param([Parameter(Mandatory=$true)][string]$OutputFile)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synth.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet, [System.Speech.Synthesis.VoiceAge]::NotSet, 0, [System.Globalization.CultureInfo]::GetCultureInfo('en-US'))
    $synth.SetOutputToWaveFile($OutputFile)
    $synth.Speak('Hello, welcome to Subtitle Flow. This is a local speech recognition test. We create subtitles on your computer.')
} finally { $synth.Dispose() }
