$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }
$cargoFromHome = Join-Path $env:USERPROFILE ".cargo\bin\cargo.exe"
$rustcFromHome = Join-Path $env:USERPROFILE ".cargo\bin\rustc.exe"
$cargoExe = if (Test-Path $cargoFromHome) { $cargoFromHome } else { "cargo" }
$rustcExe = if (Test-Path $rustcFromHome) { $rustcFromHome } else { "rustc" }

function Print-Version {
    param(
        [string]$Label,
        [string[]]$Command
    )
    try {
        $out = & $Command[0] $Command[1..($Command.Length - 1)] 2>&1
        if (-not $out) {
            $out = "<no output>"
        }
        Write-Host ("{0}: {1}" -f $Label, ($out -join " ").Trim())
    }
    catch {
        Write-Host ("{0}: <missing>" -f $Label)
    }
}

Write-Host "[doctor] Tool versions"
Print-Version "python" @($pythonExe, "--version")
Print-Version "pip" @("pip", "--version")
Print-Version "uv" @("uv", "--version")
Print-Version "rustc" @($rustcExe, "--version")
Print-Version "cargo" @($cargoExe, "--version")

Write-Host "[doctor] scores (python parser) check"
$scoresSrc = Join-Path $repoRoot "scores\src"
$originalPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = "$scoresSrc;$originalPythonPath"
try {
    & $pythonExe -m pjsekai.scores --help | Out-Null
    Write-Host "scores: ok"
}
catch {
    Write-Host "scores: failed"
    throw
}
finally {
    $env:PYTHONPATH = $originalPythonPath
}

Write-Host "[doctor] pjsekai-scores-rs (rust parser) check"
if (-not (Test-Path $cargoExe) -and -not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    throw "cargo is not installed. Run ./scripts/bootstrap_toolchain.ps1 first."
}
Push-Location (Join-Path $repoRoot "pjsekai-scores-rs")
try {
    & $cargoExe run -- --help | Out-Null
    Write-Host "pjsekai-scores-rs: ok"
}
finally {
    Pop-Location
}

Write-Host "[doctor] All checks passed."
