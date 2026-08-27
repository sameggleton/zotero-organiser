# Security Policy

## Reporting a vulnerability

Report security issues privately through [GitHub Security Advisories](https://github.com/sameggleton/zotero-organiser/security/advisories/new).

Do not open a public issue for secrets, a local API token, or a write-path bug that could change someone else's Zotero library.

## What this tool can write

When `safety.write_enabled` is true, zotero-organiser mutates the open Zotero desktop library through the Local API (`http://127.0.0.1:23119/api`). It can add organiser-owned taxonomy tags. It does not parse PDFs, edit collections, or talk to zotero.org.

Writes are gated by the conservative defaults: `write_enabled` false, `require_backup` true, `only_new_items` true, `allow_tag_removal` false, and `max_items_per_cycle` 5. Keep those defaults until you have reviewed a sandbox library.

Each real write takes a Restic snapshot (unless backup is deliberately disabled), writes timestamped pre-write JSON, and sends `If-Unmodified-Since-Version`. Treat those artifacts as recovery data, not as a substitute for a full Zotero data-directory backup.

## Local API key in SQLite

Zotero 10+ issues a localhost write token after the in-app authorization dialog. The organiser stores that token in the state database as `meta.zotero_local_api_key`. It is a desktop Local API secret, not a zotero.org API key.

The database file is created mode `0600`. The parent is created `0700` and existing parents are chmod `0700` when possible. Treat `state.sqlite` as secret storage: do not copy it into tickets, backups that are world-readable, or a public gist.

Remote classifier keys (for example `OPENAI_API_KEY`) live in the process environment or in `~/.config/zotero-organiser/environment` (mode `600`). They are not written to SQLite.

## Classifier invocations without Zotero writes

`classify`, `dry-run`, `test`, and `tag-untagged` send title, abstract, item type, publication title, and existing tags to `classification.endpoint` only when remote classification is enabled. The default local pipeline keeps that metadata on-box. They do not parse PDFs. Preview commands use isolated SQLite and do not enqueue later Zotero writes.

The daemon (`run` / `once`) does not call the classifier while `safety.write_enabled` is false. `doctor` fails if writes are enabled while the process is still using the packaged starter taxonomy.
