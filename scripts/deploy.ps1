<#
.SYNOPSIS
    One-command deployment of Magentic Marketplace to Azure Container Apps.

.DESCRIPTION
    This script validates prerequisites, prompts for required configuration,
    and deploys the entire stack (PostgreSQL, Container App, Managed Identity)
    to Azure using the included Bicep template. Uses Azure OpenAI with
    Entra ID (Managed Identity) authentication — no API keys needed.

.PARAMETER ResourceGroup
    Azure resource group name. Created if it doesn't exist.

.PARAMETER Location
    Azure region (default: swedencentral).

.PARAMETER AzureOpenAiEndpoint
    Your Azure OpenAI endpoint URL.

.PARAMETER LlmModel
    LLM model/deployment name (default: gpt-5.3-chat).

.PARAMETER PostgresPassword
    PostgreSQL admin password. Generated if not provided.

.EXAMPLE
    .\scripts\deploy.ps1 -AzureOpenAiEndpoint "https://my-resource.openai.azure.com/"
#>

param(
    [string]$ResourceGroup = "magentic-marketplace-rg",
    [string]$Location = "swedencentral",
    [string]$AzureOpenAiEndpoint = "",
    [string]$LlmModel = "",
    [string]$PostgresPassword = "",
    [string]$ContainerImage = "",
    [string]$GhcrUsername = "",
    [string]$GhcrToken = ""
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Magentic Marketplace — Azure Deployment ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check prerequisites ──────────────────────────────────────
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

# Azure CLI
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Azure CLI (az) is not installed." -ForegroundColor Red
    Write-Host "  Install: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
}

# Logged in?
$account = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Not logged in to Azure CLI. Run 'az login' first." -ForegroundColor Red
    exit 1
}
$subscription = ($account | ConvertFrom-Json).name
$subscriptionId = ($account | ConvertFrom-Json).id
Write-Host "  Azure CLI: OK" -ForegroundColor Green
Write-Host "  Subscription: $subscription ($subscriptionId)"

# Bicep template exists?
$bicepPath = Join-Path $PSScriptRoot "..\infra\main.bicep"
if (-not (Test-Path $bicepPath)) {
    Write-Host "ERROR: infra/main.bicep not found. Run this script from the repository root." -ForegroundColor Red
    exit 1
}
Write-Host "  Bicep template: OK" -ForegroundColor Green

# ── 2. Collect configuration ────────────────────────────────────
Write-Host ""
Write-Host "[2/5] Configuring deployment..." -ForegroundColor Yellow

# Azure OpenAI endpoint
if (-not $AzureOpenAiEndpoint) {
    $AzureOpenAiEndpoint = Read-Host "  Azure OpenAI endpoint (e.g. https://my-resource.openai.azure.com/)"
    if (-not $AzureOpenAiEndpoint) {
        Write-Host "ERROR: Azure OpenAI endpoint is required." -ForegroundColor Red
        exit 1
    }
}

# Model name
if (-not $LlmModel) {
    $LlmModel = Read-Host "  Model/deployment name (default: gpt-5.3-chat)"
    if (-not $LlmModel) { $LlmModel = "gpt-5.3-chat" }
}

# PostgreSQL password
if (-not $PostgresPassword) {
    # Generate a random alphanumeric password
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $PostgresPassword = -join ((1..24) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    Write-Host "  PostgreSQL password: (auto-generated)"
}

# Summary
Write-Host ""
Write-Host "  Configuration summary:" -ForegroundColor Cyan
Write-Host "    Resource group:  $ResourceGroup"
Write-Host "    Location:        $Location"
Write-Host "    Endpoint:        $AzureOpenAiEndpoint"
Write-Host "    Model:           $LlmModel"
if ($ContainerImage) {
    Write-Host "    Container image: $ContainerImage"
}
else {
    Write-Host "    Container image: (default public image)"
}
Write-Host ""

$confirm = Read-Host "  Proceed with deployment? (Y/n)"
if ($confirm -and $confirm -notin @("y", "Y", "yes", "Yes", "YES", "")) {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

# ── 3. Create resource group ────────────────────────────────────
Write-Host ""
Write-Host "[3/5] Creating resource group '$ResourceGroup'..." -ForegroundColor Yellow

az group create --name $ResourceGroup --location $Location -o none 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create resource group." -ForegroundColor Red
    exit 1
}
Write-Host "  Resource group: OK" -ForegroundColor Green

# ── 4. Deploy Bicep template ───────────────────────────────────
Write-Host ""
Write-Host "[4/5] Deploying infrastructure (this takes ~5 minutes)..." -ForegroundColor Yellow

$deployParams = @(
    "--resource-group", $ResourceGroup,
    "--template-file", $bicepPath,
    "--parameters",
    "postgresAdminPassword=$PostgresPassword",
    "azureOpenAiDeploymentName=$LlmModel",
    "azureOpenAiEndpoint=$AzureOpenAiEndpoint"
)

if ($ContainerImage) {
    $deployParams += "containerImage=$ContainerImage"
}
if ($GhcrUsername) {
    $deployParams += "ghcrUsername=$GhcrUsername"
}
if ($GhcrToken) {
    $deployParams += "ghcrToken=$GhcrToken"
}

$result = az deployment group create @deployParams -o json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Deployment failed." -ForegroundColor Red
    Write-Host $result
    exit 1
}

# ── 5. Extract outputs ─────────────────────────────────────────
Write-Host ""
Write-Host "[5/5] Deployment complete!" -ForegroundColor Yellow

$outputs = ($result | ConvertFrom-Json).properties.outputs
$appUrl = $outputs.applicationUrl.value
$pgFqdn = $outputs.postgresFqdn.value

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Deployment Successful!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard:    $appUrl/dashboard"
Write-Host "  API Docs:     $appUrl/docs"
Write-Host "  Visualizer:   $appUrl/"
Write-Host ""
Write-Host "  PostgreSQL:   $pgFqdn"
Write-Host ""
Write-Host "  PostgreSQL password: $PostgresPassword"
Write-Host "  (Save this — it cannot be retrieved later)"
Write-Host ""
Write-Host "  To delete all resources:"
Write-Host "    az group delete --name $ResourceGroup --yes"
Write-Host ""
