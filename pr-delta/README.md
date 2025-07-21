# GitHub/GitLab PR/MR Delta Summary Script

## Summary

This script summarizes the code changes (delta) in a GitHub Pull Request (PR) or GitLab Merge Request (MR). It fetches the list of changed files, counts lines added and deleted, and provides an option to exclude test files from the summary. The script can also display per-file change details and highlight configuration files.

## Purpose

- Quickly assess the impact of a PR/MR by counting lines added, deleted, and changed.
- Optionally exclude test files to focus on production code changes.
- Identify configuration file changes.
- Works with both GitHub and GitLab platforms.

## Usage

### Prerequisites

- Python 3.9+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Authentication

- For GitHub: Set the `GITHUB_TOKEN` environment variable or use `--token`.
- For GitLab: Set the `GITLAB_TOKEN` environment variable or use `--token`.
- If `--token` is provided, it is used for both platforms.

### Running the Script

```bash
python pr_delta.py <PR_or_MR_URL> [--token <TOKEN>] [--include-tests] [--show-files] [--truncate-paths]
```

#### Arguments

- `<PR_or_MR_URL>`: The URL of the GitHub PR or GitLab MR.
- `--token <TOKEN>`: (Optional) Personal access token for authentication.
- `--include-tests`: (Optional) Include test files in the summary.
- `--show-files`: (Optional) Show per-file changes in the output.
- `--truncate-paths`: (Optional) Truncate long file paths in file changes output for better readability. 
                      If `--truncate-paths` is not provided, file paths in the per-file output are right-aligned and only the last 60 characters are shown. This helps ensure the filename is visible even for long paths.

#### Examples

Summarize a GitHub PR, excluding test files:
```bash
python pr_delta.py https://github.com/owner/repo/pull/123
```

Summarize a GitLab MR, including test files and showing per-file changes:
```bash
python pr_delta.py https://gitlab.com/group/project/-/merge_requests/456 --include-tests --show-files
```


Show per-file changes with truncated long file paths:
```bash
python pr_delta.py https://github.com/owner/repo/pull/123 --show-files --truncate-paths
```

## Output

- Total lines added, deleted, and changed.
- Optional per-file breakdown with config file indication.

## Notes

- The script supports both GitHub and GitLab PR/MR URLs.
- Make sure to provide the correct token for the platform you are querying.
