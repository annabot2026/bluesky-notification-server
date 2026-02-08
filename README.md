# Bluesky Notification Server

A lightweight server that continuously polls the Bluesky API for new notifications and sends them to Letta Agent.

## Setup

### Environment Variables

Create a `.env` file or export these variables:

```bash
export BLUESKY_HANDLE="annabot2026"
export BLUESKY_PASSWORD="your_bluesky_app_password"
export LETTA_API_KEY="your_letta_api_key"
export LETTA_AGENT_ID="your_agent_id"
```

**Note:** `BLUESKY_PASSWORD` should be an app password, not your account password. Generate one in Bluesky settings.

### Installation

```bash
pip install -r requirements.txt
python server.py
```

## How It Works

1. **Authentication**: Creates a session with Bluesky using handle + app password
2. **Continuous Polling**: Checks Bluesky notifications every 5 minutes
3. **Cursor Tracking**: Uses API cursor to avoid duplicate notifications
4. **Selective Notifications**: Only sends message to Letta when new interactions exist
5. **Formatted Output**: Emoji-coded notification types for quick scanning
   - 💬 replies
   - ❤️ likes
   - 👤 follows
   - 🔄 reposts

## State Management

The server maintains `state.json` with:
- `last_cursor`: Bluesky API cursor for incremental polling
- `last_check_time`: Timestamp of last poll (for debugging)

## Configuration

- **Poll Interval**: 300 seconds (5 minutes) by default
- **Letta API URL**: http://localhost:8080 (adjust if needed)
- **Notification Limit**: Shows top 10 + count of remaining

## Running as Service

To run continuously in the background:

```bash
# Using nohup
nohup python server.py > server.log 2>&1 &

# Using screen
screen -S bluesky-notify python server.py

# Using systemd (recommended)
# Create /etc/systemd/system/bluesky-notify.service
```