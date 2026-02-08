"""Bluesky Notification Poller
Continuously polls Bluesky API for new notifications and sends them to Letta
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path

class BlueskyNotificationPoller:
    def __init__(self, bluesky_handle: str, bluesky_password: str, letta_api_key: str, letta_agent_id: str, state_file: str = "state.json"):
        self.bluesky_handle = bluesky_handle
        self.bluesky_password = bluesky_password
        self.letta_api_key = letta_api_key
        self.letta_agent_id = letta_agent_id
        self.state_file = Path(state_file)
        self.bluesky_api_url = "https://api.bsky.app"
        self.letta_api_url = "http://localhost:8080"  # Adjust if needed
        
        # Session token will be set after authentication
        self.session_token = None
        
        # Load or initialize state
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        """Load last cursor from state file"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "last_cursor": None,
            "last_check_time": None
        }
    
    def _save_state(self):
        """Save current state to file"""
        self.state["last_check_time"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _authenticate(self) -> bool:
        """Authenticate with Bluesky and get session token"""
        try:
            response = requests.post(
                f"{self.bluesky_api_url}/xrpc/com.atproto.server.createSession",
                json={
                    "identifier": self.bluesky_handle,
                    "password": self.bluesky_password
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            self.session_token = data.get("accessJwt")
            print(f"[{datetime.now().isoformat()}] Successfully authenticated with Bluesky")
            return True
        except requests.RequestException as e:
            print(f"Authentication error: {e}")
            return False
    
    def _get_notifications(self) -> dict:
        """Fetch notifications from Bluesky API"""
        if not self.session_token:
            if not self._authenticate():
                return {"notifications": []}
        
        headers = {
            "Authorization": f"Bearer {self.session_token}"
        }
        params = {
            "limit": 50
        }
        
        # Include cursor if we have one
        if self.state.get("last_cursor"):
            params["cursor"] = self.state["last_cursor"]
        
        try:
            response = requests.get(
                f"{self.bluesky_api_url}/xrpc/app.bsky.notification.listNotifications",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching notifications: {e}")
            # Clear token on auth errors so we re-authenticate next time
            if response.status_code == 401:
                self.session_token = None
            return {"notifications": []}
    
    def _send_to_letta(self, message: str):
        """Send notification message to Letta agent"""
        headers = {
            "Authorization": f"Bearer {self.letta_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "agent_id": self.letta_agent_id,
            "message": message,
            "role": "user"
        }
        
        try:
            response = requests.post(
                f"{self.letta_api_url}/v1/agents/{self.letta_agent_id}/messages",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            print(f"Message sent to Letta successfully")
        except requests.RequestException as e:
            print(f"Error sending to Letta: {e}")
    
    def _format_notification(self, notif: dict) -> str:
        """Format a single notification for display"""
        reason = notif.get("reason", "unknown")
        author = notif.get("author", {})
        author_name = author.get("displayName", author.get("handle", "Unknown"))
        
        if reason == "reply":
            text = notif.get("record", {}).get("text", "")
            preview = text[:80] + "..." if len(text) > 80 else text
            return f"💬 {author_name} replied: {preview}"
        elif reason == "like":
            return f"❤️ {author_name} liked your post"
        elif reason == "follow":
            return f"👤 {author_name} followed you"
        elif reason == "repost":
            return f"🔄 {author_name} reposted your post"
        else:
            return f"📬 {author_name} - {reason}"
    
    def poll(self):
        """Poll for new notifications and send to Letta if any found"""
        result = self._get_notifications()
        notifications = result.get("notifications", [])
        
        if not notifications:
            print(f"[{datetime.now().isoformat()}] No new notifications")
            self._save_state()
            return
        
        # Update cursor for next poll
        if "cursor" in result:
            self.state["last_cursor"] = result["cursor"]
        
        # Format notification summary
        count = len(notifications)
        message = f"🔔 You have {count} new Bluesky notification{'s' if count != 1 else ''}:\n\n"
        
        for notif in notifications[:10]:  # Limit to 10 most recent
            message += f"• {self._format_notification(notif)}\n"
        
        if count > 10:
            message += f"\n... and {count - 10} more"
        
        print(f"[{datetime.now().isoformat()}] Found {count} new notifications, sending to Letta")
        self._send_to_letta(message)
        self._save_state()
    
    def run(self, poll_interval: int = 300):
        """Run continuous polling loop (default: 5 minutes)"""
        print(f"Starting Bluesky notification poller (interval: {poll_interval}s)")
        
        # Initial authentication
        if not self._authenticate():
            print("Failed to authenticate. Exiting.")
            return
        
        try:
            while True:
                self.poll()
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\nShutting down notification poller")
        except Exception as e:
            print(f"Fatal error: {e}")
            raise


if __name__ == "__main__":
    import os
    
    # Load from environment variables
    bluesky_handle = os.getenv("BLUESKY_HANDLE")
    bluesky_password = os.getenv("BLUESKY_PASSWORD")
    letta_api_key = os.getenv("LETTA_API_KEY")
    letta_agent_id = os.getenv("LETTA_AGENT_ID")
    
    if not all([bluesky_handle, bluesky_password, letta_api_key, letta_agent_id]):
        print("Error: Missing required environment variables")
        print("Required: BLUESKY_HANDLE, BLUESKY_PASSWORD, LETTA_API_KEY, LETTA_AGENT_ID")
        exit(1)
    
    poller = BlueskyNotificationPoller(bluesky_handle, bluesky_password, letta_api_key, letta_agent_id)
    poller.run(poll_interval=300)  # 5 minutes