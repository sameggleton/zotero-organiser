from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from .backup import repository_status, restic_backup, save_prewrite
from .classify import Classifier, input_hash
from .config import Config
from .local_classifier import LocalNLIClassifier
from .personalization import PersonalizationRanker, build_profile
from .policy import decide
from .ranking import RankerUnavailable, TaxonomyRanker
from .reconcile import reconcile
from .state import StateStore, now
from .taxonomy import Taxonomy
from .webdav import attachment_ready, storage_available
from .zotero import LocalWriteDenied, VersionConflict, ZoteroClient, eligible, tags

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchSummary:
    requested: int
    selected: int
    classified: int
    tagged: int
    unchanged: int
    failed: int


class Organiser:
    def __init__(self, config: Config, taxonomy: Taxonomy):
        self.config, self.taxonomy = config, taxonomy
        self.state = StateStore(config.state.database)
        self.zotero = ZoteroClient(
            config.zotero,
            server_id=self.state.get_zotero_server_id(),
            local_api_key=self.state.get_local_api_key(),
        )
        ranker = TaxonomyRanker(config.ranking, taxonomy) if config.ranking.enabled else None
        local_classifier = (
            LocalNLIClassifier(config.local_classifier, taxonomy)
            if config.local_classifier.enabled
            else None
        )
        personalization = (
            PersonalizationRanker(config.personalization, taxonomy, self.state, ranker)
            if config.personalization.enabled and ranker is not None
            else None
        )
        self.classifier = Classifier(
            config.classification, taxonomy, ranker, local_classifier, personalization
        )
        self._cycle_snapshot: str | None = None

    def close(self) -> None:
        self.zotero.close()
        self.state.close()

    def sync(self) -> None:
        self._cycle_snapshot = None
        prior_version = self.state.get_library_version()
        # Web API versions are unrelated to local object versions. A missing
        # local server identity therefore always starts a fresh local baseline.
        if self.state.get_baseline_at() is None or self.state.get_zotero_server_id() is None:
            # Capture the temporal boundary before reading the API cursor so an
            # import racing this call is treated as new, never silently lost.
            baseline_at = now()
            version = self.zotero.library_version()
            self._persist_server_identity()
            baseline_at = self.state.establish_baseline(version, baseline_at=baseline_at)
            LOG.info(
                "established Zotero baseline version=%s at %s; no existing items queued",
                version,
                baseline_at,
            )
            if self.config.personalization.enabled and self.classifier.ranker is not None:
                try:
                    profile = build_profile(self.state, self.zotero, self.classifier.ranker)
                except RankerUnavailable as exc:
                    LOG.warning("could not build local preference profile: %s", exc)
                else:
                    LOG.info(
                        "built local preference profile from %s tagged items and %s tags",
                        profile.item_count,
                        profile.tag_count,
                    )
            return
        assert prior_version is not None
        items, version = self.zotero.changed_items(prior_version)
        self._persist_server_identity()
        changed_keys: list[str] = []
        for item in items:
            if eligible(item, self.config.daemon.allowed_item_types):
                self.state.discover(item["key"], item["version"])
                changed_keys.append(item["key"])
        if not self.config.safety.write_enabled:
            # Discover for a later write-enabled cycle, but do not classify.
            LOG.info("writes disabled; skipping classification for this cycle")
            self.state.set_library_version(version)
            return
        # Pending items keep discovery order. Alphabetically sorting keys starved
        # later discoveries whenever leftover classifying rows occupied the cap.
        seen: set[str] = set()
        queue: list[str] = []
        for key in self.state.pending_keys():
            queue.append(key)
            seen.add(key)
        for key in changed_keys:
            if key not in seen:
                queue.append(key)
                seen.add(key)
        # The API cursor can safely advance even when a single item fails:
        # pending local state is explicitly retried in every later cycle.
        for key in queue[: self.config.safety.max_items_per_cycle]:
            try:
                self.process(key)
            except Exception as exc:
                stored = self.state.get(key)
                if stored:
                    self.state.record_error(stored, str(exc))
                LOG.exception("failed to process item %s", key)
        # Detection is safe locally before this checkpoint; any incomplete item remains queued.
        self.state.set_library_version(version)

    def process(
        self,
        key: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        allow_prebaseline: bool = False,
        require_semantically_untagged: bool = False,
    ) -> dict | None:
        started = time.monotonic()
        stored = self.state.get(key)
        item = self.zotero.get_item(key)
        if not eligible(item, self.config.daemon.allowed_item_types):
            return None
        if require_semantically_untagged and tags(item) & self.taxonomy.classifier_tags():
            return {"skipped": "already has taxonomy tags"}
        baseline_at = self.state.get_baseline_at()
        # Dry-runs are deliberately allowed for old papers: they cannot mutate
        # Zotero and are useful for evaluating representative library items.
        if (
            self.config.safety.only_new_items
            and not dry_run
            and not allow_prebaseline
            and not _is_new_since(item, baseline_at)
        ):
            LOG.info("skipping pre-baseline item %s due to only_new_items", key)
            return {"skipped": "pre-baseline item"}
        if not dry_run and not self.config.safety.write_enabled:
            LOG.info("skipping item %s because writes are disabled", key)
            return {"skipped": "writes disabled"}
        stored = stored or self.state.discover(key, item["version"])
        children = self.zotero.children(key)
        age = (
            datetime.now(UTC)
            - datetime.fromisoformat(
                (self.state.discovered_at(key) or now()).replace("Z", "+00:00")
            )
        ).total_seconds()
        if children and age < self.config.daemon.settle_seconds:
            stored.state = "waiting_for_attachment"
            self.state.upsert(stored)
            return None
        attachment_path = self.config.attachments.path
        if not storage_available(attachment_path):
            stored.state = "waiting_for_attachment"
            self.state.upsert(stored, last_error="attachment storage unavailable")
            return None
        if not attachment_ready(attachment_path, children):
            stored.state = (
                "waiting_for_attachment"
                if age < self.config.daemon.max_attachment_wait_seconds
                else "attachment_timeout"
            )
            self.state.upsert(
                stored,
                last_error=None
                if age < self.config.daemon.max_attachment_wait_seconds
                else "attachment sync did not settle",
            )
            return None
        if self.config.safety.write_enabled and self.config.safety.require_backup:
            backup_status = repository_status(self.config.backup)
            if not backup_status.available:
                stored.state = "waiting_for_backup"
                self.state.upsert(stored, last_error=backup_status.detail)
                return None
        manual = tags(item) - stored.auto_tags
        digest = input_hash(item, self.taxonomy.version, self.classifier.version, manual)
        if (
            not force
            and digest == stored.input_hash
            and stored.state in {"organised", "needs_triage"}
        ):
            return {"skipped": "unchanged"}
        if self.config.safety.write_enabled and not dry_run:
            self.zotero.require_local_write_support()
        LOG.info("timing item=%s phase=preflight seconds=%.3f", key, time.monotonic() - started)
        stored.state = "classifying"
        self.state.upsert(stored, ready_at=now())
        result = self.classifier.classify(item)
        scores = {label.tag: label.confidence for label in result.tags}
        decision = decide(
            scores,
            auto_threshold=self.config.classification.auto_accept_threshold,
            triage_threshold=self.config.classification.triage_threshold,
            suppressed=stored.suppressed_tags,
        )
        plan = reconcile(
            tags(item),
            stored.auto_tags,
            decision.accepted,
            suppressed_tags=stored.suppressed_tags,
            allow_tag_removal=self.config.safety.allow_tag_removal,
        )
        response = {"item": item, "scores": scores, "decision": decision, "tags": plan.tags}
        if dry_run or not self.config.safety.write_enabled:
            if not dry_run:
                response["skipped"] = "writes disabled"
            LOG.info("timing item=%s phase=process seconds=%.3f", key, time.monotonic() - started)
            return response
        self._ensure_local_write_authorization()
        snapshot = self._backup_once() if self.config.safety.require_backup else None
        current = self.zotero.get_item(key)
        if require_semantically_untagged and tags(current) & self.taxonomy.classifier_tags():
            return {"skipped": "taxonomy tags added during classification"}
        # Reconcile again against current user edits just before mutation.
        plan = reconcile(
            tags(current),
            stored.auto_tags,
            decision.accepted,
            suppressed_tags=stored.suppressed_tags,
            allow_tag_removal=self.config.safety.allow_tag_removal,
        )
        prewrite = save_prewrite(self.config.backup.prewrite_dir, current)
        write_started = time.monotonic()
        try:
            written = self._put_tags(current, plan.tags)
        except VersionConflict:
            current = self.zotero.get_item(key)
            if require_semantically_untagged and tags(current) & self.taxonomy.classifier_tags():
                return {"skipped": "taxonomy tags added during classification"}
            plan = reconcile(
                tags(current),
                stored.auto_tags,
                decision.accepted,
                suppressed_tags=stored.suppressed_tags,
                allow_tag_removal=self.config.safety.allow_tag_removal,
            )
            prewrite = save_prewrite(self.config.backup.prewrite_dir, current)
            written = self._put_tags(current, plan.tags)
        finally:
            LOG.info(
                "timing item=%s phase=zotero_write seconds=%.3f",
                key,
                time.monotonic() - write_started,
            )
        self._persist_server_identity()
        stored.zotero_version = written.get("version", current["version"])
        stored.input_hash, stored.auto_tags, stored.suppressed_tags = (
            digest,
            plan.auto_tags,
            stored.suppressed_tags | plan.suppressed_tags,
        )
        stored.state = "needs_triage" if decision.held or not decision.accepted else "organised"
        self.state.upsert(
            stored,
            classified_at=now(),
            taxonomy_version=self.taxonomy.version,
            classifier_version=self.classifier.version,
            backup_snapshot=snapshot,
            prewrite_path=str(prewrite),
            last_error=None,
        )
        LOG.info("timing item=%s phase=process seconds=%.3f", key, time.monotonic() - started)
        return response

    def tag_untagged(self, count: int) -> BatchSummary:
        """Classify up to count items that have no classifier-eligible taxonomy tags."""
        if not self.config.safety.write_enabled:
            raise RuntimeError("tag-untagged requires safety.write_enabled: true")
        if self.config.classification.enabled:
            LOG.warning(
                "tag-untagged can send title, abstract, item type, publication title, "
                "and existing tags to %s because remote classification is enabled",
                self.config.classification.endpoint,
            )
        self.zotero.require_local_write_support()
        self._cycle_snapshot = None
        selected = classified = tagged = unchanged = failed = 0
        classifier_tags = self.taxonomy.classifier_tags()
        for item in self.zotero.top_items():
            if selected >= count:
                break
            if not eligible(item, self.config.daemon.allowed_item_types):
                continue
            if tags(item) & classifier_tags:
                continue
            stored = self.state.get(item["key"])
            if stored and stored.state in {"organised", "needs_triage"}:
                continue
            selected += 1
            key = item["key"]
            try:
                result = self.process(
                    key,
                    force=True,
                    allow_prebaseline=True,
                    require_semantically_untagged=True,
                )
            except Exception as exc:
                failed += 1
                stored = self.state.get(key)
                if stored:
                    self.state.record_error(stored, str(exc))
                LOG.exception("failed to classify untagged item %s", key)
                continue
            if not result or "scores" not in result:
                unchanged += 1
                continue
            classified += 1
            applied = set(result["tags"]) & classifier_tags
            if applied:
                tagged += 1
                LOG.info("tagged item %s with %s", key, ", ".join(sorted(applied)))
            else:
                unchanged += 1
                candidates = (
                    ", ".join(
                        f"{tag}={confidence:.2f}"
                        for tag, confidence in sorted(
                            result["scores"].items(), key=lambda entry: (-entry[1], entry[0])
                        )
                    )
                    or "none"
                )
                LOG.info(
                    "classified item %s; no taxonomy tags met the acceptance threshold; "
                    "top candidates: %s",
                    key,
                    candidates,
                )
        return BatchSummary(count, selected, classified, tagged, unchanged, failed)

    def _backup_once(self) -> str:
        if self._cycle_snapshot is None:
            LOG.info("backup started")
            started = time.monotonic()
            self._cycle_snapshot = restic_backup(
                self.config.backup.repository, self.config.backup.source
            )
            LOG.info(
                "backup completed snapshot=%s seconds=%.3f",
                self._cycle_snapshot,
                time.monotonic() - started,
            )
        return self._cycle_snapshot

    def _persist_server_identity(self) -> None:
        if self.zotero.server_id:
            self.state.set_zotero_server_id(self.zotero.server_id)

    def _ensure_local_write_authorization(self) -> None:
        if self.zotero.local_api_key:
            return
        key = self.zotero.authorize_write()
        self._persist_server_identity()
        self.state.set_local_api_key(key)

    def _put_tags(self, item: dict, desired: set[str]) -> dict:
        try:
            return self.zotero.update_tags(item, desired)
        except LocalWriteDenied:
            # A single-use local authorization may have been consumed, or the
            # user may have cleared remembered authorizations in Zotero.
            self.state.clear_local_api_key()
            self.zotero.local_api_key = None
            self._ensure_local_write_authorization()
            return self.zotero.update_tags(item, desired)

    def run(self) -> None:
        while True:
            try:
                self.sync()
            except Exception:
                LOG.exception("synchronisation cycle failed")
            time.sleep(self.config.daemon.poll_interval_seconds)


def _is_new_since(item: dict, baseline_at: str | None) -> bool:
    """Only dateAdded after the local baseline may enter an only-new queue."""
    if baseline_at is None:
        return False
    date_added = item.get("data", {}).get("dateAdded")
    if not date_added:
        return False
    try:
        return datetime.fromisoformat(date_added.replace("Z", "+00:00")) >= datetime.fromisoformat(
            baseline_at.replace("Z", "+00:00")
        )
    except ValueError:
        LOG.warning("item %s has an unparseable dateAdded", item.get("key"))
        return False
