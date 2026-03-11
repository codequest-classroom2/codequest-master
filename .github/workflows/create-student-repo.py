import os
import json
import requests
import base64
import sys
import time

def create_student_repo(student_username, student_name, mission_id):
    """Generates the mission repo, custom README, and ensures the portfolio site exists."""
    
    token = os.environ.get("GH_TOKEN")
    org_name = "codequest-classroom"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print(f"📦 Starting creation for {student_username}...")
    
    # 1. Load Data from Master Repo folders
    try:
        with open(f"students/{student_username}.json", 'r') as f:
            student_data = json.load(f)
        with open(f"missions/{mission_id}.json", 'r') as f:
            mission_data = json.load(f)
        with open(f"rubrics/{mission_id}.json", 'r') as f:
            rubric_data = json.load(f)
        print("✅ Loaded all config files")
    except FileNotFoundError as e:
        print(f"❌ Missing config file: {e}")
        return False

    # 2. Identify Template
    template_name = mission_data.get("template", "basic-web-mission")
    repo_name = f"{student_username}-{mission_id}"
    
    # 3. Generate Private Repo
    print(f"🛠️ Creating {repo_name}...")
    create_url = f"https://api.github.com/repos/{org_name}/{template_name}/generate"
    payload = {
        "owner": org_name,
        "name": repo_name,
        "description": mission_data.get("description", "CodeQuest Mission"),
        "private": True
    }
    
    response = requests.post(create_url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print(f"✅ Repo created successfully!")
        time.sleep(5)  # Wait for GitHub provisioning
        
        # 4. NOW PUSH ALL THE FILES (THIS IS THE CRITICAL PART!)
        print(f"📝 Pushing mission files to {repo_name}...")
        
        # Create Identity
        identity_content = {
            "username": student_username,
            "name": student_name,
            "xp": student_data.get("progress", {}).get("xp", 0),
            "completedMissions": student_data.get("progress", {}).get("completedMissions", []),
            "currentMission": mission_id,
            "badges": student_data.get("progress", {}).get("badges", [])
        }

        # Create README from mission.json requirements
        readme_content = f"# 🚀 Mission: {mission_data['title']}\n\n"
        readme_content += f"### 👋 Hey {student_name}!\n\n"
        readme_content += f"### 💰 Reward: {mission_data['points']} XP | 🎖️ Badge: {mission_data.get('badge', 'None')}\n\n"
        readme_content += "## 📋 Requirements\n"
        for req in mission_data.get('requirements', []):
            readme_content += f"- [ ] {req}\n"
        readme_content += "\n## 🛠️ Submission\n"
        readme_content += "1. Edit code in the `submissions/` folder.\n"
        readme_content += "2. **Commit and Push** to get AI feedback.\n"

        # Push files to new Repo
        files = [
            ("identity.json", json.dumps(identity_content, indent=2)),
            ("mission.json", json.dumps(mission_data, indent=2)),
            ("rubric.json", json.dumps(rubric_data, indent=2)),
            ("README.md", readme_content)
        ]

        files_pushed = 0
        for filename, content in files:
            file_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{filename}"
            
            # Check for existing file
            get_res = requests.get(file_url, headers=headers)
            sha = get_res.json().get("sha") if get_res.status_code == 200 else None
            
            put_payload = {
                "message": f"🤖 Setup {filename}",
                "content": base64.b64encode(content.encode()).decode()
            }
            if sha:
                put_payload["sha"] = sha
                
            put_response = requests.put(file_url, headers=headers, json=put_payload)
            
            if put_response.status_code in [200, 201]:
                print(f"   ✅ Pushed {filename}")
                files_pushed += 1
            else:
                print(f"   ⚠️ Failed to push {filename}: {put_response.status_code}")

        print(f"\n✅ Successfully pushed {files_pushed}/{len(files)} files to {repo_name}")
        
        # 5. INVITE STUDENT AS COLLABORATOR
        print(f"📧 Inviting {student_username} to the repo...")
        invite_url = f"https://api.github.com/repos/{org_name}/{repo_name}/invitations"
        invite_response = requests.post(
            invite_url, 
            headers=headers, 
            json={"invitee": student_username}
        )
        
        if invite_response.status_code == 201:
            print(f"✅ Invitation sent to {student_username}!")
        else:
            # Fallback
            collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
            collab_response = requests.put(collab_url, headers=headers, json={"permission": "push"})
            if collab_response.status_code in [201, 204]:
                print(f"✅ Added {student_username} as collaborator")
            else:
                print(f"❌ Failed to add collaborator")

    else:
        print(f"❌ Failed to create repo: {response.status_code}")
        print(response.text)
        return False

    # 6. Ensure Student Site is up
    ensure_portfolio_site(student_username, student_name, token, org_name)
    
    print(f"\n🎉 ALL DONE! Student can now access:")
    print(f"   📚 Mission: https://github.com/{org_name}/{repo_name}")
    print(f"   🌐 Portfolio: https://{student_username}.github.io")
    
    return True

def ensure_portfolio_site(username, name, token, org):
    site_repo = f"{username}.github.io"
    headers = {"Authorization": f"token {token}"}
    
    check = requests.get(f"https://api.github.com/repos/{org}/{site_repo}", headers=headers)
    
    if check.status_code == 404:
        print(f"📦 Creating portfolio site: {site_repo}")
        url = f"https://api.github.com/repos/{org}/codequest-templates/generate"
        payload = {
            "owner": org,
            "name": site_repo,
            "description": f"{name}'s Coding Quest",
            "private": False
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"✅ Portfolio site created")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create-student-repo.py <username> <name> <mission_id>")
        sys.exit(1)
    
    success = create_student_repo(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
