param(
    [Parameter(Mandatory=$true)][string]$BackupFile,
    [Parameter(Mandatory=$true)][string]$RecoveryDatabase
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $root 'compose.yaml'
$composeArgs = @('compose', '--project-name', 'scholarship-tracker-restart', '--file', $composeFile)

function Invoke-Docker([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed with exit code $LASTEXITCODE." }
}

if ($RecoveryDatabase -cnotmatch '^scholarship_tracker_restore_[a-z0-9_]{1,32}$') {
    throw 'RecoveryDatabase must start with scholarship_tracker_restore_ and contain only lowercase letters, digits and underscores after the prefix (maximum 32 characters).'
}
if (-not (Test-Path -LiteralPath $BackupFile -PathType Leaf)) { throw 'Backup file not found.' }
$source = (Resolve-Path -LiteralPath $BackupFile).Path
$tag = [guid]::NewGuid().ToString('N')
$containerFile = "/tmp/scholarship-restore-$tag.dump"
$created = $false
try {
    Invoke-Docker ($composeArgs + @('cp',$source,"db:$containerFile"))
    Invoke-Docker ($composeArgs + @('exec','-T','db','pg_restore','--list',$containerFile)) | Out-Null
    # createdb refuses an existing name. Never drop or overwrite a database.
    Invoke-Docker ($composeArgs + @('exec','-T','db','createdb','-U','tracker_local',$RecoveryDatabase))
    $created = $true
    Invoke-Docker ($composeArgs + @('exec','-T','db','pg_restore','-U','tracker_local','--dbname',$RecoveryDatabase,'--no-owner','--no-acl','--single-transaction','--exit-on-error',$containerFile))
    Write-Host "Restored into new database: $RecoveryDatabase"
    Write-Host 'Verify its schema revision and records before using it.'
} catch {
    if ($created) { Write-Warning "Restore did not complete. The new database $RecoveryDatabase was retained; no existing database was overwritten." }
    throw
} finally {
    & docker @composeArgs exec -T db rm -f -- $containerFile
    if ($LASTEXITCODE -ne 0) { Write-Warning "Could not remove temporary container file $containerFile." }
}
