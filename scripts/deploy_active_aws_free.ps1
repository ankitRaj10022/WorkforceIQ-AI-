param(
    [string]$AwsRegion = "us-east-1",
    [string]$InstanceId = "i-0064b45ececace888",
    [string]$EcrRepositoryUrl = "187528943333.dkr.ecr.us-east-1.amazonaws.com/workforceiq-free",
    [string]$HealthUrl = "http://ec2-44-211-148-129.compute-1.amazonaws.com/api/health/ready",
    [switch]$SkipHealthCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-ToWslPath([string]$Path) {
    $resolved = (Resolve-Path $Path).Path
    $drive = $resolved.Substring(0, 1).ToLowerInvariant()
    $suffix = $resolved.Substring(2).Replace("\", "/")
    return "/mnt/$drive$suffix"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$wslRepoRoot = Convert-ToWslPath $repoRoot
$registry = $EcrRepositoryUrl.Split("/")[0]
$image = "${EcrRepositoryUrl}:latest"
$passwordFile = Join-Path $repoRoot ".tmp-ecr-password.txt"
$ssmCommandsFile = Join-Path $repoRoot ".tmp-ssm-commands.json"

function Remove-TempFile([string]$Path) {
    if (Test-Path $Path) {
        Remove-Item $Path -Force
    }
}

function Assert-LastExitCode([string]$StepName) {
    if ($LASTEXITCODE -ne 0) {
        throw "$StepName failed with exit code $LASTEXITCODE."
    }
}

try {
    Write-Host "Logging into Amazon ECR..."
    aws ecr get-login-password --region $AwsRegion | Set-Content -NoNewline $passwordFile

    $wslPasswordFile = Convert-ToWslPath $passwordFile
    $buildCommand = @"
set -euo pipefail
cat '$wslPasswordFile' | docker login --username AWS --password-stdin $registry
cd '$wslRepoRoot'
docker build -t $image .
docker push $image
"@

    Write-Host "Building and pushing the latest app image..."
    & wsl -e bash -lc $buildCommand
    Assert-LastExitCode "WSL Docker build and push"

    $commands = @{
        commands = @(
            "set -euo pipefail",
            "cd /opt/workforceiq",
            "aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin $registry",
            "docker image prune -af || true",
            "docker compose -f docker-compose.free.yml --env-file .env.free pull",
            "docker compose -f docker-compose.free.yml --env-file .env.free up -d",
            "docker compose -f docker-compose.free.yml --env-file .env.free ps"
        )
    } | ConvertTo-Json -Depth 3

    $commands | Set-Content $ssmCommandsFile

    Write-Host "Restarting the EC2 stack through SSM..."
    $commandId = aws ssm send-command `
        --region $AwsRegion `
        --instance-ids $InstanceId `
        --document-name "AWS-RunShellScript" `
        --comment "Deploy WorkforceIQ containers" `
        --parameters "file://$ssmCommandsFile" `
        --query "Command.CommandId" `
        --output text
    Assert-LastExitCode "SSM send-command"
    Write-Host "SSM command id: $commandId"

    aws ssm wait command-executed `
        --region $AwsRegion `
        --command-id $commandId `
        --instance-id $InstanceId
    if ($LASTEXITCODE -ne 0) {
        try {
            $failedInvocation = aws ssm get-command-invocation `
                --region $AwsRegion `
                --command-id $commandId `
                --instance-id $InstanceId | ConvertFrom-Json
            if ($failedInvocation.StandardOutputContent) {
                Write-Host ""
                Write-Host "Remote stdout:"
                Write-Host $failedInvocation.StandardOutputContent.TrimEnd()
            }
            if ($failedInvocation.StandardErrorContent) {
                Write-Host ""
                Write-Host "Remote stderr:"
                Write-Host $failedInvocation.StandardErrorContent.TrimEnd()
            }
            throw "SSM command wait failed. Remote status: $($failedInvocation.StatusDetails)"
        } catch {
            throw "SSM command wait failed with exit code $LASTEXITCODE. Command id: $commandId"
        }
    }

    $invocation = aws ssm get-command-invocation `
        --region $AwsRegion `
        --command-id $commandId `
        --instance-id $InstanceId | ConvertFrom-Json
    Assert-LastExitCode "SSM command inspection"

    Write-Host ""
    Write-Host "Remote deploy status: $($invocation.Status)"
    if ($invocation.Status -ne "Success") {
        throw "Remote deploy did not finish successfully."
    }
    if ($invocation.StandardOutputContent) {
        Write-Host $invocation.StandardOutputContent.TrimEnd()
    }
    if ($invocation.StandardErrorContent) {
        Write-Host ""
        Write-Host "Remote stderr:"
        Write-Host $invocation.StandardErrorContent.TrimEnd()
    }

    if (-not $SkipHealthCheck -and $HealthUrl) {
        Write-Host ""
        Write-Host "Checking public health endpoint..."
        $healthy = $false
        for ($attempt = 1; $attempt -le 20; $attempt++) {
            try {
                $response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 20
                if ($response.status -notin @("ok", "ready")) {
                    throw "Unexpected health status: $($response.status)"
                }
                $response | ConvertTo-Json -Depth 5
                $healthy = $true
                break
            } catch {
                Start-Sleep -Seconds 15
            }
        }

        if (-not $healthy) {
            throw "Deployment finished but the public health endpoint did not respond in time: $HealthUrl"
        }
    }
} finally {
    Remove-TempFile $passwordFile
    Remove-TempFile $ssmCommandsFile
}
