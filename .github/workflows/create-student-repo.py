import os
import json
import requests
import base64
import sys
import time

def create_student_repo(student_username, student_name, mission_id):
    """Create a personalized mission repo for a student"""
    
    token = os.environ.get("GH_TOKEN")
    org_name = "codequest-classroom"
    
    print(f"\n📦 Starting repo creation for {student_username}...")
    
    # Determine which template to use
    if mission_id.startswith(('html-', 'css-', 'js-')):
        template_name = "basic-web-mission"
    else:
        template_name = "basic-python-mission"
    
    # Load mission data (for identity/mission/rubric files)
    with open(f"missions/{mission_id}.json") as f:
        mission_data = json.load(f)
    
    with open(f"rubrics/{mission_id}.json") as f:
        rubric_data = json.load(f)
    
    # Create repo from template
    repo_name = f"{student_username}-{mission_id}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    create_url = f"https://api.github.com/repos/{org_name}/codequest-templates/generate"
    payload = {
        "owner": org_name,
        "name": repo_name,
        "description": f"{mission_data['title']} for {student_name}",
        "private": False
    }
    
    response = requests.post(create_url, headers=headers, json=payload)
    if response.status_code != 201:
        print(f"❌ Failed: {response.text}")
        return False
    
    print(f"✅ Repo created: {response.json()['html_url']}")
    time.sleep(2)
    
    # Add student as collaborator
    collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
    requests.put(collab_url, headers=headers)
    
    # Update ONLY the files that need student data
    files_to_update = [
        ("identity.json", {
            "username": student_username,
            "name": student_name,
            "xp": 0,
            "badges": [],
            "completedMissions": [],
            "currentMission": mission_id
        }),
        ("mission.json", mission_data),
        ("rubric.json", rubric_data)
    ]
    
    for file_path, content in files_to_update:
        # Get file SHA
        get_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{file_path}"
        sha = requests.get(get_url, headers=headers).json()["sha"]
        
        # Update file
        update_url = get_url
        update_payload = {
            "message": f"✨ Customize for {student_username}",
            "content": base64.b64encode(json.dumps(content, indent=2).encode()).decode(),
            "sha": sha
        }
        requests.put(update_url, headers=headers, json=update_payload)
        print(f"✅ Updated {file_path}")
    
    # Create personal site
    create_student_site(student_username, student_name, token, org_name)
    
    return True

def create_student_site(student_username, student_name, token, org_name):
    """Create GitHub Pages site for student"""
    
    site_repo = f"{student_username}.github.io"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    # Check if exists
    check_url = f"https://api.github.com/repos/{org_name}/{site_repo}"
    if requests.get(check_url, headers=headers).status_code == 404:
        # Create from template
        create_url = f"https://api.github.com/repos/{org_name}/codequest-templates/generate"
        payload = {
            "owner": org_name,
            "name": site_repo,
            "description": f"{student_name}'s Coding Quest",
            "private": False
        }
        response = requests.post(create_url, headers=headers, json=payload)
        
        if response.status_code == 201:
            print(f"✅ Created site: https://{site_repo}")
            time.sleep(2)
            
            # Enable GitHub Pages
            pages_url = f"https://api.github.com/repos/{org_name}/{site_repo}/pages"
            requests.post(pages_url, headers=headers, json={"source": {"branch": "main"}})
            
            # Add collaborator
            collab_url = f"https://api.github.com/repos/{org_name}/{site_repo}/collaborators/{student_username}"
            requests.put(collab_url, headers=headers)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create-student-repo.py <username> <name> <mission_id>")
        sys.exit(1)
    
    success = create_student_repo(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
