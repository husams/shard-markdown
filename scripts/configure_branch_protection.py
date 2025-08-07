#!/usr/bin/env python3
"""Configure GitHub branch protection rules for shard-markdown.

This script helps configure branch protection rules that enforce type checking
and other quality gates to prevent CI/CD failures.
"""

import argparse
import json
import os
import subprocess  # noqa: S404
import sys
from typing import Any


def run_gh_command(command: list[str]) -> dict[str, Any]:
    """Run a GitHub CLI command and return JSON result."""
    try:
        result = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip():
            return dict(json.loads(result.stdout))
        return {}
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}")
        print(f"Command: {' '.join(command)}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}")
        print(f"Raw output: {result.stdout}")
        sys.exit(1)


def check_gh_auth() -> bool:
    """Check if GitHub CLI is authenticated."""
    try:
        subprocess.run(  # noqa: S603, S607
            ["gh", "auth", "status"],
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_repo_info() -> dict:
    """Get current repository information."""
    try:
        result = subprocess.run(  # noqa: S603, S607
            ["gh", "repo", "view", "--json", "owner,name,defaultBranchRef"],
            capture_output=True,
            text=True,
            check=True,
        )
        return dict(json.loads(result.stdout))
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error getting repository info: {e}")
        sys.exit(1)


def get_current_protection_rules(
    repo_owner: str, repo_name: str, branch: str
) -> dict | None:
    """Get current branch protection rules."""
    try:
        result = subprocess.run(  # noqa: S603, S607
            [
                "gh",
                "api",
                f"repos/{repo_owner}/{repo_name}/branches/{branch}/protection",
                "--method",
                "GET",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return dict(json.loads(result.stdout))
        elif result.returncode == 404:
            # No protection rules exist
            return None
        else:
            print(f"Error getting protection rules: {result.stderr}")
            return None

    except json.JSONDecodeError as e:
        print(f"Error parsing protection rules: {e}")
        return None


def configure_branch_protection(
    repo_owner: str, repo_name: str, branch: str = "main", dry_run: bool = False
) -> bool:
    """Configure branch protection rules with type checking requirements."""
    print(f"🔒 Configuring branch protection for {repo_owner}/{repo_name}:{branch}")

    # Get current protection rules
    current_rules = get_current_protection_rules(repo_owner, repo_name, branch)

    if current_rules:
        print("📋 Current protection rules exist")
        if not dry_run:
            response = input("Update existing rules? (y/N): ")
            if response.lower() != "y":
                print("Aborted.")
                return False

    # Define required status checks for type safety
    required_status_checks = [
        "lint",  # From ci.yml workflow
        "test (ubuntu-latest, 3.12)",  # At least one test matrix
        "coverage",  # Coverage check
        "security",  # Security scanning
        "Type Safety Monitoring / type-safety-metrics",  # Type safety monitoring
    ]

    # Branch protection configuration
    protection_config = {
        "required_status_checks": {
            "strict": True,  # Require branches to be up to date before merging
            "contexts": required_status_checks,
        },
        "enforce_admins": False,  # Allow admins to bypass (for emergency fixes)
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "require_last_push_approval": True,
        },
        "restrictions": None,  # No user/team restrictions
        "allow_force_pushes": False,  # Prevent force pushes
        "allow_deletions": False,  # Prevent branch deletion
        "block_creations": False,  # Allow branch creation
        "required_conversation_resolution": True,  # Require conversation resolution
    }

    print("📋 Protection configuration:")
    print("  ✅ Required status checks:")
    for check in required_status_checks:
        print(f"    - {check}")
    print("  ✅ Required PR reviews: 1")
    print("  ✅ Dismiss stale reviews: True")
    print("  ✅ Require up-to-date branches: True")
    print("  ✅ Block force pushes: True")
    print("  ✅ Require conversation resolution: True")

    if dry_run:
        print("\n🔍 DRY RUN - No changes will be made")
        print("Configuration that would be applied:")
        print(json.dumps(protection_config, indent=2))
        return True

    # Apply protection rules using GitHub API
    try:
        # Convert to API format
        api_data = {
            "required_status_checks": protection_config["required_status_checks"],
            "enforce_admins": protection_config["enforce_admins"],
            "required_pull_request_reviews": protection_config[
                "required_pull_request_reviews"
            ],
            "restrictions": protection_config["restrictions"],
            "allow_force_pushes": protection_config["allow_force_pushes"],
            "allow_deletions": protection_config["allow_deletions"],
            "block_creations": protection_config["block_creations"],
            "required_conversation_resolution": protection_config[
                "required_conversation_resolution"
            ],
        }

        # Write to temporary file for API call
        with open("branch_protection.json", "w") as f:
            json.dump(api_data, f, indent=2)

        # Apply protection rules
        result = subprocess.run(  # noqa: S603, S607
            [
                "gh",
                "api",
                f"repos/{repo_owner}/{repo_name}/branches/{branch}/protection",
                "--method",
                "PUT",
                "--input",
                "branch_protection.json",
            ],
            capture_output=True,
            text=True,
        )

        # Clean up temporary file
        os.unlink("branch_protection.json")

        if result.returncode == 0:
            print("✅ Branch protection rules applied successfully!")
            return True
        else:
            print(f"❌ Error applying protection rules: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error configuring branch protection: {e}")
        return False


def verify_protection_rules(
    repo_owner: str, repo_name: str, branch: str = "main"
) -> bool:
    """Verify that branch protection rules are properly configured."""
    print(f"🔍 Verifying branch protection for {repo_owner}/{repo_name}:{branch}")

    rules = get_current_protection_rules(repo_owner, repo_name, branch)

    if not rules:
        print("❌ No branch protection rules found")
        return False

    # Check required status checks
    status_checks = rules.get("required_status_checks", {})
    if not status_checks.get("strict"):
        print("⚠️  Warning: Branches are not required to be up to date")

    contexts = status_checks.get("contexts", [])
    print(f"📋 Required status checks ({len(contexts)}):")
    for context in contexts:
        print(f"  ✅ {context}")

    # Check for critical type safety checks
    critical_checks = ["lint", "coverage", "type-safety-metrics"]
    missing_checks = []
    for check in critical_checks:
        if not any(check in context for context in contexts):
            missing_checks.append(check)

    if missing_checks:
        print("⚠️  Missing critical type safety checks:")
        for check in missing_checks:
            print(f"    ❌ {check}")

    # Check PR review requirements
    pr_reviews = rules.get("required_pull_request_reviews", {})
    review_count = pr_reviews.get("required_approving_review_count", 0)
    print(f"👥 Required PR reviews: {review_count}")

    if pr_reviews.get("dismiss_stale_reviews"):
        print("✅ Stale review dismissal: Enabled")
    else:
        print("⚠️  Stale review dismissal: Disabled")

    # Check other settings
    if not rules.get("allow_force_pushes", {}).get("enabled", True):
        print("✅ Force pushes: Blocked")
    else:
        print("⚠️  Force pushes: Allowed")

    success: bool = len(missing_checks) == 0 and review_count > 0
    if success:
        print("✅ Branch protection rules are properly configured!")
    else:
        print("❌ Branch protection rules need attention")

    return success


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Configure GitHub branch protection rules for type safety enforcement"
        )
    )

    parser.add_argument(
        "--branch",
        default="main",
        help="Branch to configure protection for (default: main)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be configured without making changes",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify current protection rules, don't configure",
    )

    args = parser.parse_args()

    # Check GitHub CLI authentication
    if not check_gh_auth():
        print("❌ GitHub CLI is not authenticated")
        print("Run: gh auth login")
        return 1

    # Get repository information
    try:
        repo_info = get_repo_info()
        repo_owner = repo_info["owner"]["login"]
        repo_name = repo_info["name"]
        default_branch = repo_info["defaultBranchRef"]["name"]

        print(f"🏠 Repository: {repo_owner}/{repo_name}")
        print(f"🌿 Default branch: {default_branch}")

        if args.branch != default_branch:
            print(
                f"⚠️  Warning: Configuring protection for '{args.branch}' "
                f"instead of default branch '{default_branch}'"
            )

    except Exception as e:
        print(f"❌ Error getting repository info: {e}")
        return 1

    if args.verify_only:
        success = verify_protection_rules(repo_owner, repo_name, args.branch)
        return 0 if success else 1

    # Configure branch protection
    success = configure_branch_protection(
        repo_owner, repo_name, args.branch, dry_run=args.dry_run
    )

    if success and not args.dry_run:
        # Verify the configuration
        print("\n🔍 Verifying configuration...")
        verify_protection_rules(repo_owner, repo_name, args.branch)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
