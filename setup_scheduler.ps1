# Create and manage Windows Task Scheduler for ThreatFeedAggregator
# Run with administrator privileges

param(
    [string]$Action = "create",
    [int]$Hour = 8,
    [int]$Minute = 0
)

$TaskName = "ThreatFeedAggregator"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonScript = Join-Path $ScriptDir "main.py"
$PythonExe = "py"
$Arguments = "$PythonScript --fetch-once"

# Check admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Requires administrator privileges!" -ForegroundColor Red
    exit 1
}

if ($Action -eq "create") {
    Write-Host "[INFO] Creating scheduled task: $TaskName" -ForegroundColor Cyan
    
    # Remove old task if it exists
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    } catch {}
    
    # Create trigger with formatted time
    $TimeStr = "{0:D2}:{1:D2}" -f $Hour, $Minute
    $Trigger = New-ScheduledTaskTrigger -Daily -At $TimeStr

    # Create action
    $ActionObj = New-ScheduledTaskAction -Execute $PythonExe -Argument $Arguments -WorkingDirectory $ScriptDir

    # Settings
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable

    # Register task
    Register-ScheduledTask -TaskName $TaskName -Trigger $Trigger -Action $ActionObj -Settings $Settings -Description "Threat Feed Aggregator - Daily IOC fetch" -RunLevel Highest | Out-Null
    
    Write-Host "[OK] Task created: $TaskName" -ForegroundColor Green
    Write-Host "     Schedule: Daily at $TimeStr" -ForegroundColor Green
    Write-Host "     Command: $PythonExe $Arguments" -ForegroundColor Green
}
elseif ($Action -eq "delete") {
    Write-Host "[INFO] Deleting task: $TaskName" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[OK] Task deleted" -ForegroundColor Green
}
elseif ($Action -eq "run") {
    Write-Host "[INFO] Running task now..." -ForegroundColor Cyan
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "[OK] Task started" -ForegroundColor Green
}
elseif ($Action -eq "status") {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "Task: $TaskName" -ForegroundColor Cyan
        Write-Host "Status: $($task.State)" -ForegroundColor Green
        $lastRun = $task | Get-ScheduledTaskInfo
        Write-Host "Last Run: $($lastRun.LastRunTime)" -ForegroundColor Green
        Write-Host "Next Run: $($lastRun.NextRunTime)" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Task not found: $TaskName" -ForegroundColor Yellow
    }
}
else {
    Write-Host "[ERROR] Unknown action: $Action" -ForegroundColor Red
    Write-Host "Valid actions: create, delete, run, status" -ForegroundColor Yellow
}
