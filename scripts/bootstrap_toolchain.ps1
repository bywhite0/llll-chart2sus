param(
    [string]$PythonVersion = "3.10",
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Ensure-RustToolchain {
    $hasRustup = Get-Command rustup -ErrorAction SilentlyContinue
    if (-not $hasRustup) {
        $hasWinget = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $hasWinget) {
            throw "rustup is missing and winget is unavailable. Install rustup manually first: https://rustup.rs/"
        }

        Write-Host "[bootstrap] Installing rustup via winget..."
        winget install --id Rustlang.Rustup --exact --accept-package-agreements --accept-source-agreements

        $rustupPath = Join-Path $env:USERPROFILE ".cargo\bin"
        if (Test-Path $rustupPath) {
            if ($env:Path -notlike "*$rustupPath*") {
                $env:Path = "$rustupPath;$env:Path"
            }
        }
    }

    Require-Command rustup
    Write-Host "[bootstrap] Ensuring stable Rust toolchain..."
    rustup toolchain install stable
    rustup default stable

    Require-Command cargo
    Require-Command rustc
}

function Ensure-PythonEnv {
    Require-Command uv

    Write-Host "[bootstrap] Preparing Python $PythonVersion with uv..."
    uv python install $PythonVersion | Out-Host

    Write-Host "[bootstrap] Creating virtual environment at $VenvPath..."
    uv venv --python $PythonVersion $VenvPath | Out-Host

    $venvPython = Join-Path (Resolve-Path $VenvPath) "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        throw "Virtual environment python not found: $venvPython"
    }

    Write-Host "[bootstrap] Installing project + dev dependencies..."
    uv pip install --python $venvPython -e ".[dev]" | Out-Host
}

Write-Host "[bootstrap] Starting toolchain bootstrap..."
Ensure-RustToolchain
Ensure-PythonEnv
Write-Host "[bootstrap] Done."
