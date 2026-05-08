"""
One-time YouTube OAuth setup.
Run this once to connect your YouTube channel.
After this, the agent uploads automatically.
"""
import os
import sys


def main():
    print("\n" + "=" * 55)
    print("  YouTube Channel Setup")
    print("=" * 55)

    if not os.path.exists("client_secrets.json"):
        print("""
ERROR: client_secrets.json not found in this folder.

To get it (all free, takes ~3 minutes):
  1. Go to https://console.cloud.google.com/
  2. Create a new project (any name)
  3. In the search bar, search "YouTube Data API v3"
  4. Click Enable
  5. Go to: APIs & Services > Credentials
  6. Click "+ Create Credentials" > OAuth 2.0 Client ID
  7. Application type: Desktop App
  8. Download the JSON file
  9. Rename it to: client_secrets.json
 10. Place it in this folder, then run this script again
""")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: Run 'pip install -r requirements.txt' first")
        sys.exit(1)

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    print("\nA browser window will open — log in and grant permission...")
    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    creds = flow.run_local_server(port=0)

    with open("token.json", "w") as f:
        f.write(creds.to_json())

    print("\n" + "=" * 55)
    print("  SUCCESS! Channel connected.")
    print("  token.json saved — agent can now upload automatically.")
    print("=" * 55)
    print("\nNext steps:")
    print("  1. Copy .env.example to .env and fill in your API keys")
    print("  2. Run 'python main.py' to test a single video")
    print("  3. Run 'python scheduler.py' for daily automation")
    print()


if __name__ == "__main__":
    main()
