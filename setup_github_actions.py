"""
GitHub Actions setup guide.
Yeh run karo: python setup_github_actions.py
"""
import os
import json
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def main():
    print("\n" + "=" * 60)
    print("  GitHub Actions Setup — Laptop OFF rehega, 24/7 chalta rahega")
    print("=" * 60)

    # Step 1: Check token.json
    if not os.path.exists("token.json"):
        print("\nERROR: token.json nahi mila. Pehle python setup_youtube.py chalao.")
        sys.exit(1)

    print("\n✓ token.json mila")
    token_content = open("token.json").read().strip()

    # Step 2: Check git
    git_check = run("git --version")
    if git_check.returncode != 0:
        print("\nERROR: Git install nahi hai!")
        print("Yahan se install karo: https://git-scm.com/download/win")
        sys.exit(1)

    print("✓ Git available")

    # Step 3: Init git repo
    if not os.path.exists(".git"):
        run("git init")
        run("git add .")
        run('git commit -m "Initial commit: YouTube Shorts Agent"')
        print("✓ Git repo initialize ho gaya")
    else:
        print("✓ Git repo already exists")

    # Step 4: Print instructions
    print("\n" + "=" * 60)
    print("  STEP 1: GitHub pe repo banao")
    print("=" * 60)
    print("""
  1. Yahan jao: https://github.com/new
  2. Repository name: youtube-shorts-agent
  3. Private rakho (recommended — API keys safe rahenge)
  4. Create repository dabao
  5. Page pe yeh commands dikhega, copy karo:
     git remote add origin https://github.com/AAPKA_USERNAME/youtube-shorts-agent.git
     git branch -M main
     git push -u origin main
""")

    print("=" * 60)
    print("  STEP 2: GitHub Secrets add karo")
    print("=" * 60)
    print("""
  Repo page pe jao:
  Settings → Secrets and variables → Actions → New repository secret

  YEH 3 SECRETS ADD KARO:
""")

    with open(".env") as f:
        env = dict(line.strip().split("=", 1) for line in f if "=" in line and not line.startswith("#"))

    print(f"  Secret name : GROQ_API_KEY")
    print(f"  Secret value: {env.get('GROQ_API_KEY', 'NOT FOUND')}\n")

    print(f"  Secret name : PEXELS_API_KEY")
    print(f"  Secret value: {env.get('PEXELS_API_KEY', 'NOT FOUND')}\n")

    print(f"  Secret name : YOUTUBE_TOKEN_JSON")
    print(f"  Secret value: (token.json ka poora content paste karo)")
    print(f"\n--- TOKEN.JSON CONTENT (copy karo) ---")
    print(token_content)
    print(f"--- END ---\n")

    print("=" * 60)
    print("  STEP 3: Push karo")
    print("=" * 60)
    print("""
  Upar wale git commands run karo.
  Phir GitHub pe jao:
  Actions tab → Upload YouTube Short → Run workflow

  Ek baar manually test karo — agar sahi chala toh
  roz khud ba khud 9 AM aur 9 PM pe chalega!
""")

    print("=" * 60)
    print("  DONE! Laptop band kar sakte ho 😊")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
