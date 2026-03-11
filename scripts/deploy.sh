#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────
# Magentic Marketplace — One-Command Azure Deployment
#
# Uses Azure OpenAI with Entra ID (Managed Identity) — no API keys needed.
#
# Usage:
#   ./scripts/deploy.sh --azure-openai-endpoint "https://my-resource.openai.azure.com/"
#
#   # All options
#   ./scripts/deploy.sh \
#     --resource-group my-rg \
#     --location swedencentral \
#     --azure-openai-endpoint "https://my-resource.openai.azure.com/" \
#     --model gpt-5.3-chat \
#     --postgres-password "MyStr0ngPassword123"
# ─────────────────────────────────────────────────────────────────

RESOURCE_GROUP="magentic-marketplace-rg"
LOCATION="swedencentral"
AZURE_OPENAI_ENDPOINT=""
LLM_MODEL=""
POSTGRES_PASSWORD=""
CONTAINER_IMAGE=""
GHCR_USERNAME=""
GHCR_TOKEN=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --resource-group)       RESOURCE_GROUP="$2"; shift 2 ;;
        --location)             LOCATION="$2"; shift 2 ;;
        --azure-openai-endpoint) AZURE_OPENAI_ENDPOINT="$2"; shift 2 ;;
        --model)                LLM_MODEL="$2"; shift 2 ;;
        --postgres-password)    POSTGRES_PASSWORD="$2"; shift 2 ;;
        --container-image)      CONTAINER_IMAGE="$2"; shift 2 ;;
        --ghcr-username)        GHCR_USERNAME="$2"; shift 2 ;;
        --ghcr-token)           GHCR_TOKEN="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Required:"
            echo "  --azure-openai-endpoint URL   Azure OpenAI endpoint (uses Managed Identity)"
            echo ""
            echo "Optional:"
            echo "  --resource-group NAME         Resource group (default: magentic-marketplace-rg)"
            echo "  --location REGION             Azure region (default: swedencentral)"
            echo "  --model NAME                  Model/deployment name (default: gpt-5.3-chat)"
            echo "  --postgres-password PASS      PostgreSQL password (auto-generated if omitted)"
            echo "  --container-image IMAGE       Custom container image"
            echo "  --ghcr-username USER          GHCR username (for private images)"
            echo "  --ghcr-token TOKEN            GHCR PAT (for private images)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BICEP_PATH="$SCRIPT_DIR/../infra/main.bicep"

echo ""
echo "=== Magentic Marketplace — Azure Deployment ==="
echo ""

# ── 1. Check prerequisites ──────────────────────────────────────
echo "[1/5] Checking prerequisites..."

if ! command -v az &> /dev/null; then
    echo "ERROR: Azure CLI (az) is not installed."
    echo "  Install: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

if ! az account show &> /dev/null; then
    echo "ERROR: Not logged in to Azure CLI. Run 'az login' first."
    exit 1
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "  Azure CLI: OK"
echo "  Subscription: $SUBSCRIPTION ($SUBSCRIPTION_ID)"

if [[ ! -f "$BICEP_PATH" ]]; then
    echo "ERROR: infra/main.bicep not found. Run this script from the repository root."
    exit 1
fi
echo "  Bicep template: OK"

# ── 2. Collect configuration ────────────────────────────────────
echo ""
echo "[2/5] Configuring deployment..."

if [[ -z "$AZURE_OPENAI_ENDPOINT" ]]; then
    read -rp "  Azure OpenAI endpoint (e.g. https://my-resource.openai.azure.com/): " AZURE_OPENAI_ENDPOINT
    if [[ -z "$AZURE_OPENAI_ENDPOINT" ]]; then
        echo "ERROR: Azure OpenAI endpoint is required."
        exit 1
    fi
fi

if [[ -z "$LLM_MODEL" ]]; then
    read -rp "  Model/deployment name (default: gpt-5.3-chat): " LLM_MODEL
    LLM_MODEL="${LLM_MODEL:-gpt-5.3-chat}"
fi

if [[ -z "$POSTGRES_PASSWORD" ]]; then
    POSTGRES_PASSWORD=$(LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 24 || true)
    echo "  PostgreSQL password: (auto-generated)"
fi

echo ""
echo "  Configuration summary:"
echo "    Resource group:  $RESOURCE_GROUP"
echo "    Location:        $LOCATION"
echo "    Endpoint:        $AZURE_OPENAI_ENDPOINT"
echo "    Model:           $LLM_MODEL"
if [[ -n "$CONTAINER_IMAGE" ]]; then
    echo "    Container image: $CONTAINER_IMAGE"
else
    echo "    Container image: (default public image)"
fi

echo ""
read -rp "  Proceed with deployment? (Y/n): " confirm
if [[ -n "$confirm" && "$confirm" != [yY]* ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# ── 3. Create resource group ────────────────────────────────────
echo ""
echo "[3/5] Creating resource group '$RESOURCE_GROUP'..."

az group create --name "$RESOURCE_GROUP" --location "$LOCATION" -o none
echo "  Resource group: OK"

# ── 4. Deploy Bicep template ───────────────────────────────────
echo ""
echo "[4/5] Deploying infrastructure (this takes ~5 minutes)..."

DEPLOY_PARAMS=(
    "postgresAdminPassword=$POSTGRES_PASSWORD"
    "azureOpenAiDeploymentName=$LLM_MODEL"
    "azureOpenAiEndpoint=$AZURE_OPENAI_ENDPOINT"
)

if [[ -n "$CONTAINER_IMAGE" ]]; then
    DEPLOY_PARAMS+=("containerImage=$CONTAINER_IMAGE")
fi
if [[ -n "$GHCR_USERNAME" ]]; then
    DEPLOY_PARAMS+=("ghcrUsername=$GHCR_USERNAME")
fi
if [[ -n "$GHCR_TOKEN" ]]; then
    DEPLOY_PARAMS+=("ghcrToken=$GHCR_TOKEN")
fi

PARAMS_STRING=$(IFS=' '; echo "${DEPLOY_PARAMS[*]}")

RESULT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$BICEP_PATH" \
    --parameters $PARAMS_STRING \
    -o json)

# ── 5. Extract outputs ─────────────────────────────────────────
echo ""
echo "[5/5] Deployment complete!"

APP_URL=$(echo "$RESULT" | jq -r '.properties.outputs.applicationUrl.value')
PG_FQDN=$(echo "$RESULT" | jq -r '.properties.outputs.postgresFqdn.value')

echo ""
echo "============================================="
echo "  Deployment Successful!"
echo "============================================="
echo ""
echo "  Dashboard:    $APP_URL/dashboard"
echo "  API Docs:     $APP_URL/docs"
echo "  Visualizer:   $APP_URL/"
echo ""
echo "  PostgreSQL:   $PG_FQDN"
echo ""
echo "  PostgreSQL password: $POSTGRES_PASSWORD"
echo "  (Save this — it cannot be retrieved later)"
echo ""
echo "  To delete all resources:"
echo "    az group delete --name $RESOURCE_GROUP --yes"
echo ""
