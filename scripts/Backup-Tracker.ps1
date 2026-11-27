param(
    [string]$BackupDirectory = (Join-Path $env:USERPROFILE 'Documents\ScholarshipTrackerBackups')
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $root 'compose.yaml'
$composeArgs = @('compose', '--project-name', 'scholarship-tracker-restart', '--file', $composeFile)

function Invoke-Docker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed with exit code $LASTEXITCODE." }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is not installed or is not on PATH.' }
if (-not (Test-Path -LiteralPath $BackupDirectory)) { New-Item -ItemType Directory -Path $BackupDirectory | Out-Null }
$directory = (Resolve-Path -LiteralPath $BackupDirectory).Path
if (-not (Test-Path -LiteralPath $directory -PathType Container)) { throw 'BackupDirectory must be a directory.' }
$tag = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N')
$backupFile = Join-Path $directory "scholarship-tracker-$tag.dump"
$containerFile = "/tmp/scholarship-tracker-$tag.dump"
if (Test-Path -LiteralPath $backupFile) { throw 'The backup path already exists; no file was overwritten.' }

try {
    Invoke-Docker ($composeArgs + @('exec','-T','db','pg_dump','-U','tracker_local','-d','scholarship_tracker_restart','--format=custom','--no-owner','--no-acl','-f',$containerFile))
    Invoke-Docker ($composeArgs + @('exec','-T','db','pg_restore','--list',$containerFile)) | Out-Null
    Invoke-Docker ($composeArgs + @('cp',"db:$containerFile",$backupFile))
    if (-not (Test-Path -LiteralPath $backupFile -PathType Leaf) -or (Get-Item -LiteralPath $backupFile).Length -eq 0) { throw 'The copied backup is missing or empty.' }
    Write-Host "Backup created: $backupFile"
    Write-Host 'Keep this private file outside Git. Test recovery before relying on it.'
} finally {
    & docker @composeArgs exec -T db rm -f -- $containerFile
    if ($LASTEXITCODE -ne 0) { Write-Warning "Could not remove temporary container file $containerFile." }
}
