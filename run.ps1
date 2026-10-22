# PowerShell runner for CSV Imputer & 3NF Normalizer
if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv run "$PSScriptRoot\imputer.py" @args
} else {
    & python "$PSScriptRoot\imputer.py" @args
}
