[CmdletBinding()]
param(
    [string]$AmplifyAppId,
    [string]$BranchName = "main",
    [switch]$WriteLocalEnv,
    [switch]$StartReleaseJob
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $repoRoot "apps\web"

function Get-WslPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowsPath
    )

    $resolved = (Resolve-Path -LiteralPath $WindowsPath).ProviderPath
    $wslPath = wsl -e wslpath -a $resolved
    return ($wslPath | Out-String).Trim()
}

function Get-ManagedFrontendEnv {
    $wslRepoRoot = Get-WslPath -WindowsPath $repoRoot
    $command = @"
cd '$wslRepoRoot' && docker run --rm -v "`$PWD/infra/aws:/workspace" -v "/mnt/c/Users/danny/.aws:/root/.aws:ro" -w /workspace/terraform hashicorp/terraform:1.9.8 output -json frontend_env
"@

    $json = wsl -e sh -lc $command
    if (-not $json) {
        throw "Unable to read frontend_env from Terraform output."
    }

    return $json | ConvertFrom-Json
}

function ConvertTo-StringMap {
    param(
        [Parameter(Mandatory = $true)]
        [object]$InputObject
    )

    $map = [ordered]@{}
    foreach ($property in $InputObject.PSObject.Properties) {
        $map[$property.Name] = [string]$property.Value
    }

    return $map
}

$envMap = ConvertTo-StringMap -InputObject (Get-ManagedFrontendEnv)

if ($WriteLocalEnv) {
    $envFile = Join-Path $frontendDir ".env.local"
    $lines = foreach ($entry in $envMap.GetEnumerator()) {
        "{0}={1}" -f $entry.Key, $entry.Value
    }
    Set-Content -LiteralPath $envFile -Value $lines
    Write-Host "Wrote $envFile"
}

if ($AmplifyAppId) {
    $payload = @{
        appId = $AmplifyAppId
        environmentVariables = $envMap
    }

    $tempFile = New-TemporaryFile
    try {
        $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $tempFile
        aws amplify update-app --cli-input-json ("file://{0}" -f $tempFile) | Out-Null
        Write-Host "Updated Amplify app environment variables for $AmplifyAppId"
    }
    finally {
        if (Test-Path -LiteralPath $tempFile) {
            Remove-Item -LiteralPath $tempFile -Force
        }
    }

    if ($StartReleaseJob) {
        aws amplify start-job --app-id $AmplifyAppId --branch-name $BranchName --job-type RELEASE | Out-Null
        Write-Host "Started Amplify release job for branch $BranchName"
    }
}

if (-not $WriteLocalEnv -and -not $AmplifyAppId) {
    $envMap.GetEnumerator() | ForEach-Object {
        "{0}={1}" -f $_.Key, $_.Value
    }
}
