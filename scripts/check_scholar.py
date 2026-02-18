#!/usr/bin/env python3
"""
Automated Scholar + Releases → News → Deploy → Bluesky pipeline.

Checks Google Scholar for new publications and CRAN for new pammtools
releases, generates news items, renders the Quarto site, commits,
pushes, deploys, and posts to Bluesky.

Usage:
    python3 check_scholar.py              # full run
    python3 check_scholar.py --dry-run    # check only, no deploy/post
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONFIG_PATH = Path.home() / ".config" / "scholar-bot" / "config.json"
SCRIPT_DIR = Path(__file__).resolve().parent
SITE_DIR = SCRIPT_DIR.parent
KNOWN_PUBS_PATH = SCRIPT_DIR / "known_pubs.json"
KNOWN_RELEASES_PATH = SCRIPT_DIR / "known_releases.json"
NEWS_DIR = SITE_DIR / "news"

LOG_DIR = Path.home() / ".local" / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "scholar-check.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def load_config():
    if not CONFIG_PATH.exists():
        log.error(f"Config not found: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_known_pubs():
    if KNOWN_PUBS_PATH.exists():
        with open(KNOWN_PUBS_PATH) as f:
            return set(json.load(f))
    return set()


def save_known_pubs(titles):
    with open(KNOWN_PUBS_PATH, "w") as f:
        json.dump(sorted(titles), f, indent=2)


# Titles to skip (e.g. internal reports, non-peer-reviewed)
SKIP_PATTERNS = ["CODAG", "CoDAG"]


def should_skip(title):
    return any(pat in title for pat in SKIP_PATTERNS)


def load_known_releases():
    if KNOWN_RELEASES_PATH.exists():
        with open(KNOWN_RELEASES_PATH) as f:
            return json.load(f)
    return {}


def save_known_releases(releases):
    with open(KNOWN_RELEASES_PATH, "w") as f:
        json.dump(releases, f, indent=2)


# ---------------------------------------------------------------------------
# CRAN / GitHub releases
# ---------------------------------------------------------------------------

TRACKED_PACKAGES = [
    {
        "name": "pammtools",
        "github": "adibender/pammtools",
        "cran": "pammtools",
    },
]


def fetch_cran_version(package_name):
    """Fetch latest CRAN version and date."""
    import urllib.request

    url = f"https://crandb.r-pkg.org/{package_name}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        return {
            "version": data.get("Version", ""),
            "date": data.get("Date/Publication", "")[:10],
            "title": data.get("Title", ""),
        }
    except Exception as e:
        log.warning(f"Could not fetch CRAN info for {package_name}: {e}")
        return None


def fetch_github_release(repo):
    """Fetch latest GitHub release with changelog."""
    import urllib.request

    url = f"https://api.github.com/repos/{repo}/releases?per_page=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "scholar-bot"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if not data:
            return None
        r = data[0]
        return {
            "tag": r.get("tag_name", ""),
            "date": r.get("published_at", "")[:10],
            "name": r.get("name", ""),
            "body": r.get("body", ""),
        }
    except Exception as e:
        log.warning(f"Could not fetch GitHub release for {repo}: {e}")
        return None


def fetch_news_md(repo):
    """Fetch NEWS.md from a GitHub repo and return content."""
    import urllib.request

    for branch in ("master", "main"):
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/NEWS.md"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "scholar-bot"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            continue
    return ""


def extract_version_changelog(news_md, version):
    """Extract the changelog section for a specific version from NEWS.md."""
    lines = news_md.split("\n")
    capturing = False
    changelog_lines = []

    for line in lines:
        # Match version headers like "# pammtools 0.7.4" or "# pamtools 0.5.93"
        if re.match(r"^#\s+\w+\s+", line):
            if capturing:
                break  # Hit the next version header
            if version in line:
                capturing = True
                continue
        elif capturing:
            changelog_lines.append(line)

    return "\n".join(changelog_lines).strip()


# Patterns that indicate a trivial/maintenance-only release
TRIVIAL_PATTERNS = [
    r"^[\s*+-]*maint[ea]?n[ae]?nce.*",
    r"^[\s*+-]*cran fix",
    r"^[\s*+-]*compliance with",
    r"^[\s*+-]*removed? .* dependency",
    r"^[\s*+-]*fix(ed|es)? (to )?url",
    r"^[\s*+-]*link fix",
    r"^[\s*+-]*discrepancy between man page",
    r"^[\s*+-]*deprecation",
    r"^[\s*+-]*smaller bugs?$",
]


def is_trivial_release(changelog):
    """Check if a changelog only contains trivial/maintenance changes."""
    if not changelog:
        return True

    lines = [l.strip() for l in changelog.split("\n") if l.strip()]
    if not lines:
        return True

    # If ALL non-empty lines match trivial patterns, skip
    for line in lines:
        if not any(re.search(pat, line, re.IGNORECASE) for pat in TRIVIAL_PATTERNS):
            return False

    return True


def check_package_releases():
    """Check for new CRAN versions. Skip trivial maintenance releases."""
    known = load_known_releases()
    new_releases = []

    for pkg in TRACKED_PACKAGES:
        name = pkg["name"]
        pkg_known = known.get(name, {})

        # Check CRAN
        cran = fetch_cran_version(pkg["cran"])
        if cran and cran["version"] != pkg_known.get("cran_version", ""):
            log.info(f"New CRAN release: {name} {cran['version']}")

            # Get changelog from NEWS.md
            news_md = fetch_news_md(pkg["github"])
            changelog = extract_version_changelog(news_md, cran["version"])

            if is_trivial_release(changelog):
                log.info(f"Skipping trivial release: {name} {cran['version']}")
                log.info(f"  Changelog: {changelog[:200]}")
                pkg_known["cran_version"] = cran["version"]
                known[name] = pkg_known
                continue

            log.info(f"Non-trivial release: {name} {cran['version']}")

            new_releases.append({
                "type": "release",
                "package": name,
                "version": cran["version"],
                "date": cran["date"],
                "changelog": changelog,
                "cran_url": f"https://cran.r-project.org/package={pkg['cran']}",
                "github_url": f"https://github.com/{pkg['github']}",
            })

            pkg_known["cran_version"] = cran["version"]

        known[name] = pkg_known

    return new_releases, known


def generate_release_news_item(release):
    """Create a news .qmd file for a package release."""
    today = date.today().isoformat()
    name = release["package"]
    version = release["version"]
    slug = slugify(f"{name}-{version}")
    filename = f"{today}-{slug}.qmd"
    filepath = NEWS_DIR / filename

    # Summarize changelog
    changelog = release.get("changelog", "")
    if changelog:
        # Clean up markdown, take first few lines
        lines = [l.strip() for l in changelog.strip().split("\n") if l.strip()]
        summary = "\n".join(f"- {l.lstrip('- ')}" for l in lines[:8])
        if len(lines) > 8:
            summary += "\n- ..."
    else:
        summary = f"New version of {name} is now available on CRAN."

    content = f"""---
title: "{name} {version} released"
date: {today}
---

[{name}](https://adibender.github.io/{name}/) version **{version}** is now available on [CRAN]({release['cran_url']}).

### What's new

{summary}

[GitHub]({release['github_url']}) | [CRAN]({release['cran_url']})
"""

    filepath.write_text(content)
    log.info(f"Created release news item: {filename}")
    return filepath


def post_release_to_bluesky(config, release, dry_run=False):
    """Post about a package release to Bluesky."""
    handle = config.get("bluesky_handle", "")
    password = config.get("bluesky_app_password", "")

    if not handle or not password or password == "FILL_IN":
        log.warning("Bluesky credentials not configured — skipping post")
        return

    name = release["package"]
    version = release["version"]
    cran_url = release["cran_url"]

    post_text = f"{name} {version} released on CRAN!"

    # Add a short changelog summary
    changelog = release.get("changelog", "")
    if changelog:
        lines = [l.strip().lstrip("- ") for l in changelog.strip().split("\n") if l.strip()]
        short = "; ".join(lines[:3])
        if len(short) > 180:
            short = short[:177] + "..."
        post_text += f"\n\n{short}"

    if dry_run:
        log.info(f"[DRY RUN] Would post to Bluesky:\n{post_text}\nLink: {cran_url}")
        return

    from atproto import Client, client_utils

    client = Client()
    client.login(handle, password)

    text = (
        client_utils.TextBuilder()
        .text(post_text + "\n\n")
        .link("View on CRAN", cran_url)
    )

    client.send_post(text)
    log.info(f"Posted release to Bluesky: {name} {version}")


# ---------------------------------------------------------------------------
# Scholar
# ---------------------------------------------------------------------------


def fetch_scholar_pubs(scholar_id):
    """Fetch publications from Google Scholar. Returns list of dicts."""
    from scholarly import scholarly

    log.info(f"Fetching Scholar profile: {scholar_id}")
    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=["publications"])

    pubs = []
    for p in author["publications"]:
        bib = p.get("bib", {})
        title = bib.get("title", "")
        if not title or should_skip(title):
            continue

        # Try to get more details (abstract, journal) — but don't fail on rate limit
        journal = bib.get("journal", bib.get("venue", bib.get("citation", "")))
        abstract = ""
        try:
            filled = scholarly.fill(p)
            bib_filled = filled.get("bib", {})
            abstract = bib_filled.get("abstract", "")
            journal = bib_filled.get("journal", journal)
        except Exception:
            log.warning(f"Could not fetch details for: {title[:60]}...")

        pubs.append({
            "title": title,
            "journal": journal,
            "abstract": abstract,
            "year": bib.get("pub_year", str(date.today().year)),
        })

    log.info(f"Found {len(pubs)} publications on Scholar")
    return pubs


# ---------------------------------------------------------------------------
# News generation
# ---------------------------------------------------------------------------


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]


def make_summary(pub):
    """Create a short summary from abstract or fallback to title."""
    abstract = pub.get("abstract", "")
    if abstract:
        # Take first two sentences
        sentences = re.split(r"(?<=[.!?])\s+", abstract)
        summary = " ".join(sentences[:2])
        if len(summary) > 300:
            summary = summary[:297] + "..."
        return summary
    return pub["title"]


def generate_news_item(pub):
    """Create a news .qmd file for a new publication."""
    today = date.today().isoformat()
    slug = slugify(pub["title"])
    filename = f"{today}-{slug}.qmd"
    filepath = NEWS_DIR / filename

    summary = make_summary(pub)
    journal = pub.get("journal", "")
    venue_line = f"*{journal}*\n\n" if journal else ""
    scholar_q = quote(f'"{pub["title"]}"')
    scholar_link = f"https://scholar.google.com/scholar?q={scholar_q}"

    content = f"""---
title: "New publication: {pub['title']}"
date: {today}
---

{venue_line}{summary}

[Find paper on Google Scholar]({scholar_link})
"""

    filepath.write_text(content)
    log.info(f"Created news item: {filename}")
    return filepath


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------


def run_cmd(cmd, cwd=None):
    log.info(f"Running: {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd or SITE_DIR,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.error(f"Command failed: {cmd}\n{result.stderr}")
    return result


def render_and_deploy(new_titles, dry_run=False):
    """Render site, commit, push, deploy to GitHub Pages."""
    if dry_run:
        log.info("[DRY RUN] Would render, commit, push, and deploy")
        return

    run_cmd("quarto render")

    # Open in browser
    index_path = SITE_DIR / "docs" / "index.html"
    run_cmd(f"xdg-open {index_path}")

    # Git commit and push
    run_cmd("git add -A")
    title_summary = new_titles[0] if len(new_titles) == 1 else f"{len(new_titles)} new publications"
    run_cmd(f'git commit -m "New publication: {title_summary}"')
    run_cmd("git push")

    # Deploy to GitHub Pages
    run_cmd("quarto publish gh-pages --no-prompt")

    log.info("Site deployed to GitHub Pages")


# ---------------------------------------------------------------------------
# Bluesky
# ---------------------------------------------------------------------------


def post_to_bluesky(config, pub, dry_run=False):
    """Post about a new publication to Bluesky."""
    handle = config.get("bluesky_handle", "")
    password = config.get("bluesky_app_password", "")

    if not handle or not password or password == "FILL_IN":
        log.warning("Bluesky credentials not configured — skipping post")
        return

    title = pub["title"]
    summary = make_summary(pub)
    site_url = config.get("site_url", "https://adibender.github.io")
    news_url = f"{site_url}/news.html"

    post_text = f"New publication: {title}\n\n{summary}"
    # Truncate if needed (Bluesky limit is 300 chars for text, link is separate)
    if len(post_text) > 250:
        post_text = post_text[:247] + "..."

    if dry_run:
        log.info(f"[DRY RUN] Would post to Bluesky:\n{post_text}\nLink: {news_url}")
        return

    from atproto import Client, client_utils

    client = Client()
    client.login(handle, password)

    text = (
        client_utils.TextBuilder()
        .text(post_text + "\n\n")
        .link("Read more", news_url)
    )

    client.send_post(text)
    log.info(f"Posted to Bluesky: {title[:60]}...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Scholar + Releases → News → Deploy → Bluesky")
    parser.add_argument("--dry-run", action="store_true", help="Check only, no deploy/post")
    args = parser.parse_args()

    config = load_config()
    scholar_id = config.get("scholar_id", "pYXcdVQAAAAJ")
    has_updates = False

    # --- Check Scholar ---
    new_pubs = []
    try:
        current_pubs = fetch_scholar_pubs(scholar_id)
        current_titles = {p["title"] for p in current_pubs}
        known_titles = load_known_pubs()
        new_titles = current_titles - known_titles

        if new_titles:
            log.info(f"Found {len(new_titles)} new publication(s):")
            new_pubs = [p for p in current_pubs if p["title"] in new_titles]
            for p in new_pubs:
                log.info(f"  - {p['title']}")
            for pub in new_pubs:
                generate_news_item(pub)
            update_publications_page(current_pubs)
            has_updates = True
        else:
            log.info("No new publications found")
    except Exception as e:
        log.error(f"Failed to fetch Scholar: {e}")
        current_titles = set()
        known_titles = load_known_pubs()

    # --- Check package releases ---
    new_releases, known_releases = check_package_releases()
    if new_releases:
        log.info(f"Found {len(new_releases)} new package release(s)")
        for rel in new_releases:
            generate_release_news_item(rel)
        has_updates = True
    else:
        log.info("No new package releases found")

    if not has_updates:
        log.info("Nothing new — done")
        return

    # Collect all update titles for commit message
    all_titles = [p["title"] for p in new_pubs]
    all_titles += [f"{r['package']} {r['version']}" for r in new_releases]
    render_and_deploy(all_titles, dry_run=args.dry_run)

    # Post to Bluesky
    for pub in new_pubs:
        post_to_bluesky(config, pub, dry_run=args.dry_run)
    for rel in new_releases:
        post_release_to_bluesky(config, rel, dry_run=args.dry_run)

    # Save state
    if not args.dry_run:
        if new_pubs:
            save_known_pubs(current_titles | known_titles)
            log.info("Updated known publications list")
        if new_releases:
            save_known_releases(known_releases)
            log.info("Updated known releases list")
    else:
        log.info("[DRY RUN] Would update known publications/releases")


def update_publications_page(pubs):
    """Regenerate publications.qmd from current Scholar data."""
    from collections import OrderedDict

    pubs_sorted = sorted(pubs, key=lambda x: x.get("year", "0"), reverse=True)
    by_year = OrderedDict()
    for p in pubs_sorted:
        y = p.get("year", "Unknown")
        by_year.setdefault(y, []).append(p)

    lines = [
        "---",
        'title: "Publications"',
        "---",
        "",
        "Full list and citation counts on [Google Scholar](https://scholar.google.com/citations?user=pYXcdVQAAAAJ&hl=en).",
        "",
    ]

    for year, papers in by_year.items():
        lines.append(f"## {year}")
        lines.append("")
        for p in papers:
            title = p["title"]
            search_q = quote(f'"{title}"')
            scholar_link = f"https://scholar.google.com/scholar?q={search_q}"
            lines.append(f"- [{title}]({scholar_link})")
        lines.append("")

    pub_path = SITE_DIR / "publications.qmd"
    pub_path.write_text("\n".join(lines))
    log.info("Updated publications.qmd")


if __name__ == "__main__":
    main()
