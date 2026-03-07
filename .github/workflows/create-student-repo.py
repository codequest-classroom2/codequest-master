import os
import json
import requests
import base64
import sys
from pathlib import Path

def create_student_repo(student_username, student_name, mission_id):
    """Create a personalized mission repo for a student"""
    
    # GitHub token from secrets
    token = os.environ.get("GH_TOKEN")
    org_name = "codequest-classroom"
    
    print(f"📦 Starting repo creation for {student_username}...")
    
    # Load student data
    student_file = f"students/{student_username}.json"
    try:
        with open(student_file, 'r') as f:
            student_data = json.load(f)
        print(f"✅ Loaded student data")
    except Exception as e:
        print(f"❌ Could not load student file: {e}")
        return False
    
    # Load mission data
    mission_file = f"missions/{mission_id}.json"
    try:
        with open(mission_file, 'r') as f:
            mission_data = json.load(f)
        print(f"✅ Loaded mission data")
    except Exception as e:
        print(f"❌ Could not load mission file: {e}")
        return False
    
    # Load rubric
    mission_num = mission_id.split('-')[-1]
    rubric_file = f"rubrics/mission-{mission_num}.json"
    try:
        with open(rubric_file, 'r') as f:
            rubric_data = json.load(f)
        print(f"✅ Loaded rubric data")
    except Exception as e:
        print(f"❌ Could not load rubric file: {e}")
        rubric_data = {"requirements": [], "xpReward": 0, "badge": ""}
    
    # Create mission repo
    repo_name = f"{student_username}-{mission_id}"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print(f"📦 Creating mission repo: {repo_name}")
    
    # Create repo from template
    create_url = f"https://api.github.com/repos/{org_name}/codequest-templates/generate"
    payload = {
        "owner": org_name,
        "name": repo_name,
        "description": f"CodeQuest mission for {student_name}",
        "private": True,
        "include_all_branches": False
    }
    
    response = requests.post(create_url, headers=headers, json=payload)
    
    if response.status_code != 201:
        print(f"❌ Failed to create mission repo: {response.text}")
        return False
    
    repo_data = response.json()
    repo_url = repo_data['html_url']
    print(f"✅ Mission repo created: {repo_url}")
    
    # Add student as collaborator
    collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
    collab_response = requests.put(collab_url, headers=headers)
    
    if collab_response.status_code == 201:
        print(f"✅ Added {student_username} as collaborator to mission repo")
    
    # Customize mission repo with student data
    files_to_update = [
        ("identity.json", json.dumps({
            "name": student_data["student"]["name"],
            "xp": student_data["progress"]["xp"],
            "badges": student_data["progress"]["badges"],
            "completedMissions": student_data["progress"]["completedMissions"],
            "currentMission": student_data["progress"]["currentMission"]
        }, indent=2)),
        ("mission.json", json.dumps(mission_data, indent=2)),
        ("rubric.json", json.dumps(rubric_data, indent=2)),
        ("README.md", f"# 🚀 {mission_data['title']}\n\n## Hey {student_name}!\n\n{mission_data['description']}\n\n## Points: {mission_data['points']}\n\nEdit `submissions/solution.py` to complete the mission.")
    ]
    
    for file_path, content in files_to_update:
        try:
            get_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{file_path}"
            get_response = requests.get(get_url, headers=headers)
            
            if get_response.status_code == 200:
                sha = get_response.json()["sha"]
                
                update_url = get_url
                update_payload = {
                    "message": f"✨ Customize for {student_username}",
                    "content": base64.b64encode(content.encode()).decode(),
                    "sha": sha
                }
                update_response = requests.put(update_url, headers=headers, json=update_payload)
                
                if update_response.status_code == 200:
                    print(f"✅ Updated {file_path} in mission repo")
        except Exception as e:
            print(f"⚠️ Error updating {file_path}: {e}")
    
    # Create student's personal GitHub Pages site
    create_student_site(student_username, student_name, token, org_name)
    
    print(f"\n🎉 Success! Created for {student_name}:")
    print(f"   📚 Mission repo: https://github.com/{org_name}/{repo_name}")
    print(f"   🌐 Personal site: https://{student_username}.github.io")
    
    return True

def create_student_site(student_username, student_name, token, org_name):
    """Create GitHub Pages site for student"""
    
    site_repo = f"{student_username}.github.io"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print(f"📦 Creating personal site: {site_repo}")
    
    # Check if site already exists
    check_url = f"https://api.github.com/repos/{org_name}/{site_repo}"
    check = requests.get(check_url, headers=headers)
    
    if check.status_code == 404:
        # Create from template
        create_url = "https://api.github.com/repos/{org_name}/codequest-templates/generate"
        payload = {
            "owner": org_name,
            "name": site_repo,
            "description": f"{student_name}'s Coding Quest - View your skill tree!",
            "private": False,  # GitHub Pages must be public
            "include_all_branches": False
        }
        
        response = requests.post(create_url, headers=headers, json=payload)
        
        if response.status_code == 201:
            print(f"✅ Created site repo: {site_repo}")
            
            # Wait a moment for repo to be ready
            import time
            time.sleep(2)
            
            # Enable GitHub Pages
            pages_url = f"https://api.github.com/repos/{org_name}/{site_repo}/pages"
            pages_payload = {
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }
            pages_response = requests.post(pages_url, headers=headers, json=pages_payload)
            
            if pages_response.status_code in [201, 204]:
                print(f"✅ GitHub Pages enabled for {site_repo}")
                print(f"🌐 Site will be live soon at: https://{site_repo}")
            else:
                print(f"⚠️ Pages may need manual enable: {pages_response.status_code}")
            
            return True
        else:
            print(f"❌ Failed to create site: {response.text}")
            return False
    else:
        print(f"✅ Site already exists: https://{site_repo}")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create-student-repo.py <student_username> <student_name> <mission_id>")
        sys.exit(1)
    
    student_username = sys.argv[1]
    student_name = sys.argv[2]
    mission_id = sys.argv[3]
    
    success = create_student_repo(student_username, student_name, mission_id)
    if not success:
        sys.exit(1)
