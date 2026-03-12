import os
import json
import requests
import base64
import sys
import time

def create_student_repo(student_username, student_name, mission_id):
    """Generates the mission repo, custom README, and ensures the portfolio site exists."""
    
    print("\n" + "="*60)
    print("🔧 CREATE-STUDENT-REPO.PY STARTED")
    print("="*60)
    
    token = os.environ.get("GH_TOKEN")
    org_name = "codequest-classroom"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # DEBUG: Check token and org access
    print(f"\n🔍 DEBUG: Verifying GH_TOKEN and Org access...")
    try:
        user_check = requests.get("https://api.github.com/user", headers=headers)
        if user_check.status_code == 200:
            print(f"✅ Authenticated as: {user_check.json().get('login')}")
        else:
            print(f"❌ Auth failed: {user_check.status_code}")
            return False
        
        org_check = requests.get(f"https://api.github.com/orgs/{org_name}", headers=headers)
        if org_check.status_code == 200:
            print(f"✅ Organization found: {org_name}")
        else:
            print(f"❌ Organization not found: {org_check.status_code}")
    except Exception as e:
        print(f"❌ Auth/organization check error: {e}")
    
    # 1. Load Data
    print(f"\n📁 Loading config files for {student_username}...")
    try:
        with open(f"students/{student_username}.json", 'r') as f: student_data = json.load(f)
        with open(f"missions/{mission_id}.json", 'r') as f: mission_data = json.load(f)
        with open(f"rubrics/{mission_id}.json", 'r') as f: rubric_data = json.load(f)
        print("✅ Config files loaded successfully")
    except Exception as e:
        print(f"❌ Load error: {e}")
        return False

    # 2. Identify Template
    # ADJUST THIS: Ensure this matches your template repo name exactly
    template_repo_name = "codequest-templates" 
    repo_name = f"{student_username}-{mission_id}"
    
    # 3. Generate Repo
    print(f"\n🛠️ Step 1: Creating {repo_name} from {org_name}/{template_repo_name}...")
    
    # CORRECT URL FORMAT: /repos/{owner}/{repo}/generate
    create_url = f"https://api.github.com/repos/{org_name}/{template_repo_name}/generate"
    
    payload = {
        "owner": org_name,
        "name": repo_name,
        "description": mission_data.get("description", "CodeQuest Mission"),
        "private": True
    }
    
    response = requests.post(create_url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print(f"✅ Repo created: {repo_name}")
        time.sleep(5) # Buffer for GitHub
        
        # 4. Invite Student (Method 1: Direct Invitation)
        print(f"\n📧 Step 2: Inviting {student_username}...")
        invite_url = f"https://api.github.com/repos/{org_name}/{repo_name}/invitations"
        invite_res = requests.post(invite_url, headers=headers, json={"invitee": student_username, "permissions": "push"})
        
        if invite_res.status_code == 201:
            print(f"✅ Invite sent! URL: {invite_res.json().get('html_url')}")
        else:
            print(f"⚠️ Invite failed ({invite_res.status_code}), trying collaborator fallback...")
            collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
            requests.put(collab_url, headers=headers, json={"permission": "push"})

        # 5. Push Mission Files
        print(f"\n📝 Step 3: Pushing mission files...")
        identity_content = {
            "username": student_username, "name": student_name,
            "xp": student_data.get("progress", {}).get("xp", 0),
            "currentMission": mission_id
        }
        
        files = [
            ("identity.json", json.dumps(identity_content, indent=2)),
            ("mission.json", json.dumps(mission_data, indent=2)),
            ("rubric.json", json.dumps(rubric_data, indent=2)),
            ("README.md", f"# 🚀 Mission: {mission_data['title']}\n\nHi {student_name}!")
        ]

        for filename, content in files:
            file_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{filename}"
            put_payload = {
                "message": f"🤖 Setup {filename}",
                "content": base64.b64encode(content.encode()).decode()
            }
            # GET existing file sha (required by GitHub API to update an existing file)
            existing = requests.get(file_url, headers=headers)
            if existing.status_code == 200:
                put_payload["sha"] = existing.json().get("sha")
            res = requests.put(file_url, headers=headers, json=put_payload)
            print(f"   {'✅' if res.status_code in [200, 201] else '❌'} {filename} ({res.status_code})")

        # 6. Create Portfolio Site
        create_portfolio_site(student_username, student_name, headers, org_name)

        print(f"\n✅ SETUP COMPLETE: https://github.com/{org_name}/{repo_name}")
        return True
    else:
        print(f"❌ FAIL: {response.status_code} - {response.text}")
        return False

def create_portfolio_site(student_username, student_name, headers, org_name):
    """Creates codequest-classroom/{username} as a public GitHub Pages portfolio site."""
    repo_name = student_username
    print(f"\n🌐 Step 4: Creating portfolio site ({org_name}/{repo_name})...")

    # Create public repo
    create_res = requests.post(
        f"https://api.github.com/orgs/{org_name}/repos",
        headers=headers,
        json={
            "name": repo_name,
            "description": f"🚀 {student_name}'s CodeQuest Progress",
            "private": False,
            "auto_init": False
        }
    )
    if create_res.status_code == 201:
        print(f"✅ Portfolio repo created")
        time.sleep(3)
    elif create_res.status_code == 422:
        print(f"ℹ️ Portfolio repo already exists, updating files...")
    else:
        print(f"❌ Failed to create portfolio repo: {create_res.status_code} - {create_res.text}")
        return

    # Fetch template files from codequest-templates/student-site-template
    template_files = ["index.html", "style.css", "script.js"]
    files_to_push = []
    for filename in template_files:
        url = f"https://api.github.com/repos/{org_name}/codequest-templates/contents/student-site-template/{filename}"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            # Re-encode cleanly (GitHub API wraps content with newlines)
            raw = base64.b64decode(res.json()['content'])
            files_to_push.append((filename, base64.b64encode(raw).decode()))
        else:
            print(f"⚠️ Could not fetch template {filename}: {res.status_code}")

    # config.json with the real username so script.js knows who this is
    config_content = json.dumps({"username": student_username}, indent=2)
    files_to_push.append(("config.json", base64.b64encode(config_content.encode()).decode()))

    # progress.json — initial record so the site loads before the student passes anything
    progress_content = json.dumps({
        "student": {"name": student_name, "username": student_username},
        "progress": {"xp": 0, "completedMissions": [], "badges": [], "currentMission": mission_id}
    }, indent=2)
    files_to_push.append(("progress.json", base64.b64encode(progress_content.encode()).decode()))

    # Push all files (GET sha first if file already exists)
    for filename, content in files_to_push:
        file_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{filename}"
        put_payload = {"message": f"🤖 Setup {filename}", "content": content}
        existing = requests.get(file_url, headers=headers)
        if existing.status_code == 200:
            put_payload["sha"] = existing.json().get("sha")
        res = requests.put(file_url, headers=headers, json=put_payload)
        print(f"   {'✅' if res.status_code in [200, 201] else '❌'} {filename} ({res.status_code})")

    # Enable GitHub Pages
    pages_res = requests.post(
        f"https://api.github.com/repos/{org_name}/{repo_name}/pages",
        headers=headers,
        json={"source": {"branch": "main", "path": "/"}}
    )
    if pages_res.status_code in [201, 409]:  # 409 = already enabled
        print(f"✅ GitHub Pages enabled")
    else:
        print(f"⚠️ Pages enable returned {pages_res.status_code}: {pages_res.text}")

    print(f"🌐 Portfolio site: https://{org_name}.github.io/{repo_name}")

if __name__ == "__main__":
    if len(sys.argv) < 4: sys.exit(1)
    create_student_repo(sys.argv[1], sys.argv[2], sys.argv[3])
