import re
import requests
import argparse
from urllib.parse import urlparse
import os

# Patterns to exclude test files
EXCLUDE_PATTERNS = [
    re.compile(r'.*/test[s]?/.*', re.IGNORECASE),
    re.compile(r'.*test.*', re.IGNORECASE),
    re.compile(r'.*spec.*', re.IGNORECASE),
    re.compile(r'.*_test\..*', re.IGNORECASE),
    re.compile(r'.*_spec\..*', re.IGNORECASE),
]

# Extensions considered as config files
CONFIG_EXTENSIONS = ('.yml', '.yaml', '.json', '.toml', '.xml', '.properties', '.conf', '.cfg', '.ini')

def is_test_file(path):
    return any(p.search(path) for p in EXCLUDE_PATTERNS)

def is_config_file(path):
    return path.endswith(CONFIG_EXTENSIONS)

def extract_pr_info(pr_url):
    parsed = urlparse(pr_url)
    host = parsed.netloc.lower()
    path_parts = parsed.path.strip('/').split('/')
    if 'github.com' in host:
        if len(path_parts) < 4 or path_parts[-2] != 'pull':
            raise ValueError("Invalid GitHub PR URL")
        owner, repo, _, pr_number = path_parts[:4]
        return 'github', owner, repo, pr_number
    elif 'gitlab.com' in host:
        # GitLab MR URL: https://gitlab.com/group/project/-/merge_requests/123
        if 'merge_requests' not in path_parts:
            raise ValueError("Invalid GitLab MR URL")
        # Find the index of 'merge_requests'
        mr_idx = path_parts.index('merge_requests')
        if mr_idx < 2 or mr_idx+1 >= len(path_parts):
            raise ValueError("Invalid GitLab MR URL")
        # The repo path is everything before '-/merge_requests'
        repo = path_parts[mr_idx-2]
        owner = path_parts[mr_idx-3] if mr_idx-3 >= 0 else ''
        mr_number = path_parts[mr_idx+1]
        # For group/subgroup/project, owner may be group/subgroup
        if mr_idx-3 > 0:
            owner = '/'.join(path_parts[:mr_idx-2])
        return 'gitlab', owner, repo, mr_number
    else:
        raise ValueError("Unsupported URL: Only GitHub and GitLab are supported.")


def fetch_pr_files(owner, repo, pr_number, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    all_files = []
    page = 1
    while True:
        response = requests.get(url, headers=headers, params={'page': page, 'per_page': 100})
        if response.status_code != 200:
            raise RuntimeError(f"GitHub API error: {response.status_code} {response.text}")
        files = response.json()
        if not files:
            break
        all_files.extend(files)
        page += 1
    return all_files

def fetch_mr_files_gitlab(owner, repo, mr_number, token):
    # GitLab API expects project path url-encoded as group%2Fproject
    import urllib.parse
    project_path = urllib.parse.quote(f"{owner}/{repo}", safe='')
    url = f"https://gitlab.com/api/v4/projects/{project_path}/merge_requests/{mr_number}/changes"
    headers = {
        "PRIVATE-TOKEN": token,
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise RuntimeError(f"GitLab API error: {response.status_code} {response.text}")
    data = response.json()
    files = data.get('changes', [])
    # Map to GitHub-like structure for compatibility
    file_list = []
    for f in files:
        # Count additions and deletions from the diff
        added = deleted = 0
        for line in f.get('diff', '').splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                added += 1
            elif line.startswith('-') and not line.startswith('---'):
                deleted += 1
        file_list.append({
            "filename": f["new_path"],
            "additions": added,
            "deletions": deleted,
            "changes": added + deleted
        })
    return file_list

def summarize_files(files, include_tests=False):
    total_added = 0
    total_deleted = 0
    total_changes = 0

    file_changes = []

    for file in files:
        path = file["filename"]
        if not include_tests and is_test_file(path):
            continue

        additions = file["additions"]
        deletions = file["deletions"]
        changes = file["changes"]
        net_change = additions - deletions
        is_config = is_config_file(path)

        total_added += additions
        total_deleted += deletions
        total_changes += changes

        file_changes.append({
            "path": path,
            "additions": additions,
            "deletions": deletions,
            "changes": changes,
            "net_change": net_change,
            "is_config": is_config
        })

    return total_added, total_deleted, total_changes, file_changes

def truncate_middle(path, max_length=60):
    if len(path) <= max_length:
        return path.ljust(max_length)
    else:
        part_len = (max_length - 3) // 2  # account for "..."
        return f"{path[:part_len]}...{path[-part_len:]}".ljust(max_length)

def main():
    parser = argparse.ArgumentParser(description="Summarize GitHub/GitLab PR/MR code delta excluding test files.")
    parser.add_argument("pr_url", help="GitHub Pull Request or GitLab Merge Request URL")
    parser.add_argument("--token", help="GitHub or GitLab Token (or set GITHUB_TOKEN or GITLAB_TOKEN env var)")
    parser.add_argument("--include-tests", action="store_true", help="Include test files in the summary")    
    parser.add_argument("--show-files", action="store_true", help="Show per-file changes in the output")
    parser.add_argument("--truncate-paths", action="store_true", help="Truncate long file paths in file changes output")
    args = parser.parse_args()
    # Get platform-specific tokens
    github_token = args.token or os.getenv("GITHUB_TOKEN")
    gitlab_token = args.token or os.getenv("GITLAB_TOKEN")

    try:
        platform, owner, repo, pr_number = extract_pr_info(args.pr_url)
        if platform == 'github':
            if not github_token:
                print("GitHub token is required. Pass via --token or set GITHUB_TOKEN.")
                return
            files = fetch_pr_files(owner, repo, pr_number, github_token)
        elif platform == 'gitlab':
            if not gitlab_token:
                print("GitLab token is required. Pass via --token or set GITLAB_TOKEN.")
                return
            files = fetch_mr_files_gitlab(owner, repo, pr_number, gitlab_token)
        else:
            raise ValueError("Unsupported platform")
        added, deleted, changed, file_changes = summarize_files(files, include_tests=args.include_tests)

        print("\nCode Delta Summary{}:".format(" (including test files)" if args.include_tests else " (excluding test files)"))
        print(f"Lines added:     {added}")
        print(f"Lines deleted:   {deleted}")
        print(f"Total changes:   {changed}")

        if args.show_files:
            print("\nFile Changes ({}):".format("all files" if args.include_tests else "non-test files"))
            print(f"{'File':60} {'+Add':>6} {'-Del':>6} {'ΔChange':>8} {'±Net':>6} {'Config?':>8}")
            print("-" * 100)
            for f in file_changes:
                if args.truncate_paths:
                    print(f"{truncate_middle(f['path']):60} {f['additions']:6} {f['deletions']:6} {f['changes']:8} {f['net_change']:6} {'Yes' if f['is_config'] else 'No':>8}")
                else:
                    print(f"{f['path'][-60:]:<60} {f['additions']:6} {f['deletions']:6} {f['changes']:8} {f['net_change']:6} {'Yes' if f['is_config'] else 'No':>8}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
