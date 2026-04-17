# Teams / M365 auth next steps

Status: research only. No setup changes applied yet.

## What we verified

### 1. Existing `m365` login is real
Observed current CLI for Microsoft 365 connection:
- connected user: `ducph@vng.com.vn`
- auth type: `deviceCode`
- tenant: `vngms.onmicrosoft.com`

### 2. Current connection does NOT have Teams chat scopes
Direct tests:
- `m365 request --method get --url https://graph.microsoft.com/v1.0/me`
- `m365 request --method get --url https://graph.microsoft.com/v1.0/me/chats?$top=5`

Result:
- both returned `403`
- `/me/chats` explicitly said the token is missing one of:
  - `Chat.ReadBasic`
  - `Chat.Read`
  - `Chat.ReadWrite`

Current token scopes observed in debug output were effectively only:
- `user_impersonation`
- `profile`
- `openid`
- `email`

So the existing connection is not usable for Teams DM/group-chat experiments.

## Important auth finding about `m365`

The installed CLI for Microsoft 365 uses browser/device-code login with static `/.default` scopes.

That means:
- it does NOT ask for arbitrary Graph scopes like `Chat.Read` dynamically
- it only gets whatever delegated Graph permissions are already configured on the Entra app registration being used

Consequence:
- simply running `m365 login` again with the current/default app will NOT fix Teams chat access

## Practical path forward

### Preferred path if we want to stay with `m365`

Use a custom Entra app registration for CLI authentication.

Requirements for that app:
- delegated Microsoft Graph permissions for the chat operations we want

Suggested delegated permissions:
- `Chat.Read` or `Chat.ReadWrite`
- `ChatMessage.Send`
- `Chat.Create`
- optional: `ChatMessage.Read.Chat`

Likely consent reality:
- `Chat.Read` / `Chat.ReadWrite` likely need admin consent
- `ChatMessage.Send` may be easier, but still depends on tenant policy
- `Chat.Create` should be validated with tenant admin during setup

How CLI for Microsoft 365 can use a custom app:
- set environment variables:
  - `CLIMICROSOFT365_ENTRAIDAPPID=<app-id>`
  - `CLIMICROSOFT365_TENANT=<tenant-id>`
- then re-auth:
  - `m365 logout`
  - `m365 login --authType browser --tenant <tenant-id>`
  - or `m365 login --authType deviceCode --tenant <tenant-id>`

Then re-test:
- `m365 request --method get --url https://graph.microsoft.com/v1.0/me/chats`
- `m365 request --method get --url https://graph.microsoft.com/v1.0/chats/{chat-id}/messages`

## Why not PnP PowerShell first

PnP PowerShell is not the natural first-class tool for Teams DM/group-chat messaging.

For this use case:
- Graph is the real platform
- `m365 request` is the most practical CLI wrapper
- PnP PowerShell should not be treated as the main path initially

## Best next step

Do NOT do tenant/app setup blindly.

Next step should be:
1. identify whether a reusable Entra app registration already exists in the tenant for Graph chat scopes
2. if not, request or create a custom app registration for `m365`
3. grant the delegated chat permissions above
4. only then retry Teams chat experiments
