<#
.SYNOPSIS
    Install / update the CursorBridge script into DaVinci Resolve's Utility
    scripts folder so it appears under Workspace > Scripts > Utility > CursorBridge.

.DESCRIPTION
    Copies src\CursorBridge.py into the per-user Resolve Fusion scripts folder
    (and the shared PROGRAMDATA folder if present). Re-run this after every
    bridge update — stale copies are the #1 source of version drift.

.NOTES
    Windows / DaVinci Resolve (Free or Studio).
#>

[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $repoRoot 'src\CursorBridge.py'

if (-not (Test-Path $source)) {
    Write-Error "Cannot find $source"
    exit 1
}

# Candidate Resolve Utility scripts folders (per-user first, then shared).
$targets = @(
    Join-Path $env:APPDATA   'Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility'
    Join-Path $env:PROGRAMDATA 'Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility'
)

$installed = @()
foreach ($dir in $targets) {
    $parent = Split-Path -Parent $dir
    # Only install into a location whose Resolve tree already exists, unless -Force.
    if ((Test-Path $parent) -or $Force) {
        try {
            if (-not (Test-Path $dir)) {
                New-Item -ItemType Directory -Force -Path $dir | Out-Null
            }
            Copy-Item -Path $source -Destination (Join-Path $dir 'CursorBridge.py') -Force
            $installed += $dir
            Write-Host "[install] Copied CursorBridge.py -> $dir" -ForegroundColor Green
        } catch {
            Write-Warning "[install] Could not write to $dir : $_"
        }
    }
}

if ($installed.Count -eq 0) {
    Write-Warning "No Resolve scripts folder found. Is DaVinci Resolve installed?"
    Write-Host "Re-run with -Force to create the per-user folder anyway:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File install.ps1 -Force"
    exit 1
}

# Report the bridge version being installed (parsed from the source).
$verLine = Select-String -Path $source -Pattern 'BRIDGE_VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
if ($verLine) {
    $ver = $verLine.Matches[0].Groups[1].Value
    Write-Host "[install] Installed CursorBridge version $ver" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. In DaVinci Resolve: Workspace > Scripts > Utility > CursorBridge"
Write-Host "  2. Open Workspace > Console and confirm 'Bridge is running (read + write)'"
Write-Host "  3. If you changed the MCP server, restart Claude Code so it reloads."
Write-Host ""
Write-Host "The bridge is idempotent — re-running CursorBridge replaces any prior instance."
