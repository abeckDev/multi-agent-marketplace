using './main.bicep'

// Required: Your Azure OpenAI endpoint
param azureOpenAiEndpoint = '<https://your-resource.openai.azure.com/>'

// Required: A strong password for PostgreSQL
param postgresAdminPassword = '<your-strong-password>'

// Optional: Override defaults
// param environmentName = 'magentic-marketplace'
// param azureOpenAiDeploymentName = 'gpt-5.3-chat'
// param azureOpenAiApiVersion = '2024-08-01-preview'
// param containerImage = 'ghcr.io/abeckdev/hosted-multi-agent-marketplace:latest'
