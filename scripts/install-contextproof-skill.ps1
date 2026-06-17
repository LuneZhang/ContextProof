param(
    [ValidateSet("agents", "codex", "claude", "opencode", "project-claude", "project-opencode", "project-agents")]
    [string]$Scope = "agents"
)

$RepoDir = Split-Path -Parent $PSScriptRoot
$Source = Join-Path $RepoDir "skill\context-proof"

switch ($Scope) {
    "agents" { $Dest = Join-Path $HOME ".agents\skills\context-proof" }
    "codex" { $Dest = Join-Path $HOME ".codex\skills\context-proof" }
    "claude" { $Dest = Join-Path $HOME ".claude\skills\context-proof" }
    "opencode" { $Dest = Join-Path $HOME ".config\opencode\skills\context-proof" }
    "project-claude" { $Dest = ".claude\skills\context-proof" }
    "project-opencode" { $Dest = ".opencode\skills\context-proof" }
    "project-agents" { $Dest = ".agents\skills\context-proof" }
}

New-Item -ItemType Directory -Force (Split-Path -Parent $Dest) | Out-Null
if (Test-Path $Dest) {
    Remove-Item -Recurse -Force $Dest
}
Copy-Item -Recurse -Force $Source $Dest
Write-Output "Installed context-proof skill to $Dest"
