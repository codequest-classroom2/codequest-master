import os
import json
import requests
import base64
import sys
import time
from nacl import encoding, public as nacl_public

def add_secret_to_repo(token, org_name, repo_name, headers):
    """Adds GH_TOKEN secret to a repo so review.py can sync progress."""
    # Get repo public key
    pk_res = requests.get(
        f"https://api.github.com/repos/{org_name}/{repo_name}/actions/secrets/public-key",
        headers=headers
    )
    if pk_res.status_code != 200:
        print(f"   ⚠️ Could not get repo public key: {pk_res.status_code}")
        return
    pk_data = pk_res.json()
    pub_key_bytes = base64.b64decode(pk_data['key'])
    sealed_box = nacl_public.SealedBox(nacl_public.PublicKey(pub_key_bytes))
    encrypted = base64.b64encode(sealed_box.encrypt(token.encode())).decode()
    res = requests.put(
        f"https://api.github.com/repos/{org_name}/{repo_name}/actions/secrets/GH_TOKEN",
        headers=headers,
        json={"encrypted_value": encrypted, "key_id": pk_data['key_id']}
    )
    print(f"   {'✅' if res.status_code in [201, 204] else '❌'} GH_TOKEN secret ({res.status_code})")

def build_readme(student_name, mission_id, repo_name, mission_data, headers, org_name):
    """Fetches README template and replaces all {{placeholders}}.

    Tries mission-specific template first (basic-web-mission/README.md),
    then falls back to the root README.md.
    """
    readme = None
    candidates = ["basic-web-mission/README.md", "README.md"]
    for path in candidates:
        res = requests.get(
            f"https://api.github.com/repos/{org_name}/codequest-templates/contents/{path}",
            headers=headers
        )
        if res.status_code == 200:
            readme = base64.b64decode(res.json()['content']).decode('utf-8')
            print(f"   📄 README template: {path}")
            break
        print(f"   ℹ️ {path} not found ({res.status_code}), trying next...")

    if readme is None:
        print(f"⚠️ Could not fetch any README template, using fallback")
        readme = f"# 🚀 Mission: {mission_data['title']}\n\nHi {student_name}!"
        return readme

    # Replace simple placeholders
    replacements = {
        "{{mission.title}}":       mission_data.get('title', mission_id),
        "{{mission.points}}":      str(mission_data.get('points', 0)),
        "{{mission.badge}}":       mission_data.get('badge', ''),
        "{{mission.level}}":       mission_data.get('level', ''),
        "{{mission.description}}": mission_data.get('description', ''),
        "{{mission.instructions}}":mission_data.get('instructions', mission_data.get('description', '')),
        "{{student.name}}":        student_name,
        "{{repo-name}}":           repo_name,
    }
    for placeholder, value in replacements.items():
        readme = readme.replace(placeholder, value)

    # Replace {{#each mission.requirements}}...{{/each}} loop
    import re
    def expand_requirements(match):
        template_line = match.group(1)
        lines = [template_line.replace("{{this}}", req) for req in mission_data.get('requirements', [])]
        return "\n".join(lines)
    readme = re.sub(r'\{\{#each mission\.requirements\}\}(.*?)\{\{/each\}\}', expand_requirements, readme, flags=re.DOTALL)

    return readme

def create_student_repo(student_username, student_name, mission_id):
    """Generates the mission repo, custom README, and ensures the portfolio site exists."""
    
    print("\n" + "="*60)
    print("🔧 CREATE-STUDENT-REPO.PY STARTED")
    print("="*60)
    
    token = os.environ.get("GH_TOKEN")
    org_name = "codequest-classroom2"
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
        "private": False
    }
    
    response = requests.post(create_url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print(f"✅ Repo created: {repo_name}")
        time.sleep(5) # Buffer for GitHub
        
        # 4. Add student as collaborator with Write access
        print(f"\n👤 Step 2: Adding {student_username} as collaborator (Write access)...")
        collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
        collab_res = requests.put(collab_url, headers=headers, json={"permission": "push"})
        if collab_res.status_code in [201, 204]:
            print(f"✅ {student_username} added as collaborator")
        else:
            print(f"❌ Failed to add collaborator ({collab_res.status_code}): {collab_res.text}")

        # 4b. Add GH_TOKEN secret to the mission repo so review.py can sync progress
        print(f"\n🔑 Step 2b: Adding GH_TOKEN secret to {repo_name}...")
        add_secret_to_repo(token, org_name, repo_name, headers)

        # 5. Push Mission Files
        print(f"\n📝 Step 3: Pushing mission files...")
        progress = student_data.get("progress", {})
        identity_content = {
            "username": student_username, "name": student_name,
            "xp": progress.get("xp", 0),
            "currentMission": mission_id,
            "completedMissions": progress.get("completedMissions", []),
            "unlockedMissions": progress.get("unlockedMissions", [])
        }
        # Explicitly replace any template placeholders in the serialised JSON so
        # the correct values always reach the student repo even if the template
        # file still contains the raw {{…}} strings.
        identity_json = (
            json.dumps(identity_content, indent=2)
            .replace("{{student_username}}", student_username)
            .replace("{{student_name}}", student_name)
            .replace("{{mission_id}}", mission_id)
        )

        # Fetch githubClientId and oauthCallbackUrl from the canonical template so
        # every student repo always gets the current values without manual edits.
        template_res = requests.get(
            f"https://api.github.com/repos/{org_name}/codequest-templates/contents/mission.json",
            headers=headers
        )
        if template_res.status_code == 200:
            template_mission = json.loads(base64.b64decode(template_res.json()['content']))
            mission_data['githubClientId']   = template_mission.get('githubClientId', '')
            mission_data['oauthCallbackUrl'] = template_mission.get('oauthCallbackUrl', '')
            print(f"   ✅ Merged githubClientId + oauthCallbackUrl from template mission.json")
        else:
            print(f"   ⚠️ Could not fetch template mission.json ({template_res.status_code}) — githubClientId may be missing")

        # Stamp the actual repo coordinates so submit.html can find the right repo.
        mission_data['repoOwner'] = org_name   # codequest-classroom2
        mission_data['repoName']  = repo_name  # e.g. alice-basic-web-mission

        # Fetch README template and fill placeholders
        readme_content = build_readme(student_name, mission_id, repo_name, mission_data, headers, org_name)

        files = [
            ("identity.json", identity_json),
            ("mission.json", json.dumps(mission_data, indent=2)),
            ("rubric.json", json.dumps(rubric_data, indent=2)),
            ("README.md", readme_content)
        ]

        for filename, content in files:
            file_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{filename}"
            put_payload = {
                "message": f"🤖 Setup {filename}",
                "content": base64.b64encode(content.encode()).decode()
            }
            # GET existing file sha (required by GitHub API to update an existing file).
            # Retry up to 5 times with backoff — newly generated repos can take a few
            # seconds before their files are accessible via the API.
            sha_found = False
            for attempt in range(5):
                existing = requests.get(file_url, headers=headers)
                if existing.status_code == 200:
                    put_payload["sha"] = existing.json().get("sha")
                    sha_found = True
                    break
                if attempt < 4:
                    time.sleep(3)
            if not sha_found:
                print(f"   ⚠️ {filename}: could not fetch existing sha after retries, attempting create")
            res = requests.put(file_url, headers=headers, json=put_payload)
            print(f"   {'✅' if res.status_code in [200, 201] else '❌'} {filename} ({res.status_code})")

        # Fetch submit.html fresh from the template repo so every student always
        # gets the latest version (never cached or hardcoded).
        print(f"\n   📄 Fetching latest submit.html from codequest-templates...")
        submit_template_res = requests.get(
            f"https://api.github.com/repos/{org_name}/codequest-templates/contents/basic-web-mission/submit.html",
            headers=headers
        )
        if submit_template_res.status_code == 200:
            submit_b64 = submit_template_res.json()['content'].replace('\n', '')
            submit_file_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/basic-web-mission/submit.html"
            submit_put_payload = {
                "message": "🤖 Setup basic-web-mission/submit.html",
                "content": submit_b64
            }
            existing_submit = requests.get(submit_file_url, headers=headers)
            if existing_submit.status_code == 200:
                submit_put_payload["sha"] = existing_submit.json().get("sha")
            submit_res = requests.put(submit_file_url, headers=headers, json=submit_put_payload)
            print(f"   {'✅' if submit_res.status_code in [200, 201] else '❌'} basic-web-mission/submit.html ({submit_res.status_code})")
        else:
            print(f"   ⚠️ Could not fetch submit.html from template repo ({submit_template_res.status_code})")

        # 6. Enable GitHub Pages so the submit.html button in README actually works.
        #    The coding environment lives at:
        #    https://codequest-classroom2.github.io/{repo_name}/basic-web-mission/submit.html
        print(f"\n🌐 Step 4: Enabling GitHub Pages for {repo_name}...")
        pages_res = requests.post(
            f"https://api.github.com/repos/{org_name}/{repo_name}/pages",
            headers=headers,
            json={"source": {"branch": "main", "path": "/"}}
        )
        if pages_res.status_code in [201, 409]:   # 409 = already enabled
            print(f"   ✅ GitHub Pages enabled → https://codequest-classroom2.github.io/{repo_name}/")
        else:
            print(f"   ⚠️ Pages enable returned {pages_res.status_code}: {pages_res.text}")

        # 7. Create sibling missions in the same level (pointsToUnlock: 0)
        create_level_sibling_repos(student_username, student_name, mission_id, headers, org_name, token)

        # 8. Create Portfolio Site
        create_portfolio_site(student_username, student_name, mission_id, headers, org_name)

        print(f"\n✅ SETUP COMPLETE: https://github.com/{org_name}/{repo_name}")
        return True
    else:
        print(f"❌ FAIL: {response.status_code} - {response.text}")
        return False

def create_level_sibling_repos(student_username, student_name, mission_id, headers, org_name, token):
    """Creates all other missions in the same level if that level has pointsToUnlock: 0."""
    res = requests.get(
        f"https://api.github.com/repos/{org_name}/codequest-master/contents/paths/web-dev.json",
        headers=headers
    )
    if res.status_code != 200:
        print(f"⚠️ Could not fetch web-dev.json: {res.status_code}")
        return

    path_config = json.loads(base64.b64decode(res.json()['content']))
    for level in path_config.get('levels', []):
        if level.get('pointsToUnlock', 1) != 0:
            continue
        mission_ids = [m['id'] if isinstance(m, dict) else m for m in level.get('missions', [])]
        if mission_id not in mission_ids:
            continue
        # Found the level — create repos for all other missions in it
        for sibling_id in mission_ids:
            if sibling_id == mission_id:
                continue
            print(f"\n🔗 Creating sibling mission repo: {sibling_id}")
            create_student_repo(student_username, student_name, sibling_id)

def create_portfolio_site(student_username, student_name, mission_id, headers, org_name):
    """Creates codequest-classroom2/{username} as a public GitHub Pages portfolio site."""
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
            raw = base64.b64decode(res.json()['content'])
            files_to_push.append((filename, base64.b64encode(raw).decode()))
        else:
            print(f"⚠️ Could not fetch template {filename}: {res.status_code}")

    # Fetch web-dev.json from master repo and include in portfolio (makes it publicly accessible)
    webdev_res = requests.get(
        f"https://api.github.com/repos/{org_name}/codequest-master/contents/paths/web-dev.json",
        headers=headers
    )
    if webdev_res.status_code == 200:
        raw = base64.b64decode(webdev_res.json()['content'])
        files_to_push.append(("web-dev.json", base64.b64encode(raw).decode()))
    else:
        print(f"⚠️ Could not fetch web-dev.json: {webdev_res.status_code}")

    # config.json with the real username so script.js knows who this is
    config_content = json.dumps({"username": student_username}, indent=2)
    files_to_push.append(("config.json", base64.b64encode(config_content.encode()).decode()))

    # progress.json — initial record so the site loads before the student passes anything
    progress_content = json.dumps({
        "student": {"name": student_name, "username": student_username},
        "progress": {"xp": 0, "completedMissions": [], "unlockedMissions": [mission_id], "badges": [], "currentMission": mission_id}
    }, indent=2)
    files_to_push.append(("progress.json", base64.b64encode(progress_content.encode()).decode()))

    # Push all files (GET sha first if file already exists)
    # progress.json is NEVER overwritten — review.py owns it after initial creation
    for filename, content in files_to_push:
        file_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{filename}"
        existing = requests.get(file_url, headers=headers)
        if filename == "progress.json" and existing.status_code == 200:
            print(f"   ⏭️ progress.json already exists, skipping to preserve student progress")
            continue
        put_payload = {"message": f"🤖 Setup {filename}", "content": content}
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
