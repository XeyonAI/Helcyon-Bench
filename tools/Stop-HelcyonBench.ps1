param(
    [string]$Workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
)

$resolvedWorkspace = (Resolve-Path -LiteralPath $Workspace).Path
$escapedWorkspace = [regex]::Escape($resolvedWorkspace)
$appPattern = [regex]::Escape((Join-Path $resolvedWorkspace "app.py"))

Get-CimInstance Win32_Process |
    Where-Object {
        $_.ProcessId -ne $PID -and
        $_.CommandLine -and
        (
            $_.CommandLine -match $appPattern -or
            ($_.CommandLine -match "streamlit" -and $_.CommandLine -match $escapedWorkspace)
        )
    } |
    ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
            Write-Host "Stopped Helcyon-Bench process $($_.ProcessId)"
        } catch {
            Write-Warning "Could not stop process $($_.ProcessId): $($_.Exception.Message)"
        }
    }
