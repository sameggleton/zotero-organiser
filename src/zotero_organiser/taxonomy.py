from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TagDefinition(BaseModel):
    """One canonical value. Aliases are recognition hints, never valid output."""

    model_config = ConfigDict(extra="forbid")
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    classifier_eligible: bool = True
    note: str | None = None


class Namespace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = ""
    kind: str = "semantic"
    classifier_eligible: bool = True
    optional: bool = False
    max_tags: int = Field(gt=0)
    mutually_exclusive: bool = False
    user_managed: list[str] = Field(default_factory=list)
    constraints: dict[str, object] = Field(default_factory=dict)
    rule: str | None = None
    values: dict[str, TagDefinition] = Field(min_length=1)


class ClassifierPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    semantic_namespaces: set[str] = Field(default_factory=set)
    workflow_namespaces: set[str] = Field(default_factory=set)
    human_only_namespaces: set[str] = Field(default_factory=set)
    rules: list[str] = Field(default_factory=list)


class TagRelationship(BaseModel):
    """A reviewed semantic relationship between two canonical taxonomy tags.

    Relationships are declarative at present. They document a human decision
    for taxonomy audits; classification does not yet act on them.
    """

    model_config = ConfigDict(extra="forbid")
    tags: tuple[str, str]
    kind: Literal["near_duplicate", "parent_child", "related"]
    resolution: Literal[
        "keep_both",
        "prefer_first",
        "prefer_second",
        "remap_first_to_second",
        "remap_second_to_first",
    ] = "keep_both"
    note: str | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> "TagRelationship":
        if self.tags[0] == self.tags[1]:
            raise ValueError("relationship tags must be distinct")
        if self.kind != "near_duplicate" and self.resolution != "keep_both":
            raise ValueError("only near_duplicate relationships may prefer or remap a tag")
        return self


class Taxonomy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    version: str
    description: str = ""
    conventions: dict[str, object] = Field(default_factory=dict)
    classifier: ClassifierPolicy = Field(default_factory=ClassifierPolicy)
    namespaces: dict[str, Namespace] = Field(min_length=1)
    relationships: list[TagRelationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_labels(self) -> "Taxonomy":
        unknown = self.classifier.semantic_namespaces - set(self.namespaces)
        if unknown:
            raise ValueError(f"classifier names namespaces not defined: {sorted(unknown)}")
        non_semantic = {
            namespace
            for namespace in self.classifier.semantic_namespaces
            if self.namespaces[namespace].kind != "semantic"
        }
        if non_semantic:
            raise ValueError(
                f"classifier semantic namespaces are not semantic: {sorted(non_semantic)}"
            )
        for namespace, rule in self.namespaces.items():
            if not namespace or "/" in namespace or namespace != namespace.strip():
                raise ValueError("namespace names must be non-empty canonical segments")
            for label in rule.values:
                if not label or "/" in label or label != label.strip():
                    raise ValueError(f"invalid label {namespace}/{label}")
            if set(rule.user_managed) - set(rule.values):
                raise ValueError(f"namespace {namespace} refers to undefined values")
        tags = self.tags()
        seen_relationships: set[frozenset[str]] = set()
        for relationship in self.relationships:
            unknown_tags = set(relationship.tags) - tags
            if unknown_tags:
                raise ValueError(f"relationship refers to undefined tags: {sorted(unknown_tags)}")
            pair = frozenset(relationship.tags)
            if pair in seen_relationships:
                raise ValueError(f"duplicate relationship for tags: {sorted(pair)}")
            seen_relationships.add(pair)
        return self

    def tags(self) -> set[str]:
        return {
            f"{space}/{label}" for space, rule in self.namespaces.items() for label in rule.values
        }

    def classifier_tags(self) -> set[str]:
        """Canonical tags the model is allowed to return, excluding workflow tags."""
        configured = self.classifier.semantic_namespaces
        return {
            f"{space}/{label}"
            for space, rule in self.namespaces.items()
            if rule.classifier_eligible and (not configured or space in configured)
            for label, definition in rule.values.items()
            if definition.classifier_eligible
        }

    def validate_tags(self, tags: list[str]) -> None:
        if len(tags) != len(set(tags)):
            raise ValueError("duplicate classifier tags")
        invalid = set(tags) - self.classifier_tags()
        if invalid:
            raise ValueError(
                f"classifier tags are not eligible canonical taxonomy tags: {sorted(invalid)}"
            )
        for namespace, rule in self.namespaces.items():
            count = sum(tag.startswith(namespace + "/") for tag in tags)
            if count > rule.max_tags:
                raise ValueError(f"too many {namespace} tags")
            if rule.mutually_exclusive and count > 1:
                raise ValueError(f"mutually exclusive namespace has multiple {namespace} tags")

    def prompt_definitions(self, allowed_tags: set[str] | None = None) -> str:
        """Policy-rich prompt text containing only model-eligible choices."""
        blocks: list[str] = []
        allowed = self.classifier_tags()
        if allowed_tags is not None:
            allowed &= allowed_tags
        for namespace, rule in self.namespaces.items():
            definitions = []
            for label, definition in rule.values.items():
                tag = f"{namespace}/{label}"
                if tag not in allowed:
                    continue
                guidance = definition.description
                if definition.aliases:
                    guidance += (
                        f" Recognition aliases (never emit): {', '.join(definition.aliases)}."
                    )
                if definition.include:
                    guidance += f" Include: {', '.join(definition.include)}."
                if definition.exclude:
                    guidance += f" Exclude: {', '.join(definition.exclude)}."
                definitions.append(f"- {tag}: {guidance}")
            if definitions:
                suffix = ", optional" if rule.optional else ""
                blocks.append(
                    "\n".join([f"{namespace} (at most {rule.max_tags}{suffix}):", *definitions])
                )
        return "\n\n".join(blocks)

    def ranking_texts(self) -> dict[str, str]:
        """Return model-eligible tag definitions as plain text for local ranking."""
        texts: dict[str, str] = {}
        allowed = self.classifier_tags()
        for namespace, rule in self.namespaces.items():
            for label, definition in rule.values.items():
                tag = f"{namespace}/{label}"
                if tag not in allowed:
                    continue
                parts = [tag, definition.description, *definition.aliases, *definition.include]
                texts[tag] = ". ".join(part for part in parts if part)
        return texts

    def local_classifier_hypotheses(self) -> dict[str, tuple[str, tuple[str, ...]]]:
        """Return positive and exclusion hypotheses for local NLI scoring."""
        hypotheses: dict[str, tuple[str, tuple[str, ...]]] = {}
        allowed = self.classifier_tags()
        for namespace, rule in self.namespaces.items():
            for label, definition in rule.values.items():
                tag = f"{namespace}/{label}"
                if tag not in allowed:
                    continue
                positive = (
                    f"This scientific paper substantively studies {tag}: {definition.description}"
                )
                if definition.include:
                    positive += f" Relevant scope includes: {', '.join(definition.include)}."
                exclusions = tuple(
                    f"For tag {tag}, this paper is in an excluded scope: {exclusion}."
                    for exclusion in definition.exclude
                )
                hypotheses[tag] = positive, exclusions
        return hypotheses

    def relationship_for(self, first: str, second: str) -> TagRelationship | None:
        """Return the declared relationship for an unordered pair of tags."""
        pair = frozenset((first, second))
        return next(
            (
                relationship
                for relationship in self.relationships
                if frozenset(relationship.tags) == pair
            ),
            None,
        )


def load_taxonomy(path: Path) -> Taxonomy:
    path = path.expanduser()
    with path.open() as handle:
        return Taxonomy.model_validate(yaml.safe_load(handle))


def packaged_taxonomy_path() -> Path:
    """Starter YAML shipped next to this module. Do not edit it in place."""
    return Path(__file__).with_name("taxonomy.yml")


def is_packaged_taxonomy(path: Path) -> bool:
    try:
        return path.expanduser().resolve() == packaged_taxonomy_path().resolve()
    except OSError:
        return False


def install_user_taxonomy(
    destination: Path, source: Path | None = None, *, force: bool = False
) -> Path:
    """Copy a valid taxonomy to a user-owned path. Never overwrites the packaged seed."""
    destination = destination.expanduser()
    source = (source or packaged_taxonomy_path()).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"taxonomy source not found: {source}")
    load_taxonomy(source)
    if is_packaged_taxonomy(destination):
        raise ValueError("refusing to overwrite the packaged starter; choose a user path")
    if destination.exists() and not force:
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text()
    with tempfile.NamedTemporaryFile(
        "w", dir=destination.parent, delete=False, suffix=".yml"
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(destination)
    return destination


AVAILABLE_PROFILES = (
    "general-scholar",
    "mathematics-statistics",
    "computer-information-sciences",
    "physics-astronomy",
    "chemistry-molecular-sciences",
    "biological-sciences",
    "biomedical-clinical-sciences",
    "health-sciences",
    "agricultural-veterinary-food",
    "earth-atmospheric-ocean",
    "environmental-sustainability",
    "engineering-technology",
    "built-environment-architecture",
    "psychology-cognitive-sciences",
    "economics",
    "business-management-organisations",
    "society-politics-human-geography",
    "education-learning-sciences",
    "law-criminology-justice",
    "language-communication-culture",
    "literature-writing",
    "history-heritage-archaeology",
    "philosophy-ethics-religious",
    "creative-arts-design",
    "indigenous-studies",
)


def profiles_directory() -> Path:
    """Return the directory containing researched domain taxonomy profiles."""
    pkg_dir = Path(__file__).resolve().parent / "profiles"
    if pkg_dir.is_dir():
        return pkg_dir
    repo_dir = Path(__file__).resolve().parents[2] / "examples" / "taxonomies" / "profiles"
    if repo_dir.is_dir():
        return repo_dir
    return pkg_dir


def list_profiles() -> list[tuple[str, Path]]:
    """Return list of (profile_id, path) for all available domain profiles."""
    p_dir = profiles_directory()
    profiles: list[tuple[str, Path]] = []
    for pid in AVAILABLE_PROFILES:
        p_path = p_dir / f"{pid}.yml"
        if p_path.is_file():
            profiles.append((pid, p_path))
    if p_dir.is_dir():
        for item in sorted(p_dir.glob("*.yml")):
            pid = item.stem
            if not any(existing_id == pid for existing_id, _ in profiles):
                profiles.append((pid, item))
    return profiles


def get_profile_path(profile_id: str) -> Path:
    """Return the Path to a domain profile YAML by profile_id."""
    clean_id = profile_id.removesuffix(".yml")
    p_dir = profiles_directory()
    path = p_dir / f"{clean_id}.yml"
    if not path.is_file():
        raise FileNotFoundError(
            f"unknown profile '{profile_id}'. Available profiles: {', '.join(AVAILABLE_PROFILES)}"
        )
    return path


def load_profile(profile_id: str) -> Taxonomy:
    """Load a domain profile by profile_id."""
    return load_taxonomy(get_profile_path(profile_id))
