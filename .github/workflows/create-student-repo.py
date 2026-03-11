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
    
    # 1. Load Data from Master Repo folders
    try:
        with open(f"students/{student_username}.json", 'r') as f:
            student_data = json.load(f)
        with open(f"missions/{mission_id}.json", 'r') as f:
            mission_data = json.load(f)
        with open(f"rubrics/{mission_id}.json", 'r') as f:
            rubric_data = json.load(f)
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
        time.sleep(5) # Wait for GitHub provisioning
        
        # 4. Invite Student
        requests.put(f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}", 
                     headers=headers, json={"permission": "push"})

        # 5. Build Dynamic Files
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
        readme_content += f"### 💰 Reward: {mission_data['points']} XP | 🎖️ Badge: {mission_data.get('badge', 'None')}\n\n"
        readme_content += "## 📋 Requirements\n"
        for req in mission_data.get('requirements', []):
            readme_content += f"- [ ] {req}\n"
        readme_content += "\n## 🛠️ Submission\n1. Edit code in the `submissions/` folder.\n2. **Commit and Push** to grade."

        # Push to new Repo
        files = [
            ("identity.json", identity_content),
            ("mission.json", mission_data),
            ("rubric.json", rubric_data),
            ("README.md", readme_content)
        ]

        for filename, content in files:
            file_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{filename}"
            # Check for existing (overwriting template placeholders)
            get_res = requests.get(file_url, headers=headers)
            sha = get_res.json().get("sha") if get_res.status_code == 200 else None
            
            put_payload = {
                "message": f"🤖 Setup {filename}",
                "content": base64.b64encode(json.dumps(content, indent=2).encode() if isinstance(content, dict) else content.encode()).decode()
            }
            if sha: put_payload["sha"] = sha
            requests.put(file_url, headers=headers, json=put_payload)

    # 6. Ensure Student Site is up
    ensure_portfolio_site(student_username, student_name, token, org_name)
    return True

def ensure_portfolio_site(username, name, token, org):
    site_repo = f"{username}.github.io"
    headers = {"Authorization": f"token {token}"}
    check = requests.get(f"https://api.github.com/repos/{org}/{site_repo}", headers=headers)
    
    if check.status_code == 404:
        url = f"https://api.github.com/repos/{org}/codequest-templates/generate"
        requests.post(url, headers=headers, json={"owner": org, "name": site_repo, "private": False})

if __name__ == "__main__":
    create_student_repo(sys.argv[1], sys.argv[2], sys.argv[3])
