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
    
    # Determine which template to use based on mission_id
    if mission_id.startswith(('html-', 'css-', 'js-')):
        template_name = "basic-web-mission"
        print(f"🎨 Using web mission template: {template_name}")
    else:
        template_name = "basic-python-mission"
        print(f"🐍 Using Python mission template: {template_name}")
    
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
        # Fallback rubric structure
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
        # FIX: Use the specific template_name determined above
        create_url = f"https://api.github.com/repos/{org_name}/{template_name}/generate"
        
        payload = {
            "owner": org_name,
            "name": repo_name,
            "description": f"{mission_data.get('title', mission_id)} for {student_name}",
            "private": True,  # FIX: Set to True so other students can't see it
            "include_all_branches": False
        }
        
        response = requests.post(create_url, headers=headers, json=payload)
        
        if response.status_code != 201:
            print(f"❌ Failed to create mission repo from {template_name}: {response.text}")
            return False
        
        repo_data = response.json()
        repo_url = repo_data['html_url']
        print(f"✅ Mission repo created: {repo_url}")
        # Wait a moment for GitHub to finish background provisioning
        time.sleep(3)
    
    # Add student as collaborator
    collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
    # Setting permission to 'push' (Write access)
    collab_payload = {"permission": "push"}
    collab_response = requests.put(collab_url, headers=headers, json=collab_payload)
    
    if collab_response.status_code == 201:
        print(f"✅ Invited {student_username} as collaborator")
    elif collab_response.status_code == 204:
        print(f"✅ {student_username} is already a collaborator")
    
    # Update identity.json with student-specific context
    identity_content = {
        "username": student_username,
        "name": student_name,
        "xp": student_data.get("progress", {}).get("xp", 0),
        "badges": student_data.get("progress", {}).get("badges", []),
        "completedMissions": student_data.get("progress", {}).get("completedMissions", []),
        "currentMission": mission_id
    }
    
    # Files to push into the new repo
    files_to_update = [
        ("identity.json", identity_content),
        ("mission.json", mission_data),
        ("rubric.json", rubric_data)
    ]
    
    for file_path, content in files_to_update:
        try:
            # Get file SHA (required for updates)
            get_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{file_path}"
            get_response = requests.get(get_url, headers=headers)
            
            sha = None
            if get_response.status_code == 200:
                sha = get_response.json()["sha"]
                
            update_payload = {
                "message": f"✨ Customize {file_path} for {student_username}",
                "content": base64.b64encode(json.dumps(content, indent=2).encode()).decode(),
            }
            if sha:
                update_payload["sha"] = sha
                
            update_response = requests.put(get_url, headers=headers, json=update_payload)
            
            if update_response.status_code in [200, 201]:
                print(f"✅ Updated {file_path}")
        except Exception as e:
            print(f"⚠️ Error updating {file_path}: {e}")
    
    # Handle the student's personal site
    create_student_site(student_username, student_name, token, org_name)
    
    print(f"\n{'🎉'*30}")
    print(f"SUCCESS! Deployment complete for {student_name}:")
    print(f"   📚 Mission repo: https://github.com/{org_name}/{repo_name}")
    print(f"   🌐 Personal site: https://{org_name}.github.io/{student_username}.github.io")
    print(f"{'🎉'*30}\n")
    
    return True

def create_student_site(student_username, student_name, token, org_name):
    """Create GitHub Pages site for student"""
    
    site_repo = f"{student_username}.github.io"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Using the general templates repo for the personal site
    site_template = "codequest-templates" 
    
    print(f"\n📦 Checking personal site: {site_repo}")
    
    check_url = f"https://api.github.com/repos/{org_name}/{site_repo}"
    check_response = requests.get(check_url, headers=headers)
    
    if check_response.status_code == 404:
        print(f"📦 Creating personal site from template: {site_template}")
        
        create_url = f"https://api.github.com/repos/{org_name}/{site_template}/generate"
        payload = {
            "owner": org_name,
            "name": site_repo,
            "description": f"{student_name}'s Coding Quest",
            "private": False, # Pages usually need public or Pro orgs for private
            "include_all_branches": False
        }
        
        response = requests.post(create_url, headers=headers, json=payload)
        
        if response.status_code == 201:
            print(f"✅ Created site repo: {site_repo}")
            time.sleep(5)
            
            # Enable GitHub Pages
            pages_url = f"https://api.github.com/repos/{org_name}/{site_repo}/pages"
            pages_payload = {
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }
            requests.post(pages_url, headers=headers, json=pages_payload)
            
            # Add student as collaborator
            collab_url = f"https://api.github.com/repos/{org_name}/{site_repo}/collaborators/{student_username}"
            requests.put(collab_url, headers=headers)
            print(f"✅ Added {student_username} as collaborator to site")
            
            return True
    else:
        print(f"✅ Site already exists for {student_username}")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create-student-repo.py <username> <name> <mission_id>")
        sys.exit(1)
    
    success = create_student_repo(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
