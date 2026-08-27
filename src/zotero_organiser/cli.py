from __future__ import annotations

import argparse
import logging
import signal
import tempfile
from pathlib import Path

import yaml

from . import __version__
from .backup import repository_status
from .config import (
    Config,
    default_config_path,
    default_environment_path,
    default_user_taxonomy_path,
    load_config,
    load_environment,
)
from .daemon import Organiser
from .doctor import run_checks
from .personalization import build_profile
from .ranking import RankerUnavailable, TaxonomyRanker
from .state import StateStore
from .taxonomy import (
    Taxonomy,
    get_profile_path,
    install_user_taxonomy,
    list_profiles,
    load_taxonomy,
    packaged_taxonomy_path,
)
from .taxonomy_audit import audit_taxonomy
from .test_assistant import CLASSIFIER_PRIVACY_WARNING, isolated_config, run_interactive
from .zotero import ZoteroClient


def default_taxonomy_path(module_file: Path | None = None) -> Path:
    """Return the packaged starter. Runtime use should copy it with taxonomy init."""
    if module_file is not None:
        return module_file.with_name("taxonomy.yml")
    return packaged_taxonomy_path()


def resolve_taxonomy_path(cli_taxonomy: Path | None, config: Config | None = None) -> Path:
    """Prefer --taxonomy, then config taxonomy.path, then the packaged default."""
    if cli_taxonomy is not None:
        return cli_taxonomy
    if config is not None and config.taxonomy.path is not None:
        return config.taxonomy.path
    return default_taxonomy_path()


def _handle_shutdown(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("count must be at least 1")
    return parsed


def unit_interval(value: str) -> float:
    parsed = float(value)
    if not 0 <= parsed <= 1:
        raise argparse.ArgumentTypeError("value must be between 0 and 1")
    return parsed


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="zotero-organiser")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--config", type=Path, default=default_config_path())
    p.add_argument("--env-file", type=Path, default=default_environment_path())
    p.add_argument(
        "--taxonomy",
        type=Path,
        default=None,
        help="taxonomy YAML; overrides taxonomy.path in the config file",
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="poll Zotero and organise new items")
    sub.add_parser("once", help="run one synchronisation cycle and exit")
    sub.add_parser("status", help="show organiser queue and backup status")
    sub.add_parser("doctor", help="check local API, storage, backup, and credentials")
    sub.add_parser(
        "test", help="interactively dry-run selected live Zotero items; never writes Zotero"
    )
    batch = sub.add_parser("tag-untagged", help="classify and tag N items without taxonomy tags")
    batch.add_argument(
        "count", type=positive_int, help="maximum number of eligible items to process"
    )
    models = sub.add_parser("models", help="download or report local embedding and NLI models")
    models_subcommands = models.add_subparsers(dest="models_command", required=True)
    models_subcommands.add_parser(
        "download", help="download the embedding and NLI models enabled in the configuration"
    )
    models_subcommands.add_parser("status", help="show whether configured local models are cached")
    classify = sub.add_parser(
        "classify", help="preview tags for one item using isolated state; never writes Zotero"
    )
    classify.add_argument("item_key")
    dry_run = sub.add_parser(
        "dry-run", help="preview tags for one item using isolated state; never writes Zotero"
    )
    dry_run.add_argument("item_key")
    retry = sub.add_parser("retry", help="reprocess one item and write tags if writes are enabled")
    retry.add_argument("item_key")
    tax = sub.add_parser("taxonomy", help="validate, copy, or audit the taxonomy")
    taxonomy_subcommands = tax.add_subparsers(dest="taxonomy_command", required=True)
    taxonomy_subcommands.add_parser("validate", help="check that the taxonomy file is valid")
    taxonomy_subcommands.add_parser("path", help="print the taxonomy file that would be used")
    init = taxonomy_subcommands.add_parser(
        "init",
        help="copy the packaged starter to your config directory for editing",
    )
    init.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing user taxonomy",
    )
    init.add_argument(
        "--from",
        dest="source",
        type=Path,
        default=None,
        help="copy this YAML instead of the packaged starter",
    )
    init.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="destination path (default: taxonomy.yml next to --config)",
    )
    audit = taxonomy_subcommands.add_parser(
        "audit", help="report potentially overlapping taxonomy tags; never changes tagging"
    )
    audit.add_argument("--threshold", type=unit_interval, default=0.88)
    audit.add_argument("--history", action="store_true", help="show recent persisted audit runs")
    audit.add_argument("--history-limit", type=positive_int, default=10)
    profiles = taxonomy_subcommands.add_parser(
        "profiles", help="list or show researched domain taxonomy profiles"
    )
    profiles_subcommands = profiles.add_subparsers(dest="profiles_command", required=True)
    profiles_subcommands.add_parser(
        "list", help="list available researched domain taxonomy profiles"
    )
    show = profiles_subcommands.add_parser(
        "show", help="display summary of namespaces and tags in a domain profile"
    )
    show.add_argument("profile_id", help="domain profile ID (e.g., general-scholar, physics)")

    profile = sub.add_parser("profile", help="build and review the local tag-preference profile")
    profile_subcommands = profile.add_subparsers(dest="profile_command", required=True)
    profile_subcommands.add_parser(
        "build", help="scan the local library and build a preference profile"
    )
    profile_subcommands.add_parser("status", help="show the current local preference profile")
    review = profile_subcommands.add_parser("review", help="list profile vocabulary and mappings")
    review.add_argument("--limit", type=positive_int, default=100)
    mapping = profile_subcommands.add_parser(
        "map", help="map a raw library tag to a canonical taxonomy tag"
    )
    mapping.add_argument("raw_tag")
    mapping.add_argument("canonical_tag")
    export = profile_subcommands.add_parser("export", help="write profile mappings to a YAML file")
    export.add_argument("path", type=Path)
    imported = profile_subcommands.add_parser(
        "import", help="load profile mappings from a YAML file"
    )
    imported.add_argument("path", type=Path)
    return p


def _isolated_preview(
    config: Config, taxonomy: Taxonomy, item_key: str, *, force: bool
) -> dict | None:
    if config.classification.enabled:
        print(CLASSIFIER_PRIVACY_WARNING)
    with tempfile.TemporaryDirectory(prefix="zotero-organiser-dry-run-") as directory:
        organiser = Organiser(isolated_config(config, Path(directory)), taxonomy)
        try:
            return organiser.process(item_key, dry_run=True, force=force)
        finally:
            organiser.close()


def _print_preview(item_key: str, result: dict | None) -> None:
    if result and "item" in result and "scores" in result:
        print(f"Paper:\n  {result['item']['data'].get('title', '')}\n\nCurrent:")
        print(
            "\n".join(
                f"  {tag}"
                for tag in sorted(result["item"]["data"].get("tags", []), key=lambda t: t["tag"])
                for tag in [tag["tag"]]
            )
        )
        print("\nProposed:")
        for tag, confidence in result["scores"].items():
            print(f"  + {tag:<35} {confidence:.2f}")
        print("\nNo Zotero changes made.")
        return
    if result and result.get("skipped"):
        print(f"skipped {item_key}: {result['skipped']}")
        return
    if result:
        print(f"processed {item_key}")


def main() -> None:
    args = parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_environment(args.env_file)
    if args.command == "taxonomy" and args.taxonomy_command == "init":
        try:
            config = load_config(args.config)
        except FileNotFoundError:
            config = None
        destination = args.dest or default_user_taxonomy_path(args.config)
        try:
            written = install_user_taxonomy(destination, args.source, force=args.force)
        except FileExistsError:
            raise SystemExit(
                f"taxonomy already exists at {destination}; pass --force to overwrite"
            ) from None
        except (FileNotFoundError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
        print(f"Wrote {written}")
        if config is None:
            print(f"Set taxonomy.path to {written} in your config, or re-run setup.")
        elif config.taxonomy.path is None or config.taxonomy.path.resolve() != written.resolve():
            print(f"Point taxonomy.path at {written} in {args.config}")
        return
    if args.command == "taxonomy" and args.taxonomy_command in {"validate", "path"}:
        config = None
        if args.taxonomy is None:
            try:
                config = load_config(args.config)
            except FileNotFoundError:
                config = None
        path = resolve_taxonomy_path(args.taxonomy, config)
        if args.taxonomy_command == "path":
            print(path)
            return
        taxonomy = load_taxonomy(path)
        print(f"taxonomy v{taxonomy.version} valid; {len(taxonomy.tags())} allowed tags")
        return
    if args.command == "taxonomy" and args.taxonomy_command == "profiles":
        if args.profiles_command == "list":
            for pid, path in list_profiles():
                try:
                    tax = load_taxonomy(path)
                    first_sentence = (
                        tax.description.strip().split(". ")[0] if tax.description else ""
                    )
                    if first_sentence and not first_sentence.endswith("."):
                        first_sentence += "."
                    print(f"{pid:<22} ({len(tax.classifier_tags())} tags)  {first_sentence}")
                except Exception:
                    print(f"{pid:<22} - {path}")
            return
        if args.profiles_command == "show":
            try:
                tax_path = get_profile_path(args.profile_id)
                tax = load_taxonomy(tax_path)
            except (FileNotFoundError, ValueError) as exc:
                raise SystemExit(str(exc)) from exc
            print(f"Profile: {args.profile_id.removesuffix('.yml')}")
            print(f"Version: {tax.version}")
            if tax.description:
                print(f"Description: {tax.description.strip()}")
            print("\nNamespaces:")
            for ns_name, ns in tax.namespaces.items():
                tags_str = ", ".join(ns.values.keys())
                eligible = "classifier-eligible" if ns.classifier_eligible else "ineligible"
                print(f"  {ns_name} ({ns.kind}, max {ns.max_tags}, {eligible}):")
                if ns.description:
                    print(f"    Description: {ns.description.strip()}")
                print(f"    Tags ({len(ns.values)}): {tags_str}")
            print(
                f"\nTotal tags: {len(tax.tags())} ({len(tax.classifier_tags())} classifier eligible)"
            )
            return

    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        raise SystemExit(f"configuration file not found: {args.config}") from exc
    if args.command == "models":
        from .models import download_active_models, model_status

        if args.models_command == "status":
            statuses = model_status(config)
            if not statuses:
                print("no local models are enabled")
                return
            for status in statuses:
                print(
                    f"{'OK' if status.cached else 'MISSING':<8} {status.name}: "
                    f"{status.model}; {status.detail}"
                )
            if not all(status.cached for status in statuses):
                raise SystemExit(1)
            return
        try:
            download_active_models(config)
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        print("downloaded configured local models")
        return
    taxonomy = load_taxonomy(resolve_taxonomy_path(args.taxonomy, config))
    if args.command == "profile":
        state = StateStore(config.state.database)
        try:
            if args.profile_command == "build":
                zotero = ZoteroClient(
                    config.zotero,
                    server_id=state.get_zotero_server_id(),
                    local_api_key=state.get_local_api_key(),
                )
                try:
                    profile = build_profile(state, zotero, TaxonomyRanker(config.ranking, taxonomy))
                except RankerUnavailable as exc:
                    raise SystemExit(f"profile build unavailable: {exc}") from exc
                finally:
                    zotero.close()
                print(
                    f"profile built from {profile.item_count} tagged items and {profile.tag_count} distinct tags; "
                    "no Zotero tags changed"
                )
            elif args.profile_command == "status":
                status = state.profile_status()
                if status is None:
                    print("no local preference profile; run `zotero-organiser profile build`")
                else:
                    print(
                        f"profile built: {status['created_at']}; model {status['embedding_model']}; "
                        f"tagged items {status['item_count']}; vocabulary {status['tag_count']}"
                    )
            elif args.profile_command == "review":
                vocabulary = state.profile_vocabulary(limit=args.limit)
                if not vocabulary:
                    print("no profile vocabulary; run `zotero-organiser profile build`")
                for entry in vocabulary:
                    canonical = entry["canonical_tag"] or (
                        entry["raw_tag"]
                        if entry["raw_tag"] in taxonomy.classifier_tags()
                        else "unmapped"
                    )
                    print(f"{entry['raw_tag']}\t{entry['item_count']} item(s)\t{canonical}")
            elif args.profile_command == "map":
                if args.canonical_tag not in taxonomy.classifier_tags():
                    raise SystemExit(
                        f"not an eligible canonical taxonomy tag: {args.canonical_tag}"
                    )
                state.set_profile_mapping(args.raw_tag, args.canonical_tag)
                print(f"mapped {args.raw_tag} -> {args.canonical_tag}; no Zotero tags changed")
            elif args.profile_command == "export":
                payload = {
                    "mappings": [
                        {
                            "raw_tag": row["raw_tag"],
                            "canonical_tag": row["canonical_tag"],
                            "type": row["mapping_type"],
                        }
                        for row in state.profile_mappings()
                    ]
                }
                args.path.write_text(yaml.safe_dump(payload, sort_keys=False))
                print(f"exported {len(payload['mappings'])} profile mapping(s) to {args.path}")
            else:
                try:
                    payload = yaml.safe_load(args.path.read_text()) or {}
                    mappings = payload["mappings"]
                except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
                    raise SystemExit(f"invalid profile mapping file: {exc}") from exc
                imported = 0
                for mapping in mappings:
                    raw_tag = mapping["raw_tag"]
                    canonical_tag = mapping["canonical_tag"]
                    if canonical_tag not in taxonomy.classifier_tags():
                        raise SystemExit(f"not an eligible canonical taxonomy tag: {canonical_tag}")
                    state.set_profile_mapping(
                        raw_tag, canonical_tag, mapping_type=mapping.get("type", "alias")
                    )
                    imported += 1
                print(f"imported {imported} profile mapping(s); no Zotero tags changed")
        finally:
            state.close()
        return
    if args.command == "taxonomy":
        state = StateStore(config.state.database)
        try:
            if args.history:
                history = state.taxonomy_audit_history(limit=args.history_limit)
                if not history:
                    print("no taxonomy audit history")
                for run in history:
                    print(
                        f"audit {run['id']}: {run['created_at']}; taxonomy v{run['taxonomy_version']}; "
                        f"model {run['embedding_model']}; threshold {run['threshold']:.2f}; "
                        f"findings {run['findings_count']}"
                    )
                return
            try:
                audit = audit_taxonomy(
                    taxonomy, TaxonomyRanker(config.ranking, taxonomy), threshold=args.threshold
                )
            except RankerUnavailable as exc:
                raise SystemExit(f"taxonomy audit unavailable: {exc}") from exc
            findings = [
                (
                    finding.first_tag,
                    finding.second_tag,
                    finding.similarity,
                    finding.relationship.kind if finding.relationship else None,
                    finding.relationship.resolution if finding.relationship else None,
                    finding.status,
                )
                for finding in audit.findings
            ]
            audit_id = state.record_taxonomy_audit(
                taxonomy_version=taxonomy.version,
                taxonomy_digest=audit.taxonomy_digest,
                embedding_model=audit.embedding_model,
                threshold=audit.threshold,
                findings=findings,
            )
            print(
                f"taxonomy audit {audit_id}; model {audit.embedding_model}; threshold {audit.threshold:.2f}; "
                f"{len(audit.findings)} finding(s). Reporting only: no taxonomy or Zotero tags changed."
            )
            for finding in audit.findings:
                suffix = "pending review"
                if finding.relationship:
                    suffix = (
                        f"declared {finding.relationship.kind}; "
                        f"resolution {finding.relationship.resolution}"
                    )
                print(
                    f"  {finding.first_tag} <-> {finding.second_tag}  "
                    f"similarity={finding.similarity:.3f}  {suffix}"
                )
        finally:
            state.close()
        return
    if args.command == "doctor":
        checks = run_checks(config)
        for check in checks:
            print(f"{'OK' if check.ok else 'FAIL':<4} {check.name}: {check.detail}")
        if not all(check.ok for check in checks):
            raise SystemExit(1)
        return
    if args.command == "test":
        run_interactive(config, taxonomy)
        return
    if args.command in {"dry-run", "classify"}:
        _print_preview(
            args.item_key, _isolated_preview(config, taxonomy, args.item_key, force=True)
        )
        return
    organiser = Organiser(config, taxonomy)
    try:
        if args.command == "run":
            signal.signal(signal.SIGTERM, _handle_shutdown)
            organiser.run()
        elif args.command == "once":
            organiser.sync()
            print(f"baseline: {organiser.state.get_baseline_at() or 'not established'}")
        elif args.command == "status":
            summary = organiser.state.summary()
            print(f"last Zotero library version: {organiser.state.get_library_version() or 'none'}")
            print(f"baseline established: {organiser.state.get_baseline_at() or 'no'}")
            print(f"writes enabled: {'yes' if config.safety.write_enabled else 'no'}")
            print(f"only new items: {'yes' if config.safety.only_new_items else 'no'}")
            print(f"max items per cycle: {config.safety.max_items_per_cycle}")
            print(
                f"queue length: {sum(n for s, n in summary.items() if s not in {'organised', 'needs_triage'})}"
            )
            print(
                f"organised: {summary.get('organised', 0)}\nneeds triage: {summary.get('needs_triage', 0)}\nfailed: {summary.get('failed', 0)}"
            )
            print(f"last backup snapshot: {organiser.state.last_backup() or 'none'}")
            backup = repository_status(config.backup)
            print(
                f"backup repository available: {'yes' if backup.available else 'no'} ({backup.detail})"
            )
        elif args.command == "tag-untagged":
            try:
                summary = organiser.tag_untagged(args.count)
            except RuntimeError as exc:
                raise SystemExit(str(exc)) from exc
            print(
                f"selected {summary.selected}/{summary.requested}; "
                f"classified {summary.classified}; tagged {summary.tagged}; "
                f"unchanged {summary.unchanged}; failed {summary.failed}"
            )
        else:
            result = organiser.process(args.item_key, dry_run=False, force=True)
            if result and result.get("skipped"):
                print(f"skipped {args.item_key}: {result['skipped']}")
            elif result:
                print(f"processed {args.item_key}")
    except KeyboardInterrupt:
        return
    finally:
        organiser.close()


if __name__ == "__main__":
    main()
