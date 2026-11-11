param([switch]$Resolve, [switch]$Models)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
function Invoke-Uv {
    & uv @args
    if ($LASTEXITCODE -ne 0) { throw "uv command failed: $args" }
}
if (!(Test-Path '.venv')) { Invoke-Uv venv --python 3.12 }
if ($Resolve) { Invoke-Uv lock }
Invoke-Uv sync --locked
Invoke-Uv pip check --python .venv/Scripts/python.exe
$validationArgs = @('scripts/validate_environment.py')
if ($Models) { $validationArgs += '--dummy' }
& .venv/Scripts/python.exe @validationArgs
if ($LASTEXITCODE -ne 0) { throw 'Environment validation failed; inspect outputs/environment_validation.json' }
