import os
import json
import requests
import base64
import sys
import time

def create_student_repo(student_username, student_name, mission_id):
    """Generates a private mission repo and ensures the student's portfolio site exists."""
    
    token = os.environ.get("GH_TOKEN")
    org_name = "codequest-classroom"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Select the correct template based on Mission ID
    if mission_id.startswith(('html-', 'css-', 'js-')):
        template_name = "basic-web-mission"
    else:
        template_name = "basic-python-mission"

    # 2. Load Local Master Data
    try:
        with open(f"students/{student_username}.json", 'r') as f:
            student_data = json.load(f)
        with open(f"missions/{mission_id}.json", 'r') as f:
            mission_data = json.load(f)
        with open(f"rubrics/{mission_id}.json", 'r') as f:
            rubric_data = json.load(f)
    except FileNotFoundError as e:
        print(f"❌ Error: Missing configuration file: {e}")
        return False

    repo_name = f"{student_username}-{mission_id}"
    
    # 3. Generate the Private Repo from Template
    print(f"📦 Generating {repo_name} from {template_name}...")
    create_url = f"https://api.github.com/repos/{org_name}/{template_name}/generate"
    payload = {
        "owner": org_name,
        "name": repo_name,
        "description": f"Quest: {mission_data.get('title')} | Student: {student_name}",
        "private": True,
        "include_all_branches": False
    }
    
    response = requests.post(create_url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print(f"✅ Repo created. Waiting for GitHub to provision...")
        time.sleep(5) # Essential for GitHub to finalize the new repo
        
        # 4. Invite Student as Collaborator (Push access)
        collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
        requests.put(collab_url, headers=headers, json={"permission": "push"})
        print(f"👤 {student_username} invited to collaborate.")

        # 5. Push Mission Files to the Student's Repo
        # We wrap the data to match the structure expected by script.js and review.py
        identity_content = {
            "username": student_username,
            "name": student_name,
            "xp": student_data.get("progress", {}).get("xp", 0),
            "completedMissions": student_data.get("progress", {}).get("completedMissions", []),
            "currentMission": mission_id
        }

        files_to_push = [
            ("identity.json", identity_content),
            ("mission.json", mission_data),
            ("rubric.json", rubric_data)
        ]

        for filename, content in files_to_push:
            file_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{filename}"
            # Check for existing file SHA (though shouldn't exist in a fresh template)
            get_res = requests.get(file_url, headers=headers)
            sha = get_res.json().get("sha") if get_res.status_code == 200 else None
            
            put_payload = {
                "message": f"🤖 Auto-setup: {filename}",
                "content": base64.b64encode(json.dumps(content, indent=2).encode()).decode()
            }
            if sha: put_payload["sha"] = sha
            requests.put(file_url, headers=headers, json=put_payload)
            print(f"📄 Pushed {filename}")

    # 6. Ensure the Portfolio Site (Github Pages) is up
    manage_student_site(student_username, student_name, token, org_name)
    
    return True

def manage_student_site(username, name, token, org):
    """Ensures the student has a username.github.io repo in the organization."""
    site_repo = f"{username}.github.io"
    headers = {"Authorization": f"token {token}"}
    
    # Check if site already exists
    res = requests.get(f"https://api.github.com/repos/{org}/{site_repo}", headers=headers)
    
    if res.status_code == 404:
        print(f"🌐 Creating portfolio site for {username}...")
        url = f"https://api.github.com/repos/{org}/codequest-templates/generate"
        # We use 'codequest-templates' specifically for the site UI
        requests.post(url, headers=headers, json={
            "owner": org, 
            "name": site_repo, 
            "private": False,
            "description": f"{name}'s Coding Journey"
        })
        print(f"✅ Portfolio site queued for creation.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create-student-repo.py <username> <name> <mission_id>")
        sys.exit(1)
    
    success = create_student_repo(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
