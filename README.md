# Bluesky Notification Server

A lightweight server that continuously polls the Bluesky API for new notifications and sends them to Letta Agent via conversation messages.

## Features

- ✅ Real-time notification polling (5-minute intervals)
- ✅ Automatic deduplication (tracks seen notifications)
- ✅ Supports custom Bluesky PDS instances
- ✅ Configurable Letta API endpoints
- ✅ Beautifully formatted notifications with emoji indicators
- ✅ Conversation-based message routing

## Quick Start

### Prerequisites

- Python 3.7+
- Bluesky account (on any PDS)
- Letta Agent access (cloud or local)
- App password for Bluesky (generate in account settings)

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project directory:

```bash
BLUESKY_HANDLE=your.handle.com
BLUESKY_PASSWORD=your_app_password
LETTA_API_KEY=your_letta_api_key
LETTA_AGENT_ID=agent-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
BLUESKY_PDS_URL=https://your-pds.example.com  # Optional, defaults to https://api.bsky.app
LETTA_API_URL=https://api.letta.com           # Optional, defaults to http://localhost:8080
LETTA_CONVERSATION_ID=conv-xxxxx             # Optional, to send to specific conversation
```

### Running

```bash
python server.py
```

## How It Works

1. **Authenticates** with your Bluesky PDS using handle + app password
2. **Polls** notifications every 5 minutes
3. **Deduplicates** by tracking notification URIs in `state.json`
4. **Sends** only new notifications to Letta as formatted messages
5. **Stores** seen notification IDs (keeps last 1000 to prevent unbounded growth)

## Notification Format

Notifications are formatted with emoji indicators:

```
🔔 You have 3 new Bluesky notifications:

• 💬 alice replied: nice post!
• ❤️ bob liked your post
• 👤 charlie followed you
```

Supported notification types:
- **💬 Replies** - Text preview included
- **❤️ Likes** - Who liked your post
- **👤 Follows** - New followers
- **🔄 Reposts** - Who reposted your content

## API Integration

### Bluesky

The server uses the AT Protocol's `app.bsky.notification.listNotifications` endpoint to fetch notifications. It supports both:
- Standard Bluesky PDS (`https://api.bsky.app`)
- Custom PDS instances (set via `BLUESKY_PDS_URL`)

### Letta

Notifications are sent via Letta's messages API:
- **Agent endpoint:** `/v1/agents/{agent_id}/messages`
- **Conversation endpoint:** `/v1/conversations/{conversation_id}/messages`

Use `LETTA_CONVERSATION_ID` to route to a specific conversation.

## State Management

The server maintains `state.json` which tracks:
- `seen_notification_ids`: Array of notification URIs already processed
- `last_check_time`: Timestamp of last polling cycle

This prevents duplicate notifications from being sent to Letta across restarts.

## Troubleshooting

### "No new notifications" every poll

This is normal! It means:
1. First poll found and sent notifications
2. Subsequent polls have no new notifications
3. Deduplication is working correctly

### Authentication errors

Make sure:
- `BLUESKY_HANDLE` includes the full domain (e.g., `username.bsky.social`)
- `BLUESKY_PASSWORD` is an app password, not your account password
- App password was generated in Bluesky account settings

### Notifications not reaching Letta

Check:
- `LETTA_API_URL` is correct (default: `http://localhost:8080` for local, `https://api.letta.com` for cloud)
- `LETTA_API_KEY` has proper permissions
- `LETTA_AGENT_ID` or `LETTA_CONVERSATION_ID` is valid

## Requirements

```
requests>=2.31.0
python-dotenv>=1.0.0
```

## License

MIT
