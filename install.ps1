<#
One-click installer for the schwab-table Claude Skill (Windows PowerShell 5.1+ / PowerShell 7).

  irm https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.ps1 | iex

To pass options, save the script and run it:
  .\install.ps1 [-Dir <path>] [-Ref <tag-or-branch>] [-SkipDeps] [-Uninstall]
  -Dir        install into <path> (default: $env:CLAUDE_SKILLS_DIR or ~\.claude\skills, + \schwab-performance-table)
  -Ref        install a tag or branch instead of main, e.g. -Ref v0.4.0 (pin a version)
  -SkipDeps   do not create the Python venv / install Playwright + Chromium
  -Uninstall  delete the installed skill folder (only if its SKILL.md is named schwab-performance-table)
Re-running updates an existing install.
#>
param(
  [string]$Dir = "",
  [string]$Ref = "",
  [switch]$SkipDeps,
  [switch]$Uninstall
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RepoUrl   = if ($env:SCHWAB_TABLE_REPO) { $env:SCHWAB_TABLE_REPO } else { "https://github.com/imoneys10k/schwab-table" }
$SkillName = "schwab-performance-table"
$SkillsRoot = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $HOME ".claude\skills" }
$Target = if ($Dir) { $Dir } else { Join-Path $SkillsRoot $SkillName }

function Say($m) { Write-Host "==> $m" }
function Test-Cmd($n) { [bool](Get-Command $n -ErrorAction SilentlyContinue) }
function Invoke-Checked($exe, [string[]]$arguments) {
  # Windows PowerShell 5.1 turns native stderr output into terminating errors under
  # $ErrorActionPreference = "Stop", so relax it just for the native call.
  $saved = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try { & $exe @arguments; $code = $LASTEXITCODE } finally { $ErrorActionPreference = $saved }
  if ($code -ne 0) { throw "$exe $($arguments -join ' ') failed (exit code $code)" }
}

function Test-GitBranchCheckedOut($dir) {
  # `git symbolic-ref` exits non-zero on a detached HEAD; relax the error preference so native stderr cannot throw on Windows PowerShell 5.1.
  $saved = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try { & git -C $dir symbolic-ref -q HEAD *> $null; return ($LASTEXITCODE -eq 0) } finally { $ErrorActionPreference = $saved }
}

# 0. Uninstall ----------------------------------------------------------------
if ($Uninstall) {
  $skillMd = Join-Path $Target "SKILL.md"
  if ((Test-Path $skillMd) -and (Select-String -Path $skillMd -Pattern "^name:\s*schwab-performance-table" -Quiet)) {
    $helper = Join-Path $Target "install_earnings_skill.py"
    if (Test-Path $helper) {
      $cleanPy = Join-Path $Target ".venv\Scripts\python.exe"
      if (Test-Path $cleanPy) { Invoke-Checked $cleanPy @($helper, "--remove") }
      elseif (Test-Cmd python3) { Invoke-Checked python3 @($helper, "--remove") }
      elseif (Test-Cmd python) { Invoke-Checked python @($helper, "--remove") }
      elseif (Test-Cmd py) { Invoke-Checked py @("-3", $helper, "--remove") }
    }
    Remove-Item -Recurse -Force $Target
    Say "Removed $Target"
    return
  }
  throw "$Target is not an installed copy of this skill (no SKILL.md named $SkillName); nothing removed"
}

# 1. Fetch the files -----------------------------------------------------------
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
$isEmpty = (-not (Test-Path $Target)) -or (-not (Get-ChildItem -Force $Target | Select-Object -First 1))
if (Test-Path (Join-Path $Target ".git")) {
  if (-not (Test-Cmd git)) { throw "git is required to update $Target" }
  Say "Updating existing install in $Target"
  if ($Ref) {
    Invoke-Checked git @("-C", $Target, "fetch", "--depth", "1", "origin", $Ref)
    Invoke-Checked git @("-C", $Target, "checkout", "-q", "FETCH_HEAD")
  } elseif (Test-GitBranchCheckedOut $Target) {
    Invoke-Checked git @("-C", $Target, "pull", "--ff-only")
  } else {
    # Detached HEAD: an earlier -Ref left the install on a tag or commit, so `pull` would silently stay there.
    Say "This install is pinned to a tag or commit; moving to main"
    Invoke-Checked git @("-C", $Target, "fetch", "--depth", "1", "origin", "main")
    Invoke-Checked git @("-C", $Target, "checkout", "-q", "-B", "main", "FETCH_HEAD")
    Invoke-Checked git @("-C", $Target, "config", "branch.main.remote", "origin")
    Invoke-Checked git @("-C", $Target, "config", "branch.main.merge", "refs/heads/main")
  }
} elseif ((Test-Cmd git) -and $isEmpty) {
  Say "Cloning into $Target"
  $gitArgs = @("clone", "--depth", "1")
  if ($Ref) { $gitArgs += @("--branch", $Ref) }
  Invoke-Checked git ($gitArgs + @("$RepoUrl.git", $Target))
} else {
  Say "Downloading into $Target"
  $tmp = Join-Path ([IO.Path]::GetTempPath()) ("schwab-table-" + [Guid]::NewGuid())
  New-Item -ItemType Directory -Force -Path $tmp | Out-Null
  $zip = Join-Path $tmp "src.zip"
  $zipRef = if ($Ref) { $Ref } else { "main" }
  Invoke-WebRequest -UseBasicParsing "$RepoUrl/archive/$zipRef.zip" -OutFile $zip
  Expand-Archive -Path $zip -DestinationPath $tmp -Force
  New-Item -ItemType Directory -Force -Path $Target | Out-Null
  $inner = Get-ChildItem -Directory $tmp | Where-Object { $_.Name -like "schwab-table-*" } | Select-Object -First 1
  Copy-Item -Path (Join-Path $inner.FullName "*") -Destination $Target -Recurse -Force
  Remove-Item -Recurse -Force $tmp
}

# 2. Python dependencies (only needed to render tables) -------------------------
if ($SkipDeps) {
  Say "Skipping Python dependencies (-SkipDeps)"
} else {
  $candidates = @(
    @{ Exe = "py";      Args = @("-3") },
    @{ Exe = "python";  Args = @() },
    @{ Exe = "python3"; Args = @() }
  )
  $pyExe = $null
  $pyArgs = @()
  foreach ($c in $candidates) {
    if (-not (Test-Cmd $c.Exe)) { continue }
    try {
      Invoke-Checked $c.Exe (@($c.Args) + @("-c", "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)")) | Out-Null
      $pyExe = $c.Exe
      $pyArgs = @($c.Args)
      break
    } catch { }
  }
  if (-not $pyExe) { throw "Python 3.9+ not found. Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), or re-run with -SkipDeps." }

  Say "Creating virtual environment ($Target\.venv)"
  Invoke-Checked $pyExe (@($pyArgs) + @("-m", "venv", (Join-Path $Target ".venv")))
  $vpy = Join-Path $Target ".venv\Scripts\python.exe"
  if (-not (Test-Path $vpy)) { $vpy = Join-Path $Target ".venv/bin/python" }  # PowerShell on Linux/macOS
  Say "Installing Playwright"
  Invoke-Checked $vpy @("-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", (Join-Path $Target "requirements.txt"))
  Say "Installing Chromium for Playwright (about 100 MB)"
  Invoke-Checked $vpy @("-m", "playwright", "install", "chromium")

  # 3. Smoke test ----------------------------------------------------------------
  Say "Smoke test: rendering four table styles and an example chart"
  $smoke = Join-Path ([IO.Path]::GetTempPath()) ("schwab-smoke-" + [Guid]::NewGuid())
  New-Item -ItemType Directory -Force -Path $smoke | Out-Null
  $ok = $true
  try {
    Invoke-Checked $vpy @((Join-Path $Target "render_table.py"), (Join-Path $Target "examples\neural9_spec.json"), (Join-Path $smoke "table")) | Out-Null
    Invoke-Checked $vpy @((Join-Path $Target "render_chart.py"), (Join-Path $Target "examples\chart_lines_spec.json"), (Join-Path $smoke "chart")) | Out-Null
    foreach ($reportStyle in @("morgan", "blackstone", "ibkr")) {
      Invoke-Checked $vpy @((Join-Path $Target "render_table.py"), (Join-Path $Target ("examples\{0}_spec.json" -f $reportStyle)), (Join-Path $smoke $reportStyle)) | Out-Null
    }
    Invoke-Checked $vpy @((Join-Path $Target "quarterly_earnings.py"), "AAPL", "--period", "FY2025Q3", "--facts", (Join-Path $Target "examples\earnings\aapl_2025q3_facts.json"), "--analysis", (Join-Path $Target "examples\earnings\aapl_2025q3_analysis.json"), "-o", (Join-Path $smoke "earnings")) | Out-Null
  } catch { $ok = $false; Write-Host $_.Exception.Message }
  Remove-Item -Recurse -Force $smoke -ErrorAction SilentlyContinue
  if (-not $ok) { throw "smoke test failed" }
  Say "Render OK (Schwab, Morgan, Blackstone, IBKR, HSBC earnings, chart)"
}

$helper = Join-Path $Target "install_earnings_skill.py"
if (Test-Path $helper) {
  Say "Registering quarterly-earnings-review beside the main skill"
  if ($vpy -and (Test-Path $vpy)) { Invoke-Checked $vpy @($helper) }
  elseif (Test-Cmd python3) { Invoke-Checked python3 @($helper) }
  elseif (Test-Cmd python) { Invoke-Checked python @($helper) }
  elseif (Test-Cmd py) { Invoke-Checked py @("-3", $helper) }
  else { Write-Host "Register the earnings skill after installing Python: python install_earnings_skill.py" }
}

Say "Installed to $Target"
Write-Host "Restart Claude (or start a new session) so it picks up the skill."
