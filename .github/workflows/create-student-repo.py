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
    
    # 1. Load Data from Master Repo folders
    print(f"\n📁 Loading config files for {student_username}...")
    try:
        student_path = f"students/{student_username}.json"
        mission_path = f"missions/{mission_id}.json"
        rubric_path = f"rubrics/{mission_id}.json"
        
        print(f"   Looking for: {student_path}")
        with open(student_path, 'r') as f:
            student_data = json.load(f)
        print(f"   ✅ Loaded student data")
        
        print(f"   Looking for: {mission_path}")
        with open(mission_path, 'r') as f:
            mission_data = json.load(f)
        print(f"   ✅ Loaded mission: {mission_data.get('title')}")
        
        print(f"   Looking for: {rubric_path}")
        with open(rubric_path, 'r') as f:
            rubric_data = json.load(f)
        print(f"   ✅ Loaded rubric with {len(rubric_data.get('checks', []))} checks")
        
    except FileNotFoundError as e:
        print(f"❌ Missing config file: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        return False

    # 2. Identify Template
    template_name = mission_data.get("template", "basic-web-mission")
    repo_name = f"{student_username}-{mission_id}"
    template_repo_name = "codequest-templates"  # THIS IS THE FIX!
    
    print(f"\n📋 Configuration:")
    print(f"   Student: {student_username} ({student_name})")
    print(f"   Mission: {mission_id}")
    print(f"   Template folder: {template_name}")
    print(f"   Template repo: {template_repo_name}")
    print(f"   New repo name: {repo_name}")
    
    # 3. Generate Private Repo from TEMPLATE REPO
    print(f"\n🛠️ Step 1: Creating {repo_name} from {template_repo_name}/{template_name}...")
    
    create_url = f"https://api.github.com/repos/{org_name}/{template_repo_name}/generate"
    print(f"   URL: {create_url}")
    
    payload = {
        "owner": org_name,
        "name": repo_name,
        "description": mission_data.get("description", "CodeQuest Mission"),
        "private": True
    }
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(create_url, headers=headers, json=payload)
    print(f"   Response status: {response.status_code}")
    
    if response.status_code == 201:
        repo_data = response.json()
        repo_url = repo_data.get('html_url')
        print(f"   ✅ Repo created successfully!")
        print(f"   📍 URL: {repo_url}")
        
        print(f"\n⏱️  Waiting 5 seconds for GitHub to provision the repo...")
        time.sleep(5)
        
        # 4. Invite Student as Collaborator
        print(f"\n📧 Step 2: Inviting {student_username} to the repo...")
        
        # Method 1: Try invitations endpoint (best for emails)
        invite_url = f"https://api.github.com/repos/{org_name}/{repo_name}/invitations"
        print(f"   URL: {invite_url}")
        
        invite_response = requests.post(
            invite_url, 
            headers=headers, 
            json={"invitee": student_username}
        )
        print(f"   Response status: {invite_response.status_code}")
        
        if invite_response.status_code == 201:
            print(f"   ✅ Invitation email sent to {student_username}!")
            invite_data = invite_response.json()
            print(f"   📧 Invitation URL: {invite_data.get('html_url', 'N/A')}")
        else:
            print(f"   ⚠️ Invitation endpoint failed ({invite_response.status_code})")
            print(f"   Response: {invite_response.text}")
            
            # Method 2: Fallback to collaborator endpoint
            print(f"   🔄 Trying collaborator endpoint as fallback...")
            collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
            collab_response = requests.put(
                collab_url, 
                headers=headers, 
                json={"permission": "push"}
            )
            print(f"   Response status: {collab_response.status_code}")
            
            if collab_response.status_code == 201:
                print(f"   ✅ Added {student_username} as collaborator (email should be sent)")
            elif collab_response.status_code == 204:
                print(f"   ✅ {student_username} is already a collaborator (no email sent)")
            else:
                print(f"   ❌ Failed to add collaborator: {collab_response.status_code}")
                print(f"   Response: {collab_response.text}")
        
        # 5. Build Dynamic Files
        print(f"\n📝 Step 3: Creating mission files...")
        
        # Create Identity content
        identity_content = {
            "username": student_username,
            "name": student_name,
            "xp": student_data.get("progress", {}).get("xp", 0),
            "completedMissions": student_data.get("progress", {}).get("completedMissions", []),
            "currentMission": mission_id,
            "badges": student_data.get("progress", {}).get("badges", [])
        }
        print(f"   ✅ Identity data prepared")

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
        readme_content += f"\n🔗 **Your Mission Repo**: https://github.com/{org_name}/{repo_name}"
        print(f"   ✅ README content prepared")

        # Push files to new Repo
        files = [
            ("identity.json", json.dumps(identity_content, indent=2)),
            ("mission.json", json.dumps(mission_data, indent=2)),
            ("rubric.json", json.dumps(rubric_data, indent=2)),
            ("README.md", readme_content)
        ]

        files_pushed = 0
        files_failed = 0
        
        for filename, content in files:
            print(f"   📄 Pushing {filename}...")
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
                print(f"      ✅ {filename} uploaded successfully")
                files_pushed += 1
            else:
                print(f"      ❌ Failed to upload {filename}: {put_response.status_code}")
                print(f"      Response: {put_response.text}")
                files_failed += 1

        print(f"\n   📊 File upload summary: {files_pushed} succeeded, {files_failed} failed")
        
        # 6. Remove student from template repos (optional cleanup)
        print(f"\n🧹 Step 4: Cleaning up template access...")
        try:
            # Try to remove from web template
            web_remove_url = f"https://api.github.com/repos/{org_name}/basic-web-mission/collaborators/{student_username}"
            web_remove = requests.delete(web_remove_url, headers=headers)
            print(f"   Web template cleanup: {web_remove.status_code}")
        except:
            pass
        
        print(f"\n" + "="*60)
        print(f"✅ SUCCESS! All steps completed for {student_name}")
        print(f"   📚 Mission repo: https://github.com/{org_name}/{repo_name}")
        print(f"   🌐 Personal site: https://{student_username}.github.io")
        print(f"="*60 + "\n")
        
    else:
        print(f"\n❌ REPO CREATION FAILED: {response.status_code}")
        print(f"💬 Error Msg: {response.text}")
        
        # Provide helpful debug info
        if response.status_code == 404:
            print("\n🔍 DEBUG TIPS:")
            print("   1. Check if template repo exists:")
            print(f"      https://github.com/{org_name}/codequest-templates")
            print("   2. Verify it's marked as a template repository")
            print("   (Settings → Template repository)")
            print("   3. Check if template folder exists inside:")
            print(f"      https://github.com/{org_name}/codequest-templates/tree/main/{template_name}")
        elif response.status_code == 403:
            print("\n🔍 DEBUG TIPS:")
            print("   - Token may lack 'repo' scope")
            print("   - Check organization permissions")
        
        return False

    # 7. Ensure Student Site is up (don't fail if this doesn't work)
    try:
        ensure_portfolio_site(student_username, student_name, token, org_name)
    except Exception as e:
        print(f"⚠️ Portfolio site creation skipped: {e}")
        
    return True

def ensure_portfolio_site(username, name, token, org):
    """Create GitHub Pages site for student if it doesn't exist"""
    site_repo = f"{username}.github.io"
    headers = {"Authorization": f"token {token}"}
    
    print(f"\n🌐 Step 5: Checking portfolio site: {site_repo}")
    
    check = requests.get(f"https://api.github.com/repos/{org}/{site_repo}", headers=headers)
    
    if check.status_code == 404:
        print(f"   📦 Creating portfolio site...")
        url = f"https://api.github.com/repos/{org}/codequest-templates/generate"
        payload = {
            "owner": org,
            "name": site_repo,
            "description": f"{name}'s Coding Quest",
            "private": False
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"   ✅ Portfolio site created: https://{site_repo}")
            
            # Add student as collaborator
            collab_url = f"https://api.github.com/repos/{org}/{site_repo}/collaborators/{username}"
            requests.put(collab_url, headers=headers)
        else:
            print(f"   ⚠️ Portfolio site creation failed: {response.status_code}")
    else:
        print(f"   ✅ Portfolio site already exists: https://{site_repo}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create-student-repo.py <username> <name> <mission_id>")
        print("Example: python create-student-repo.py sarah 'Sarah Chen' html-1-1")
        sys.exit(1)
    
    print(f"\n🚀 Script called with arguments:")
    print(f"   Username: {sys.argv[1]}")
    print(f"   Name: {sys.argv[2]}")
    print(f"   Mission: {sys.argv[3]}")
    
    success = create_student_repo(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
