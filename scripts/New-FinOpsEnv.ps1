param([string]$Path = ".env.finops")

$ErrorActionPreference = "Stop"

function New-Token([int]$Bytes = 32) {
    $buffer = [byte[]]::new($Bytes)
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($buffer)
    }
    finally {
        $generator.Dispose()
    }
    return ([BitConverter]::ToString($buffer) -replace "-", "").ToLowerInvariant()
}

if (Test-Path -LiteralPath $Path) {
    throw "$Path already exists; remove it explicitly before generating new persisted credentials."
}

$values = @(
    "FINOPS_POSTGRES_PASSWORD=$(New-Token 24)"
    "FINOPS_CLICKHOUSE_PASSWORD=$(New-Token 24)"
    "FINOPS_REDIS_PASSWORD=$(New-Token 24)"
    "FINOPS_MINIO_USER=finops-local"
    "FINOPS_MINIO_PASSWORD=$(New-Token 24)"
    "FINOPS_SALT=$(New-Token 32)"
    "FINOPS_ENCRYPTION_KEY=$(New-Token 32)"
    "FINOPS_NEXTAUTH_SECRET=$(New-Token 32)"
    "FINOPS_LANGFUSE_PUBLIC_KEY=pk-lf-$(New-Token 16)"
    "FINOPS_LANGFUSE_SECRET_KEY=sk-lf-$(New-Token 24)"
    "FINOPS_ADMIN_EMAIL=finops-local@example.invalid"
    "FINOPS_ADMIN_PASSWORD=$(New-Token 24)"
)
[IO.File]::WriteAllLines((Join-Path (Get-Location) $Path), $values)
Write-Host "Created $Path. Keep this ignored file private; seeded credentials do not rotate existing Langfuse data."
