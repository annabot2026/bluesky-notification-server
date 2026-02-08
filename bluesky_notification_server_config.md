# Bluesky Notification Server Configuration

## Required Environment Variables

```bash
export BLUESKY_HANDLE="your.handle.com"
export BLUESKY_PASSWORD="your_app_password"
export LETTA_API_KEY="your_letta_api_key"
export LETTA_AGENT_ID="agent-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**Important:** `BLUESKY_PASSWORD` must be an app password, not your account password. Generate one in your Bluesky account settings.

## Optional Environment Variables

```bash
export BLUESKY_PDS_URL="https://your-pds.example.com"  # Defaults to https://api.bsky.app
export LETTA_API_URL="https://api.letta.com"           # Defaults to http://localhost:8080
export LETTA_CONVERSATION_ID="conv-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # Route to specific conversation
```

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py
```

The server will:
1. Authenticate with your Bluesky PDS
2. Poll notifications every 5 minutes
3. Send only NEW notifications to Letta (duplicates are filtered)
4. Store notification history in `state.json` for deduplication

## Notification Format

Notifications are sent as formatted messages with emoji indicators:

```
🔔 You have 3 new Bluesky notifications:

• 💬 alice replied: nice post!
• ❤️ bob liked your post
• 👤 charlie followed you
```

## State Management

The server maintains `state.json` which tracks:

- `seen_notification_ids`: List of notification URIs already processed
- `last_check_time`: Timestamp of last polling cycle

This prevents duplicate notifications from being sent to Letta.

The server keeps track of the last 1000 notification IDs to prevent unbounded file growth.

## Endpoint Routing

**Without LETTA_CONVERSATION_ID:**
```
POST {LETTA_API_URL}/v1/agents/{LETTA_AGENT_ID}/messages
```

**With LETTA_CONVERSATION_ID:**
```
POST {LETTA_API_URL}/v1/conversations/{LETTA_CONVERSATION_ID}/messages
```

Use the conversation endpoint to send notifications to a specific conversation instead of the agent's default.

## Supported Bluesky PDS Instances

- **Bluesky (public)**: `https://api.bsky.app`
- **Custom PDS**: Any AT Protocol-compatible PDS (e.g., `https://yapfest.club`)

## Notes

- Poll interval is 5 minutes (300 seconds) by default
- Notification limit per poll is 50
- Connection timeouts are set to 10 seconds (PDS) and 30 seconds (Letta)
- Session tokens are cached in memory and re-authenticated on 401 errors
