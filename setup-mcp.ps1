# ==========================================================
# AetherScope V2 - MCP Configurator pour AetherCraft
# ==========================================================
param(
    [string]$Port = "3030"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " AETHERSCOPE V2 - CONFIGURATION MCP AETHERCRAFT           " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$mcpExe = "C:\Users\1234\Desktop\Projets\aether-engine\aetherscope-mcp.exe"
$projectPath = "C:\Users\1234\Desktop\Projets\aethercraft"

if (-not (Test-Path $mcpExe)) {
    Write-Host "[ERREUR] $mcpExe est introuvable." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Serveur MCP detecte : $mcpExe" -ForegroundColor Green
Write-Host "[INFO] Port cible : $Port" -ForegroundColor DarkGray
Write-Host "[INFO] Projet cible : $projectPath" -ForegroundColor DarkGray
Write-Host ""

$serverObj = [PSCustomObject]@{
    command = $mcpExe
    args = @("--port", $Port, "--path", $projectPath)
}

function Update-McpConfig {
    param([string]$Path, [string]$Client)
    try {
        $parentDir = Split-Path -Parent $Path
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Force -Path $parentDir | Out-Null
        }
        $cfg = $null
        if (Test-Path $Path) {
            $raw = Get-Content -Path $Path -Raw -Encoding UTF8
            if (-not [string]::IsNullOrWhiteSpace($raw)) {
                try { $cfg = $raw | ConvertFrom-Json } catch { $cfg = $null }
            }
        }
        if (-not $cfg) {
            $cfg = [PSCustomObject]@{ mcpServers = [PSCustomObject]@{} }
        }
        if (-not $cfg.PSObject.Properties['mcpServers']) {
            $cfg | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{})
        }
        if ($cfg.mcpServers.PSObject.Properties['aetherscope']) {
            $cfg.mcpServers.aetherscope = $serverObj
        } else {
            $cfg.mcpServers | Add-Member -MemberType NoteProperty -Name "aetherscope" -Value $serverObj
        }
        $jsonOutput = $cfg | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($Path, $jsonOutput, [System.Text.Encoding]::UTF8)
        Write-Host "  [OK] $Client configure avec succes :" -ForegroundColor Green
        Write-Host "       $Path" -ForegroundColor DarkGray
    }
    catch {
        Write-Host "  [!] Echec pour $Client : $_" -ForegroundColor Yellow
    }
}

# 1. Claude Desktop
Update-McpConfig -Path (Join-Path $env:APPDATA "Claude\claude_desktop_config.json") -Client "Claude Desktop"

# 2. Antigravity / Gemini CLI
Update-McpConfig -Path (Join-Path $env:USERPROFILE ".gemini\config\mcp_config.json") -Client "Antigravity / Gemini"

# 3. Cursor Global
Update-McpConfig -Path (Join-Path $env:USERPROFILE ".cursor\mcp.json") -Client "Cursor Global"

# 4. Projet Local AetherCraft
Update-McpConfig -Path (Join-Path $projectPath "mcp.json") -Client "AetherCraft Local (mcp.json)"
Update-McpConfig -Path (Join-Path $projectPath ".cursor\mcp.json") -Client "AetherCraft Local (.cursor/mcp.json)"
Update-McpConfig -Path (Join-Path $projectPath ".vscode\mcp.json") -Client "AetherCraft Local (.vscode/mcp.json)"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " Configuration MCP terminee avec succes pour AetherCraft !" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
