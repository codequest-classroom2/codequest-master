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
    
    print(f"\n{'='*60}")
    print(f"📦 Starting repo creation for {student_username}...")
    print(f"{'='*60}")
    
    # Load student data
    try:
        with open(f"students/{student_username}.json", 'r') as f:
            student_data = json.load(f)
        print(f"✅ Loaded student data for {student_name}")
    except Exception as e:
        print(f"❌ Could not load student file: {e}")
        return False
    
    # Determine which template to use
    if mission_id.startswith(('html-', 'css-', 'js-')):
        template_name = "basic-web-mission"
        print(f"🎨 Using web mission template")
    else:
        template_name = "basic-python-mission"
        print(f"🐍 Using Python mission template")
    
    # Load mission data
    try:
        with open(f"missions/{mission_id}.json", 'r') as f:
            mission_data = json.load(f)
        print(f"✅ Loaded mission: {mission_data.get('title', mission_id)}")
    except Exception as e:
        print(f"❌ Could not load mission file: {e}")
        return False
    
    # Load rubric
    try:
        with open(f"rubrics/{mission_id}.json", 'r') as f:
            rubric_data = json.load(f)
        print(f"✅ Loaded rubric with {len(rubric_data.get('checks', []))} checks")
    except Exception as e:
        print(f"⚠️ Could not load rubric file: {e}")
        rubric_data = {"checks": [], "totalPoints": mission_data.get('points', 0), "passingScore": 1}
    
    # Create mission repo
    repo_name = f"{student_username}-{mission_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print(f"\n📦 Creating mission repo: {repo_name}")
    
    # Check if repo already exists
    check_url = f"https://api.github.com/repos/{org_name}/{repo_name}"
    check_response = requests.get(check_url, headers=headers)
    
    if check_response.status_code == 200:
        print(f"⚠️ Repo {repo_name} already exists! Skipping creation...")
        repo_url = check_response.json()['html_url']
    else:
        # Create repo from template
        create_url = f"https://api.github.com/repos/{org_name}/codequest-templates/generate"
        payload = {
            "owner": org_name,
            "name": repo_name,
            "description": f"{mission_data.get('title', mission_id)} for {student_name}",
            "private": False,
            "include_all_branches": False
        }
        
        response = requests.post(create_url, headers=headers, json=payload)
        
        if response.status_code != 201:
            print(f"❌ Failed to create mission repo: {response.text}")
            return False
        
        repo_data = response.json()
        repo_url = repo_data['html_url']
        print(f"✅ Mission repo created: {repo_url}")
        time.sleep(2)
    
    # Add student as collaborator
    collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
    collab_response = requests.put(collab_url, headers=headers)
    
    if collab_response.status_code == 201:
        print(f"✅ Added {student_username} as collaborator")
    elif collab_response.status_code == 204:
        print(f"✅ {student_username} is already a collaborator")
    
    # Update identity.json
    identity_content = {
        "username": student_username,
        "name": student_name,
        "xp": student_data["progress"]["xp"],
        "badges": student_data["progress"]["badges"],
        "completedMissions": student_data["progress"]["completedMissions"],
        "currentMission": mission_id
    }
    
    # Update files
    files_to_update = [
        ("identity.json", identity_content),
        ("mission.json", mission_data),
        ("rubric.json", rubric_data)
    ]
    
    for file_path, content in files_to_update:
        try:
            # Get file SHA
            get_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{file_path}"
            get_response = requests.get(get_url, headers=headers)
            
            if get_response.status_code == 200:
                sha = get_response.json()["sha"]
                
                # Update file
                update_url = get_url
                update_payload = {
                    "message": f"✨ Customize for {student_username}",
                    "content": base64.b64encode(json.dumps(content, indent=2).encode()).decode(),
                    "sha": sha
                }
                update_response = requests.put(update_url, headers=headers, json=update_payload)
                
                if update_response.status_code == 200:
                    print(f"✅ Updated {file_path}")
        except Exception as e:
            print(f"⚠️ Error updating {file_path}: {e}")
    
    # Create student's personal site
    create_student_site(student_username, student_name, token, org_name)
    
    print(f"\n{'🎉'*40}")
    print(f"🎉 SUCCESS! Created for {student_name}:")
    print(f"   📚 Mission repo: https://github.com/{org_name}/{repo_name}")
    print(f"   🌐 Personal site: https://{student_username}.github.io")
    print(f"{'🎉'*40}\n")
    
    return True

def create_student_site(student_username, student_name, token, org_name):
    """Create GitHub Pages site for student"""
    
    site_repo = f"{student_username}.github.io"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print(f"\n📦 Checking personal site: {site_repo}")
    
    # Check if site exists
    check_url = f"https://api.github.com/repos/{org_name}/{site_repo}"
    check_response = requests.get(check_url, headers=headers)
    
    if check_response.status_code == 404:
        print(f"📦 Creating personal site: {site_repo}")
        
        # Create from template
        create_url = f"https://api.github.com/repos/{org_name}/codequest-templates/generate"
        payload = {
            "owner": org_name,
            "name": site_repo,
            "description": f"{student_name}'s Coding Quest",
            "private": False,
            "include_all_branches": False
        }
        
        response = requests.post(create_url, headers=headers, json=payload)
        
        if response.status_code == 201:
            print(f"✅ Created site repo: {site_repo}")
            time.sleep(3)
            
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
                print(f"🌐 Site will be live at: https://{site_repo}")
            
            # Add student as collaborator
            collab_url = f"https://api.github.com/repos/{org_name}/{site_repo}/collaborators/{student_username}"
            requests.put(collab_url, headers=headers)
            print(f"✅ Added {student_username} as collaborator")
            
            return True
    else:
        print(f"✅ Site already exists: https://{site_repo}")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create-student-repo.py <username> <name> <mission_id>")
        print("Example: python create-student-repo.py sarah 'Sarah Chen' html-1-1")
        sys.exit(1)
    
    success = create_student_repo(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
