# Lab 0: Test Connection

## What It Does
Verifies that your environment is correctly set up before you start building agents.

## Flow

```
  .env file
    |
    v
  Load PROJECT_ENDPOINT + MODEL_DEPLOYMENT_NAME
    |
    v
  Create AIProjectClient (using DefaultAzureCredential)
    |
    v
  Get OpenAI client from project client
    |
    v
  Send a test prompt --> "SmartClaims connection successful!"
    |
    v
  All checks passed -- ready for Lab 1
```

## Key Concepts

- **DefaultAzureCredential** picks up your `az login` session automatically
- **AIProjectClient** is the gateway to all Foundry agent operations
- **OpenAI client** is obtained from the project client, not created separately
- If this lab fails, nothing else will work -- fix connection issues here first

## SDK Used

- `AIProjectClient` -- project-level client
- `DefaultAzureCredential` -- authentication
- `openai_client.responses.create()` -- basic model call
