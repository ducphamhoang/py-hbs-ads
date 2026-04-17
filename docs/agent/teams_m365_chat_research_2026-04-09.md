# Teams / M365 chat research

Status: research only. No setup performed yet.

## Goal

Understand practical options for asking teammates questions through Microsoft Teams, either:
- direct message (1:1 chat)
- group chat

Priority:
- command-line friendly approach
- realistic auth model
- limits and risks known in advance

## Main conclusion

The realistic platform for Teams DM/group chat is Microsoft Graph.

For command-line usage:
- CLI for Microsoft 365 (`m365`) is the most practical shell wrapper
- use `m365 request` against Graph chat endpoints

PnP PowerShell is not the primary path for this use case.
It may help with auth or token handling, but it is not the natural first-class tool for Teams personal/group chat messaging.

## Practical options

### Option A — CLI for Microsoft 365 + Graph
Best choice for experimentation from a terminal.

Typical shape:
- `m365 login`
- `m365 request --method GET --url https://graph.microsoft.com/v1.0/me/chats`
- `m365 request --method GET --url https://graph.microsoft.com/v1.0/chats/{chat-id}/messages`
- `m365 request --method POST --url https://graph.microsoft.com/v1.0/chats/{chat-id}/messages --data '{...}'`
- `m365 request --method POST --url https://graph.microsoft.com/v1.0/chats --data '{...}'`

Use this for:
- listing chats
- reading chat messages
- sending a message into an existing chat
- creating a 1:1 or group chat, then sending a message

### Option B — Microsoft Graph directly
Best choice for a future real integration.

Relevant Graph endpoints:
- `GET /me/chats`
- `POST /chats`
- `GET /chats/{chat-id}/messages`
- `POST /chats/{chat-id}/messages`

### Option C — PnP PowerShell
Not the preferred path for Teams DM/group chat.

Treat it as:
- possible auth/token helper
- maybe a wrapper around Graph calls

Do not treat it as the main product surface for chat automation.

## Auth and permission expectations

Most practical model:
- delegated auth
- a real signed-in user account

Likely delegated permissions/scopes:
- `Chat.Read`
- `Chat.ReadWrite`
- `ChatMessage.Send`
- `Chat.Create`
- `User.Read`

Important warning:
- unattended app-only messaging into normal Teams chats is much harder / more restricted
- if later we need true bot-style autonomous messaging, we may need to research Teams bot/app model separately

## Limits / caveats

1. Channel messages are not the same as personal/group chats
- channel posts and chat messages use different Graph resources

2. Delegated auth is the likely viable path
- especially for “ask teammate X a question in chat”

3. Tenant consent/admin approval may be needed
- especially for chat read/write scopes

4. Teams/tenant policy may affect behavior
- DLP, retention, external chat policy, app policy, and tenant restrictions matter

5. Rich content is more complex
- plain message send is the easy case
- mentions, files, cards, and richer UX add complexity

## Strong environment finding

The local environment already has CLI for Microsoft 365 installed and authenticated.

Observed during research:
- command available: `m365`
- version observed: `v11.6.0`
- authenticated account observed: `ducph@vng.com.vn`
- auth type observed: `deviceCode`
- tenant observed: `vngms.onmicrosoft.com`

This is important because it means future experimentation may not need fresh login work.

## Repo/integration finding

Current Hermes repo does NOT have first-class Teams support yet.

What exists:
- no Teams gateway adapter
- no dedicated M365/Teams skill in active use for chat
- one old migration mapping stub mentioning `msteams`, but not a working adapter

Nearest reusable patterns in Hermes:
- `gateway/platforms/ADDING_A_PLATFORM.md` for a future Teams adapter
- Slack/Telegram/Webhook adapters as messaging-platform references
- Google Workspace skill as the best model for an OAuth/productivity-style integration

## Recommended next step

Do not build anything yet.

Next research/execution sequence should be:
1. verify `m365 status` in the local environment
2. test whether `m365 request` can list chats through Graph
3. test read-only access first (`/me/chats`)
4. then test sending to an existing chat
5. only after that consider whether we need:
   - a Hermes skill wrapping `m365`, or
   - a deeper Teams/Graph integration

## Recommendation summary

Use this decision rule:
- quick CLI experiments: `m365 request` + Graph
- real implementation later: Graph-first
- do not assume PnP PowerShell is the right main tool for DM/group-chat work
- keep bot/app-model research separate unless autonomous app-only messaging becomes necessary
