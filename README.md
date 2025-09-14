# cleanspool – Usenet Spool Cleaner

## NAME
**cleanspool** – interactive and batch tool for cleaning spam from an INN spool

---

## SYNOPSIS

```bash
cleanspool.py [GROUP] [OPTIONS]
```

---

## DESCRIPTION

`cleanspool.py` is a utility for **scanning and removing spam from an INN news spool**.  
Unlike Cleanfeed (which blocks incoming spam) or postfilter (which checks outgoing posts), this tool operates **after delivery** – on articles already in your spool.  

It supports both **interactive review** (showing headers and body snippets with [d]elete / [s]kip) and **non-interactive batch deletion** with keyword filters. A **safe dry-run** mode is included to preview matches before deleting.

The tool is intended for server operators who want a second line of defense against abusive crossposts, spam floods, and obvious garbage in technical hierarchies.

---

## OPTIONS

### Positional
- **GROUP**  
  A group name or wildcard pattern (e.g. `comp.*`, `alt.sex.*`).  
  Determines which spool directory is scanned.

### General
- **--lines N**  
  Number of body lines to display in interactive mode (default: 20).

- **--keywords word1,word2,…**  
  Comma-separated keyword list (overrides `keywords.txt`).  
  Supports quoted phrases (`"click here"`).

- **--subject-only**  
  Match keywords only in `Subject:` header.

- **--body-only**  
  Match keywords only in message body.

- **--dry-run**  
  Preview matches without deleting or logging.  
  Works in both interactive and batch modes.

### Interactive
(default if no other mode is chosen)

- Displays matching articles one by one.  
- Lets the operator decide:
  - `[d]elete` – cancel the article
  - `[s]kip` – mark safe, won’t be shown again
  - `[v]iew full` – show the entire article
  - `[q]uit` – exit immediately

### Batch
- **--batch-delete**  
  Non-interactive mode: automatically deletes all matching articles.  
  Uses the same filters (`--keywords`, `--subject-only`, etc.).

- **--delete-from FILE**  
  Cancel all articles listed in FILE (one Message-ID per line).  
  Useful for importing spam logs from another server.

- **--spamlog FILE**  
  Export Message-IDs of deleted articles into FILE.  
  Can be shared with peers as a “blacklist”.

---

## BACKGROUND STORY

Spam on Usenet is as old as Usenet itself. While modern filters like **Cleanfeed** and **postfilter** catch most of it at the edges, spam often slips through and clogs local spools.  

**cleanspool.py** was written as a **practical operator’s tool** to surgically clean up already-delivered spam. Its design goals:

- Be **interactive and cautious** by default.  
- Support **batch deletion** when confidence is high.  
- Always offer a **dry-run** mode for safety.  
- Encourage **sharing of spam logs** between admins.  

The tool is simple by design – just Python + `ctlinnd`. It relies on **keywords and operator judgment**, not heavy AI or blacklists.

---

## EXAMPLES

### Interactive cleanup with defaults
```bash
./cleanspool.py comp.* 
```
Scan the entire `comp.*` hierarchy using keywords from `keywords.txt`. Shows 20 lines of body preview per article.

---

### Show more body lines
```bash
./cleanspool.py alt.sex.* --lines 40
```
Preview 40 body lines instead of 20.

---

### Subject-only filter
```bash
./cleanspool.py sci.* --subject-only --keywords viagra
```
Match only if `Subject:` contains “viagra”.

---

### Phrase matching
```bash
./cleanspool.py alt.* --keywords '"click here to enter"'
```
Matches only if the full phrase `click here to enter` appears.

---

### Batch delete with keywords
```bash
./cleanspool.py comp.dcom.sys.cisco \\
  --batch-delete --subject-only \\
  --keywords ketamine,lsd,pills
```
Silently cancels all Cisco newsgroup spam about drugs.

---

### Batch dry-run (safe preview)
```bash
./cleanspool.py comp.* \\
  --batch-delete --keywords bitcoin \\
  --dry-run
```
Lists all matches but performs no cancels.

---

### Cancel from shared spamlog
```bash
./cleanspool.py --delete-from remote.spam
```
Cancels all Message-IDs listed in `remote.spam`.

---

### Export spamlog
```bash
./cleanspool.py comp.* --batch-delete \\
  --keywords viagra,pills \\
  --spamlog mysite.spam
```
Deletes matches and saves Message-IDs into `mysite.spam`.

---

## IMPORT/EXPORT SPAMLOG

`cleanspool` supports collaboration between news admins by allowing spamlog sharing:

- **Export** spamlog from your server:
  ```bash
  ./cleanspool.py comp.* --batch-delete --keywords viagra --spamlog mysite.spam
  ```
  Produces a `mysite.spam` file with only Message-IDs of deleted articles.

- **Import** spamlog on another server:
  ```bash
  ./cleanspool.py --delete-from mysite.spam
  ```
  Cancels all articles listed in `mysite.spam`.

This workflow makes it easy to share curated spamfeeds without setting up peering or complex filtering.

---

## FILES
- `keywords.txt` – list of keywords/phrases (default filter set)  
- `cleanspool.safe` – safelist of skipped Message-IDs  
- `cleanspool.log` – record of all deletions  

---

## SEE ALSO
- **cleanfeed**(8) – real-time spam filter for incoming Usenet articles  
- **postfilter** – outgoing article filter  
- **ctlinnd**(8) – control interface for INN  

---

## RELEASE NOTES

### v0.7.3 (feature freeze)
- Fixed `--dry-run` in batch mode (no more accidental deletes!).
- Added clear summary after dry-run: “N matches found.”
- Stable feature set, ready for release.
- Project renamed to **cleanspool**.

### v0.7.2
- Rebuilt `main()` logic to ensure `--batch-delete` takes precedence over interactive mode.

### v0.7.1
- Attempted fix for batch-mode precedence (superseded by v0.7.2).

### v0.7
- Introduced `--dry-run` mode for safe previewing of matches.
- Works in both interactive and batch modes.

### v0.6
- Merged features from v0.5 into v0.4 base.
- Added `--keywords` CLI override.
- Added `--batch-delete` for non-interactive spam removal.
- Preserved `--delete-from` and `--spamlog`.

### v0.5
- First version with `--keywords` override and batch deletion.
- Introduced phrase matching (`\"quoted phrase\"`).

### v0.4
- Interactive spool cleaner with:
  - Color UI
  - Skip-to-safe list (`cleanspool.safe`)
  - Logging of deletions (`cleanspool.log`)
  - `--delete-from` and `--spamlog` options
