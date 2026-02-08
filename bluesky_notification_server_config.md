# Bluesky Notification Server Setup

## Environment Variables Required

```bash
export BLUESKY_HANDLE="anna.yapfest.club"
export BLUESKY_PASSWORD="your_bluesky_app_password"
export LETTA_API_KEY="your_letta_api_key"
export LETTA_AGENT_ID="your_agent_id"
```

## Environment Variables Optional

```bash
export BLUESKY_PDS_URL="https://yapfest.club"  # Defaults to https://api.bsky.app if not set
```

**Important Notes:**
- `BLUESKY_PASSWORD` must be an app password, not your account password. Generate one in your Bluesky account settings.
- `BLUESKY_PDS_URL` should be set if you're using a custom PDS (Personal Data Server). For example, if your handle is `anna.yapfest.club`, you would use `https://yapfest.club`. If using a standard Bluesky account, leave this unset or use `https://api.bsky.app`.

## Installation

```bash
pip install -r requirements.txt
```

## Requirements

```
requests>=2.31.0
python-dotenv>=1.0.0
```

## Running the Server

```bash
python server.py
```

The server will:
1. Authenticate with your Bluesky PDS using your handle and app password
2. Poll Bluesky notifications every 5 minutes
3. Only send a message to Letta if new notifications exist
4. Track the last cursor in `state.json` to avoid duplicate notifications
5. Format notifications nicely with emoji indicators:
   - 💬 for replies
   - ❤️ for likes
   - 👤 for follows
   - 🔄 for reposts

## State Management

The server maintains `state.json` with:
- `last_cursor`: Used by Bluesky API to fetch only new notifications
- `last_check_time`: Timestamp of last successful poll (for debugging)

## Notes

- Letta API URL defaults to `http://localhost:8080` - adjust in server.py if needed
- Poll interval is set to 300 seconds (5 minutes) by default - adjustable in server.py
- Supports graceful shutdown with Ctrl+C
- Session tokens are cached in memory and will be refreshed on 401 errors
