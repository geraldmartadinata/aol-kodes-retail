# PowerShell runner for Martadinata CSV Imputer
$uvPath = "C:\Users\steph\AppData\Local\hermes\bin\uv.exe"
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $uvCmd = "uv"
} else {
    $uvCmd = $uvPath
}

& $uvCmd run "$PSScriptRoot\imputer.py" @args
