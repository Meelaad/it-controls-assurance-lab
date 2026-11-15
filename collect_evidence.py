import csv
import json
import random
import subprocess
import sys

OWNER = "Meelaad"
REPOS = ["cve-triage", "access-governance-lab", "splunk-detections", "traffic-analysis"]
SAMPLE_SIZE = 10
SEED = 2026


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if r.returncode != 0:
        if "HTTP 404" in r.stderr:
            return None
        sys.exit(f"gh api {path} failed: {r.stderr.strip()}")
    return json.loads(r.stdout)


def all_commits(repo):
    out, page = [], 1
    while True:
        batch = gh(f"repos/{OWNER}/{repo}/commits?per_page=100&page={page}")
        if not batch:
            return out
        out += batch
        page += 1


def repo_settings(repo):
    info = gh(f"repos/{OWNER}/{repo}")
    sec = info.get("security_and_analysis") or {}
    protection = gh(f"repos/{OWNER}/{repo}/branches/{info['default_branch']}/protection")
    workflows = gh(f"repos/{OWNER}/{repo}/actions/workflows")
    return {
        "repo": repo,
        "visibility": info["visibility"],
        "branch_protection": "yes" if protection else "no",
        "secret_scanning": sec.get("secret_scanning", {}).get("status", "unknown"),
        "push_protection": sec.get("secret_scanning_push_protection", {}).get("status", "unknown"),
        "dependabot_updates": sec.get("dependabot_security_updates", {}).get("status", "unknown"),
        "workflows": workflows["total_count"],
    }


def change_sample(repo):
    commits = all_commits(repo)
    rng = random.Random(SEED)
    picked = rng.sample(commits, min(SAMPLE_SIZE, len(commits)))
    rows = []
    for c in picked:
        # GitHub links a commit to the PR it was merged from
        prs = gh(f"repos/{OWNER}/{repo}/commits/{c['sha']}/pulls") or []
        approved = 0
        for pr in prs:
            reviews = gh(f"repos/{OWNER}/{repo}/pulls/{pr['number']}/reviews") or []
            approved += sum(1 for rv in reviews if rv["state"] == "APPROVED")
        rows.append({
            "repo": repo,
            "sha": c["sha"][:7],
            "date": c["commit"]["author"]["date"][:10],
            "message": c["commit"]["message"].splitlines()[0],
            "via_pr": "yes" if prs else "no",
            "approvals": approved,
        })
    return len(commits), rows


def write_csv(name, rows):
    with open(f"evidence/{name}", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    settings, samples = [], []
    for repo in REPOS:
        settings.append(repo_settings(repo))
        total, rows = change_sample(repo)
        samples += rows
        print(f"{repo}: {total} commits on the default branch, sampled {len(rows)}")
    write_csv("repo_settings.csv", settings)
    write_csv("change_samples.csv", samples)
