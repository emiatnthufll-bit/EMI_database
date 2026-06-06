$ErrorActionPreference = "Stop"

$root = Resolve-Path "${PSScriptRoot}\.."

function Require-Command($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "$name is not installed or not in PATH"
  }
}

function Run-Command($name, $cmdArgs) {
  & $name @cmdArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $name $($cmdArgs -join ' ')"
  }
}

function Get-ComposeCommand() {
  $compose = @("docker", "compose")
  try {
    & docker compose version | Out-Null
    return $compose
  } catch {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
      return @("docker-compose")
    }
    throw "Docker Compose is not available (docker compose or docker-compose)"
  }
}

function Get-PythonCommand($root) {
  $candidates = @(
    (Join-Path $root ".venv\Scripts\python.exe"),
    (Join-Path (Split-Path $root -Parent) ".venv\Scripts\python.exe")
  )
  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      return $candidate
    }
  }
  return "python"
}

function Read-EnvFile($path) {
  $envMap = @{}
  if (-not (Test-Path $path)) {
    return $envMap
  }
  Get-Content $path | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) {
      return
    }
    $pair = $line.Split("=", 2)
    if ($pair.Length -eq 2) {
      $envMap[$pair[0].Trim()] = $pair[1].Trim()
    }
  }
  return $envMap
}

function Read-EnvFromComposeFile($path) {
  $envMap = @{}
  if (-not (Test-Path $path)) {
    return $envMap
  }
  $lines = Get-Content $path
  $inDb = $false
  foreach ($line in $lines) {
    $text = $line.Trim()
    if ($text -like "db:*") {
      $inDb = $true
      continue
    }
    if ($inDb -and $text -like "*:") {
      if ($text -notlike "environment:*") {
        $inDb = $false
      }
    }
    if ($inDb -and $text -match "^MYSQL_[A-Z_]+\s*:\s*(.+)$") {
      $parts = $text.Split(":", 2)
      $key = $parts[0].Trim()
      $value = $parts[1].Trim()
      $envMap[$key] = $value
    }
  }
  return $envMap
}

function Read-EnvFromContainer($composeCmd, $varName) {
  $oldErr = $ErrorActionPreference
  $ErrorActionPreference = "SilentlyContinue"
  $value = & docker exec emi_mysql sh -c "printenv $varName" 2>$null | Select-Object -First 1
  $ErrorActionPreference = $oldErr
  if ($LASTEXITCODE -ne 0) {
    return $null
  }
  $text = ($value | Out-String).Trim()
  if ($text -like "time=*attribute `version` is obsolete*") {
    return $null
  }
  return $text
}

Require-Command docker
$pythonCmd = Get-PythonCommand $root
Require-Command $pythonCmd

$envFile = Join-Path $root ".env"
$envMap = Read-EnvFile $envFile
if ($envMap.ContainsKey("MYSQL_USER")) { $env:MYSQL_USER = $envMap["MYSQL_USER"] }
if ($envMap.ContainsKey("MYSQL_PASSWORD")) { $env:MYSQL_PASSWORD = $envMap["MYSQL_PASSWORD"] }
if ($envMap.ContainsKey("MYSQL_DATABASE")) { $env:MYSQL_DATABASE = $envMap["MYSQL_DATABASE"] }
if ($envMap.ContainsKey("MYSQL_ROOT_PASSWORD")) { $env:MYSQL_ROOT_PASSWORD = $envMap["MYSQL_ROOT_PASSWORD"] }

$composeEnv = Read-EnvFromComposeFile (Join-Path $root "docker-compose.yml")
if (-not $env:MYSQL_USER -and $composeEnv.ContainsKey("MYSQL_USER")) { $env:MYSQL_USER = $composeEnv["MYSQL_USER"] }
if (-not $env:MYSQL_PASSWORD -and $composeEnv.ContainsKey("MYSQL_PASSWORD")) { $env:MYSQL_PASSWORD = $composeEnv["MYSQL_PASSWORD"] }
if (-not $env:MYSQL_DATABASE -and $composeEnv.ContainsKey("MYSQL_DATABASE")) { $env:MYSQL_DATABASE = $composeEnv["MYSQL_DATABASE"] }
if (-not $env:MYSQL_ROOT_PASSWORD -and $composeEnv.ContainsKey("MYSQL_ROOT_PASSWORD")) { $env:MYSQL_ROOT_PASSWORD = $composeEnv["MYSQL_ROOT_PASSWORD"] }

Write-Host "[1/8] Starting Docker services..."
Set-Location $root
$composeCmd = Get-ComposeCommand
Run-Command $composeCmd[0] ($composeCmd[1..($composeCmd.Length - 1)] + @("up", "-d"))

Write-Host "[2/8] Waiting for API health check..."
$healthOk = $false
for ($i = 1; $i -le 30; $i++) {
  try {
    $resp = & curl.exe -s http://localhost:8000/health | Out-String
    if ($resp -match '"ok"') {
      $healthOk = $true
      break
    }
  } catch {
    # keep retrying
  }
  Write-Host "Waiting for API... ($i/30)"
  Start-Sleep -Seconds 2
}
if (-not $healthOk) {
  throw "API health check failed"
}

Write-Host "[3/8] Running backend tests..."
Set-Location (Join-Path $root "backend")
try {
  Run-Command $pythonCmd @("-m", "pytest", "--version")
} catch {
  throw "pytest is not installed. Run: python -m pip install -r backend/requirements.txt"
}
Run-Command $pythonCmd @("-m", "pytest")

Set-Location $root

Write-Host "[4/8] Running smoke test..."
$health = & curl.exe -s http://localhost:8000/health | Out-String
if ($health -notmatch '"ok"') {
  throw "Health check failed: $health"
}

$webStatus = & curl.exe -s -I http://localhost:5173 | Select-Object -First 1
if ($webStatus -notmatch "200") {
  throw "Frontend not reachable"
}

$docsStatus = & curl.exe -s -I http://localhost:8000/docs | Select-Object -First 1
if ($docsStatus -notmatch "200") {
  throw "API docs not reachable"
}

if (-not $env:MYSQL_USER) { $env:MYSQL_USER = "emi" }
if (-not $env:MYSQL_PASSWORD) { $env:MYSQL_PASSWORD = "emipass" }
$mysqlPasswordArg = "-p{0}" -f $env:MYSQL_PASSWORD
Run-Command docker @("exec", "emi_mysql", "mysqladmin", "ping", "-u$env:MYSQL_USER", $mysqlPasswordArg)

Write-Host "[5/8] Running backup..."
if (-not $env:MYSQL_USER) { $env:MYSQL_USER = Read-EnvFromContainer $composeCmd "MYSQL_USER" }
if (-not $env:MYSQL_PASSWORD) { $env:MYSQL_PASSWORD = Read-EnvFromContainer $composeCmd "MYSQL_PASSWORD" }
if (-not $env:MYSQL_DATABASE) { $env:MYSQL_DATABASE = Read-EnvFromContainer $composeCmd "MYSQL_DATABASE" }

if (-not $env:MYSQL_USER -or -not $env:MYSQL_PASSWORD -or -not $env:MYSQL_DATABASE) {
  throw "MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE must be set (env, .env, or db container env)"
}

$backupDir = Join-Path $root "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$backupPath = Join-Path $backupDir "emi_db_${timestamp}.sql.gz"

$dumpUser = $env:MYSQL_USER
$dumpPassword = $env:MYSQL_PASSWORD
$dumpPasswordArg = "-p{0}" -f $dumpPassword

if (-not $dumpUser -or $dumpUser -eq "`$dumpUser") {
  throw "Invalid MySQL user for backup"
}

$dump = & docker exec emi_mysql mysqldump --no-tablespaces -u $dumpUser $dumpPasswordArg $env:MYSQL_DATABASE
if ($LASTEXITCODE -ne 0) {
  throw "mysqldump failed"
}

if (-not $dump -or ($dump | Out-String).Trim().Length -lt 10) {
  throw "mysqldump produced empty output"
}

$dumpText = ($dump | Out-String)
if ($dumpText -notmatch "(?s)CREATE TABLE\s+.*`?papers`?") {
  throw "Backup does not include papers table schema"
}

$bytes = [System.Text.Encoding]::UTF8.GetBytes($dumpText)
$fileStream = [System.IO.File]::Create($backupPath)
$gzip = New-Object System.IO.Compression.GZipStream($fileStream, [System.IO.Compression.CompressionMode]::Compress)
$gzip.Write($bytes, 0, $bytes.Length)
$gzip.Dispose()
$fileStream.Dispose()

Write-Host "[6/8] Running backup restore validation..."
if (-not $env:MYSQL_ROOT_PASSWORD) {
  $env:MYSQL_ROOT_PASSWORD = Read-EnvFromContainer $composeCmd "MYSQL_ROOT_PASSWORD"
}
if (-not $env:MYSQL_ROOT_PASSWORD) {
  $composeEnv = Read-EnvFromComposeFile (Join-Path $root "docker-compose.yml")
  if ($composeEnv.ContainsKey("MYSQL_ROOT_PASSWORD")) { $env:MYSQL_ROOT_PASSWORD = $composeEnv["MYSQL_ROOT_PASSWORD"] }
}
if (-not $env:MYSQL_ROOT_PASSWORD) {
  throw "MYSQL_ROOT_PASSWORD must be set (env, .env, or db container env)"
}

$latestBackup = Get-ChildItem -Path $backupDir -Filter "*.sql.gz" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latestBackup) {
  throw "No backup file found in backups"
}

$restoreDb = "emi_restore_test"
$dropCreateSql = "DROP DATABASE IF EXISTS {0}; CREATE DATABASE {0}" -f $restoreDb
$dropOnlySql = "DROP DATABASE IF EXISTS {0}" -f $restoreDb
$countSql = "USE {0}; SELECT COUNT(*) FROM papers;" -f $restoreDb
try {
  $rootPasswordArg = "-p{0}" -f $env:MYSQL_ROOT_PASSWORD
  Run-Command docker @("exec", "emi_mysql", "mysql", "-uroot", $rootPasswordArg, "-e", $dropCreateSql)

  $fs = [System.IO.File]::OpenRead($latestBackup.FullName)
  $gzipIn = New-Object System.IO.Compression.GZipStream($fs, [System.IO.Compression.CompressionMode]::Decompress)
  $reader = New-Object System.IO.StreamReader($gzipIn)
  $sql = $reader.ReadToEnd()
  $reader.Close()
  $gzipIn.Close()
  $fs.Close()

  $filtered = $sql -split "\r?\n" | Where-Object {
    $_ -notmatch "^CREATE DATABASE" -and $_ -notmatch "^USE "
  }
  ($filtered -join "`n") | & docker exec -i emi_mysql mysql -uroot $rootPasswordArg $restoreDb
  if ($LASTEXITCODE -ne 0) {
    throw "Restore import failed"
  }

  Run-Command docker @("exec", "emi_mysql", "mysql", "-uroot", $rootPasswordArg, "-N", "-e", $countSql)
} finally {
  Run-Command docker @("exec", "emi_mysql", "mysql", "-uroot", $rootPasswordArg, "-e", $dropOnlySql)
}

Write-Host "[7/8] Running production config check..."
Run-Command $pythonCmd @("scripts/check_prod_config.py")

Write-Host "[8/8] All checks passed"
