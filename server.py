"""Bluesky Notification Poller
Continuously polls Bluesky API for new notifications and sends them to Letta
"""

import json
import time
import requests
import os
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    dotenv_loaded = load_dotenv()
    print(f"[DEBUG] python-dotenv loaded: {dotenv_loaded}")
except ImportError as e:
    print(f"[DEBUG] python-dotenv import failed: {e}")
    dotenv_loaded = False

class BlueskyNotificationPoller:
    def __init__(self, bluesky_handle: str, bluesky_password: str, letta_api_key: str, letta_agent_id: str, bluesky_pds_url: str = "https://api.bsky.app", letta_api_url: str = "http://localhost:8080", letta_conversation_id: str = None, state_file: str = "state.json"):
        self.bluesky_handle = bluesky_handle
        self.bluesky_password = bluesky_password
        self.letta_api_key = letta_api_key
        self.letta_agent_id = letta_agent_id
        self.letta_conversation_id = letta_conversation_id
        self.state_file = Path(state_file)
        self.bluesky_pds_url = bluesky_pds_url
        self.letta_api_url = letta_api_url
        self.max_tracked_ids = 1000  # Keep track of up to 1000 notification IDs
        
        print(f"[DEBUG] Using Bluesky PDS URL: {self.bluesky_pds_url}")
        print(f"[DEBUG] Using Letta API URL: {self.letta_api_url}")
        if self.letta_conversation_id:
            print(f"[DEBUG] Using Letta Conversation ID: {self.letta_conversation_id}")
        else:
            print(f"[DEBUG] Using Letta Agent ID: {self.letta_agent_id}")
        
        # Session token will be set after authentication
        self.session_token = None
        
        # Load or initialize state
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        """Load state from file"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                state = json.load(f)
                print(f"[DEBUG] Loaded state from file, tracking {len(state.get('seen_notification_ids', []))} notification IDs")
                return state
        print(f"[DEBUG] State file does not exist, initializing new state")
        return {
            "seen_notification_ids": [],
            "last_check_time": None
        }
    
    def _save_state(self):
        """Save current state to file"""
        self.state["last_check_time"] = datetime.now().isoformat()
        # Keep state file size reasonable by limiting tracked IDs
        if len(self.state.get("seen_notification_ids", [])) > self.max_tracked_ids:
            self.state["seen_notification_ids"] = self.state["seen_notification_ids"][-self.max_tracked_ids:]
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _authenticate(self) -> bool:
        """Authenticate with Bluesky PDS and get session token"""
        try:
            response = requests.post(
                f"{self.bluesky_pds_url}/xrpc/com.atproto.server.createSession",
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
        """Fetch notifications from Bluesky PDS"""
        if not self.session_token:
            if not self._authenticate():
                return {"notifications": []}
        
        headers = {
            "Authorization": f"Bearer {self.session_token}"
        }
        params = {
            "limit": 50
        }
        
        try:
            response = requests.get(
                f"{self.bluesky_pds_url}/xrpc/app.bsky.notification.listNotifications",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching notifications: {e}")
            # Clear token on auth errors so we re-authenticate next time
            if hasattr(e, 'response') and e.response.status_code == 401:
                self.session_token = None
            return {"notifications": []}
    
    def _send_to_letta(self, message: str):
        """Send notification message to Letta agent or conversation"""
        headers = {
            "Authorization": f"Bearer {self.letta_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": message
        }
        
        # Determine endpoint based on whether conversation_id is specified
        if self.letta_conversation_id:
            url = f"{self.letta_api_url}/v1/conversations/{self.letta_conversation_id}/messages"
        else:
            url = f"{self.letta_api_url}/v1/agents/{self.letta_agent_id}/messages"
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
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
        
        # Filter out notifications we've already seen
        seen_ids = set(self.state.get("seen_notification_ids", []))
        new_notifications = [n for n in notifications if n.get("uri") not in seen_ids]
        
        if not new_notifications:
            print(f"[{datetime.now().isoformat()}] No new notifications (received {len(notifications)}, all previously seen)")
            self._save_state()
            return
        
        # Format notification summary
        count = len(new_notifications)
        message = f"🔔 You have {count} new Bluesky notification{'s' if count != 1 else ''}:\n\n"
        
        for notif in new_notifications[:10]:  # Limit to 10 most recent
            message += f"• {self._format_notification(notif)}\n"
        
        if count > 10:
            message += f"\n... and {count - 10} more"
        
        print(f"[{datetime.now().isoformat()}] Found {count} new notifications (out of {len(notifications)} total), sending to Letta")
        self._send_to_letta(message)
        
        # Track all notifications we just received
        for notif in notifications:
            notif_uri = notif.get("uri")
            if notif_uri and notif_uri not in seen_ids:
                self.state["seen_notification_ids"].append(notif_uri)
        
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
    # Load from environment variables (or .env file if python-dotenv is installed)
    bluesky_handle = os.getenv("BLUESKY_HANDLE")
    bluesky_password = os.getenv("BLUESKY_PASSWORD")
    letta_api_key = os.getenv("LETTA_API_KEY")
    letta_agent_id = os.getenv("LETTA_AGENT_ID")
    bluesky_pds_url = os.getenv("BLUESKY_PDS_URL", "https://api.bsky.app")
    letta_api_url = os.getenv("LETTA_API_URL", "http://localhost:8080")
    letta_conversation_id = os.getenv("LETTA_CONVERSATION_ID")
    
    # Debug output
    print(f"[DEBUG] BLUESKY_HANDLE: {bluesky_handle}")
    print(f"[DEBUG] BLUESKY_PASSWORD: {'*' * len(bluesky_password) if bluesky_password else None}")
    print(f"[DEBUG] LETTA_API_KEY: {'*' * len(letta_api_key) if letta_api_key else None}")
    print(f"[DEBUG] LETTA_AGENT_ID: {letta_agent_id}")
    print(f"[DEBUG] BLUESKY_PDS_URL: {bluesky_pds_url}")
    print(f"[DEBUG] LETTA_API_URL: {letta_api_url}")
    if letta_conversation_id:
        print(f"[DEBUG] LETTA_CONVERSATION_ID: {letta_conversation_id}")
    
    if not all([bluesky_handle, bluesky_password, letta_api_key, letta_agent_id]):
        print("\nError: Missing required environment variables")
        print("Required: BLUESKY_HANDLE, BLUESKY_PASSWORD, LETTA_API_KEY, LETTA_AGENT_ID")
        print("Optional: BLUESKY_PDS_URL (defaults to https://api.bsky.app)")
        print("Optional: LETTA_API_URL (defaults to http://localhost:8080)")
        print("Optional: LETTA_CONVERSATION_ID (to send to a specific conversation)")
        print("\nYou can set these in a .env file or export them:")
        print("  export BLUESKY_HANDLE='anna.yapfest.club'")
        print("  export BLUESKY_PASSWORD='your_app_password'")
        print("  export LETTA_API_KEY='your_key'")
        print("  export LETTA_AGENT_ID='your_id'")
        print("  export BLUESKY_PDS_URL='https://yapfest.club'  # Optional")
        print("  export LETTA_API_URL='https://api.letta.com'  # Optional")
        print("  export LETTA_CONVERSATION_ID='your_conversation_id'  # Optional")
        exit(1)
    
    poller = BlueskyNotificationPoller(bluesky_handle, bluesky_password, letta_api_key, letta_agent_id, bluesky_pds_url, letta_api_url, letta_conversation_id)
    poller.run(poll_interval=300)  # 5 minutes