#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import glob
import argparse
import re

SPOOL_DIR = "/usr/local/news/spool/articles"
KEYWORD_FILE = "keywords.txt"
SAFE_FILE = "cleanspool.safe"
LOG_FILE = "cleanspool.log"
THROTTLE_REASON = "Running cleanspool.py"

# ANSI
YELLOW = "\033[93m"
BWHITE = "\033[1;37m"
WHITE = "\033[0;37m"
BOLD = "\033[1m"
RESET = "\033[0m"

spinner = ['|', '/', '-', '\\']
spin_index = 0

def clear_screen():
    os.system("clear" if os.name == "posix" else "cls")

def spin():
    global spin_index
    print(f"\rScanning... {spinner[spin_index % len(spinner)]}", end="", flush=True)
    spin_index += 1

def throttle_inn():
    print("Throttling INN...", end="", flush=True)
    result = subprocess.run(["ctlinnd", "throttle", THROTTLE_REASON], capture_output=True, text=True)
    print(" OK" if result.returncode == 0 else f" FAILED ({result.stderr.strip()})")

def resume_inn():
    print("Resuming INN...", end="", flush=True)
    result = subprocess.run(["ctlinnd", "go", THROTTLE_REASON], capture_output=True, text=True)
    print(" OK" if result.returncode == 0 else f" FAILED ({result.stderr.strip()})")

def cancel_article(msgid):
    subprocess.run(["ctlinnd", "cancel", msgid])

def load_keywords(file_keywords=None):
    phrases = []
    # CLI override: comma-separated list supports quoted phrases
    if file_keywords:
        for raw in file_keywords.split(','):
            item = raw.strip()
            if not item:
                continue
            if (item.startswith('"') and item.endswith('"')) or (item.startswith("'") and item.endswith("'")):
                phrases.append(("phrase", item[1:-1].lower()))
            else:
                phrases.append(("word", item.lower()))
        return phrases
    try:
        with open(KEYWORD_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith('"') and line.endswith('"'):
                    phrases.append(("phrase", line[1:-1].lower()))
                else:
                    phrases.append(("word", line.lower()))
    except FileNotFoundError:
        return []
    return phrases

def match_keywords(content, keywords, subject_only=False, body_only=False, subject=""):
    haystack = ""
    if subject_only:
        haystack = subject.lower()
    elif body_only:
        haystack = content.lower()
    else:
        haystack = subject.lower() + " " + content.lower()

    for kind, word in keywords:
        if kind == "phrase" and word in haystack:
            return word
        elif kind == "word" and re.search(r'\b' + re.escape(word) + r'\b', haystack):
            return word
    return None

def load_safe_list():
    safe = set()
    if os.path.exists(SAFE_FILE):
        with open(SAFE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("<") and line.endswith(">"):
                    safe.add(line)
    return safe

def save_safe_message(msgid):
    with open(SAFE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{msgid}\n")

def dedupe_file(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = sorted(set(line.strip() for line in f if line.strip()))
        with open(path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

def extract_header(lines, name):
    for line in lines:
        if line.lower().startswith(name.lower() + ":"):
            return line.strip().split(":", 1)[1].strip()
    return "(missing)"

def extract_message_id(lines):
    for line in lines:
        if line.lower().startswith("message-id:"):
            return line.strip().split(":", 1)[1].strip()
    return None

def extract_body(lines):
    body = []
    passed_headers = False
    for line in lines:
        if passed_headers:
            body.append(line)
        elif line.strip() == "":
            passed_headers = True
    return body

def view_full_article(lines):
    clear_screen()
    print("".join(lines))
    print("=" * 80)
    input("Press Enter to continue...")

def show_summary(path, lines, matched_keyword, max_lines):
    clear_screen()
    subject = extract_header(lines, "Subject")
    from_header = extract_header(lines, "From")
    date_header = extract_header(lines, "Date")
    body = extract_body(lines)

    print(f"{YELLOW}FILE:{RESET} {path}")
    print(f"{BWHITE}Subject:{RESET} {subject}")
    print(f"{BWHITE}From:   {RESET} {from_header}")
    print(f"{BWHITE}Date:   {RESET} {date_header}")
    print("-" * 80)
    for line in body[:max_lines]:
        print(f"{WHITE}{line.rstrip()}{RESET}")
    print("=" * 80)
    if matched_keyword:
        print(f"{BWHITE}Keyword found:{RESET} {matched_keyword}")
    print("-" * 80)
    print(f"{BOLD}[d]{RESET}elete / {BOLD}[s]{RESET}kip / {BOLD}[v]{RESET}iew full / {BOLD}[q]{RESET}uit: ", end="")

def walk_articles(group_pattern=None):
    if group_pattern:
        pattern = os.path.join(SPOOL_DIR, *group_pattern.split("."))
        paths = glob.glob(pattern + "/**/*", recursive=True)
    else:
        paths = glob.glob(SPOOL_DIR + "/**/*", recursive=True)

    for path in paths:
        if os.path.isfile(path):
            yield path

def run_interactive(args):
    keywords = load_keywords(args.keywords)
    safe_ids = load_safe_list()
    throttle_inn()
    try:
        for i, path in enumerate(walk_articles(args.group)):
            spin() if i % 500 == 0 else None
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue

            msgid = extract_message_id(lines)
            if not msgid or msgid in safe_ids:
                continue

            subject = extract_header(lines, "Subject")
            bodytext = " ".join(extract_body(lines))
            matched = match_keywords(bodytext, keywords, args.subject_only, args.body_only, subject)

            if not matched:
                continue

            show_summary(path, lines, matched, args.lines)

            if args.dry_run:
                print("[DRY-RUN] No actions available (would prompt here)")
                continue

            while True:
                choice = input().strip().lower()
                if choice == "d":
                    cancel_article(msgid)
                    with open(LOG_FILE, "a", encoding="utf-8") as log:
                        log.write(f"{time.ctime()} DELETED {msgid} from {path}\n")
                    print(f"Deleted {msgid}")
                    break
                elif choice == "s":
                    save_safe_message(msgid)
                    print(f"Saved as safe: {msgid}")
                    break
                elif choice == "v":
                    view_full_article(lines)
                    show_summary(path, lines, matched, args.lines)
                    continue
                elif choice == "q":
                    print("Quitting.")
                    return
                else:
                    print("Invalid choice.")
    finally:
        resume_inn()
        dedupe_file(SAFE_FILE)
        dedupe_file(LOG_FILE)

def run_batch_delete_args(args):
    keywords = load_keywords(args.keywords)
    throttle_inn()
    count = 0
    matches = 0
    try:
        for path in walk_articles(args.group):
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue
            msgid = extract_message_id(lines)
            if not msgid:
                continue
            subject = extract_header(lines, "Subject")
            bodytext = " ".join(extract_body(lines))
            matched = match_keywords(bodytext, keywords, args.subject_only, args.body_only, subject)
            if matched:
                matches += 1
                if args.dry_run:
                    print(f"[DRY-RUN] Would delete {msgid} [keyword: {matched}]")
                    print(f"Subject: {subject}")
                    print(f"From: {extract_header(lines, 'From')}")
                    print(f"Date: {extract_header(lines, 'Date')}")
                    print("-" * 60)
                else:
                    cancel_article(msgid)
                    with open(LOG_FILE, "a", encoding="utf-8") as log:
                        log.write(f"{time.ctime()} DELETED {msgid} from {path}\\n")
                    print(f"Deleted {msgid} [keyword: {matched}]")
                    count += 1
    finally:
        resume_inn()
        if args.dry_run:
            print(f"Dry-run complete. {matches} matches found.")
        else:
            print(f"Batch delete complete. {count} articles removed.")

import re

def run_export_spamlog(filename):
    """
    Export all deleted Message-IDs (from cleanspool.log)
    into a separate file for sharing with peers.
    """
    pattern = re.compile(r"<[^>]+>")
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as src, \
             open(filename, "w", encoding="utf-8") as dst:
            seen = set()
            for line in src:
                match = pattern.search(line)
                if match:
                    msgid = match.group(0)
                    if msgid not in seen:
                        dst.write(msgid + "\n")
                        seen.add(msgid)
        print(f"Exported {len(seen)} Message-IDs to {filename}")
    except FileNotFoundError:
        print("No cleanspool.log found, nothing to export.")

def main():
    parser = argparse.ArgumentParser(description="CleanSpool v0.7.3.")
    parser.add_argument("group", nargs="?", help="Group name or wildcard (e.g. comp.*)")
    parser.add_argument("--delete-from", help="File with Message-IDs to cancel")
    parser.add_argument("--spamlog", help="Export deleted Message-IDs to file")
    parser.add_argument("--subject-only", action="store_true", help="Match keywords only in Subject")
    parser.add_argument("--body-only", action="store_true", help="Match keywords only in body")
    parser.add_argument("--lines", type=int, default=20, help="Number of body lines to show")
    parser.add_argument("--keywords", help="Comma-separated list of keywords (overrides keywords.txt)")
    parser.add_argument("--batch-delete", action="store_true", help="Enable non-interactive batch deletion")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without deleting or logging")
    args = parser.parse_args()

    if args.batch_delete:
        run_batch_delete_args(args)
    elif args.delete_from:
        run_batch_delete(args.delete_from)
    elif args.spamlog:
        run_export_spamlog(args.spamlog)
    else:
        run_interactive(args)

if __name__ == "__main__":
    main()
