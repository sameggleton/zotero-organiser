import yaml from 'yaml';
import { z } from 'zod';

export const TagDefinitionSchema = z.object({
  description: z.string().default(''),
  aliases: z.array(z.string()).default([]),
  include: z.array(z.string()).default([]),
  exclude: z.array(z.string()).default([]),
  classifier_eligible: z.boolean().default(true),
  note: z.string().nullable().optional(),
});

export type TagDefinition = z.infer<typeof TagDefinitionSchema>;

export const NamespaceSchema = z.object({
  description: z.string().default(''),
  kind: z.string().default('semantic'),
  classifier_eligible: z.boolean().default(true),
  optional: z.boolean().default(false),
  max_tags: z.number().int().positive(),
  mutually_exclusive: z.boolean().default(false),
  user_managed: z.array(z.string()).default([]),
  constraints: z.record(z.any()).default({}),
  rule: z.string().nullable().optional(),
  values: z.record(TagDefinitionSchema).refine((val) => Object.keys(val).length >= 1, {
    message: 'Namespace must contain at least one tag value',
  }),
});

export type Namespace = z.infer<typeof NamespaceSchema>;

export const ClassifierPolicySchema = z.object({
  semantic_namespaces: z.array(z.string()).default([]),
  workflow_namespaces: z.array(z.string()).default([]),
  human_only_namespaces: z.array(z.string()).default([]),
  rules: z.array(z.string()).default([]),
});

export type ClassifierPolicy = z.infer<typeof ClassifierPolicySchema>;

export const TagRelationshipSchema = z.object({
  tags: z.tuple([z.string(), z.string()]),
  kind: z.enum(['near_duplicate', 'parent_child', 'related']),
  resolution: z
    .enum([
      'keep_both',
      'prefer_first',
      'prefer_second',
      'remap_first_to_second',
      'remap_second_to_first',
    ])
    .default('keep_both'),
  note: z.string().nullable().optional(),
}).refine(
  (rel) => rel.tags[0] !== rel.tags[1],
  { message: 'Relationship tags must be distinct' }
).refine(
  (rel) => rel.kind === 'near_duplicate' || rel.resolution === 'keep_both',
  { message: 'Only near_duplicate relationships may prefer or remap a tag' }
);

export type TagRelationship = z.infer<typeof TagRelationshipSchema>;

export const RawTaxonomySchema = z.object({
  schema_version: z.number().int().default(1),
  version: z.string(),
  description: z.string().default(''),
  conventions: z.record(z.any()).default({}),
  classifier: ClassifierPolicySchema.default({}),
  namespaces: z.record(NamespaceSchema).refine((ns) => Object.keys(ns).length >= 1, {
    message: 'Taxonomy must have at least one namespace',
  }),
  relationships: z.array(TagRelationshipSchema).default([]),
});

export type RawTaxonomy = z.infer<typeof RawTaxonomySchema>;

export class Taxonomy {
  public schemaVersion: number;
  public version: string;
  public description: string;
  public conventions: Record<string, any>;
  public classifier: ClassifierPolicy;
  public namespaces: Record<string, Namespace>;
  public relationships: TagRelationship[];

  constructor(data: RawTaxonomy) {
    this.schemaVersion = data.schema_version;
    this.version = data.version;
    this.description = data.description;
    this.conventions = data.conventions;
    this.classifier = data.classifier;
    this.namespaces = data.namespaces;
    this.relationships = data.relationships;

    this.validate();
  }

  private validate(): void {
    const semanticSet = new Set(this.classifier.semantic_namespaces);
    const namespaceKeys = Object.keys(this.namespaces);

    for (const sem of semanticSet) {
      if (!this.namespaces[sem]) {
        throw new Error(`Classifier names namespace not defined: ${sem}`);
      }
      if (this.namespaces[sem].kind !== 'semantic') {
        throw new Error(`Classifier semantic namespace is not semantic: ${sem}`);
      }
    }

    for (const [namespace, rule] of Object.entries(this.namespaces)) {
      if (!namespace || namespace.includes('/') || namespace !== namespace.trim()) {
        throw new Error(`Namespace names must be non-empty canonical segments: '${namespace}'`);
      }
      for (const label of Object.keys(rule.values)) {
        if (!label || label.includes('/') || label !== label.trim()) {
          throw new Error(`Invalid label: '${namespace}/${label}'`);
        }
      }
      for (const managed of rule.user_managed) {
        if (!rule.values[managed]) {
          throw new Error(`Namespace ${namespace} refers to undefined user_managed value: ${managed}`);
        }
      }
    }

    const allTags = this.tags();
    const seenPairs = new Set<string>();

    for (const rel of this.relationships) {
      for (const tag of rel.tags) {
        if (!allTags.has(tag)) {
          throw new Error(`Relationship refers to undefined tag: ${tag}`);
        }
      }
      const pairKey = [...rel.tags].sort().join('<->');
      if (seenPairs.has(pairKey)) {
        throw new Error(`Duplicate relationship for tags: ${rel.tags[0]} and ${rel.tags[1]}`);
      }
      seenPairs.add(pairKey);
    }
  }

  public tags(): Set<string> {
    const res = new Set<string>();
    for (const [space, rule] of Object.entries(this.namespaces)) {
      for (const label of Object.keys(rule.values)) {
        res.add(`${space}/${label}`);
      }
    }
    return res;
  }

  public classifierTags(): Set<string> {
    const res = new Set<string>();
    const semanticAllowed = new Set(this.classifier.semantic_namespaces);
    const hasSemanticFilter = semanticAllowed.size > 0;

    for (const [space, rule] of Object.entries(this.namespaces)) {
      if (!rule.classifier_eligible) continue;
      if (hasSemanticFilter && !semanticAllowed.has(space)) continue;

      for (const [label, def] of Object.entries(rule.values)) {
        if (def.classifier_eligible) {
          res.add(`${space}/${label}`);
        }
      }
    }
    return res;
  }

  public validateTags(tags: string[]): void {
    const unique = new Set(tags);
    if (unique.size !== tags.length) {
      throw new Error('Duplicate classifier tags');
    }

    const allowed = this.classifierTags();
    for (const tag of tags) {
      if (!allowed.has(tag)) {
        throw new Error(`Classifier tag is not an eligible canonical taxonomy tag: ${tag}`);
      }
    }

    for (const [namespace, rule] of Object.entries(this.namespaces)) {
      const count = tags.filter((t) => t.startsWith(`${namespace}/`)).length;
      if (count > rule.max_tags) {
        throw new Error(`Too many ${namespace} tags: got ${count}, max is ${rule.max_tags}`);
      }
      if (rule.mutually_exclusive && count > 1) {
        throw new Error(`Mutually exclusive namespace ${namespace} has multiple tags`);
      }
    }
  }

  public promptDefinitions(allowedTags?: Set<string>): string {
    const allowed = this.classifierTags();
    const blocks: string[] = [];

    for (const [namespace, rule] of Object.entries(this.namespaces)) {
      const definitions: string[] = [];
      for (const [label, def] of Object.entries(rule.values)) {
        const tag = `${namespace}/${label}`;
        if (!allowed.has(tag)) continue;
        if (allowedTags && !allowedTags.has(tag)) continue;

        let guidance = def.description;
        if (def.aliases && def.aliases.length > 0) {
          guidance += ` Recognition aliases (never emit): ${def.aliases.join(', ')}.`;
        }
        if (def.include && def.include.length > 0) {
          guidance += ` Include: ${def.include.join(', ')}.`;
        }
        if (def.exclude && def.exclude.length > 0) {
          guidance += ` Exclude: ${def.exclude.join(', ')}.`;
        }
        definitions.push(`- ${tag}: ${guidance}`);
      }

      if (definitions.length > 0) {
        const suffix = rule.optional ? ', optional' : '';
        blocks.push(`${namespace} (at most ${rule.max_tags}${suffix}):\n${definitions.join('\n')}`);
      }
    }
    return blocks.join('\n\n');
  }

  public rankingTexts(): Record<string, string> {
    const texts: Record<string, string> = {};
    const allowed = this.classifierTags();

    for (const [namespace, rule] of Object.entries(this.namespaces)) {
      for (const [label, def] of Object.entries(rule.values)) {
        const tag = `${namespace}/${label}`;
        if (!allowed.has(tag)) continue;

        const parts = [tag, def.description, ...(def.aliases || []), ...(def.include || [])];
        texts[tag] = parts.filter(Boolean).join('. ');
      }
    }
    return texts;
  }

  public localClassifierHypotheses(): Record<string, { positive: string; exclusions: string[] }> {
    const hypotheses: Record<string, { positive: string; exclusions: string[] }> = {};
    const allowed = this.classifierTags();

    for (const [namespace, rule] of Object.entries(this.namespaces)) {
      for (const [label, def] of Object.entries(rule.values)) {
        const tag = `${namespace}/${label}`;
        if (!allowed.has(tag)) continue;

        let positive = `This scientific paper substantively studies ${tag}: ${def.description}`;
        if (def.include && def.include.length > 0) {
          positive += ` Relevant scope includes: ${def.include.join(', ')}.`;
        }
        const exclusions = (def.exclude || []).map(
          (excl) => `For tag ${tag}, this paper is in an excluded scope: ${excl}.`
        );
        hypotheses[tag] = { positive, exclusions };
      }
    }
    return hypotheses;
  }

  public relationshipFor(first: string, second: string): TagRelationship | null {
    const pair = new Set([first, second]);
    for (const rel of this.relationships) {
      if (rel.tags[0] === first && rel.tags[1] === second) return rel;
      if (rel.tags[0] === second && rel.tags[1] === first) return rel;
    }
    return null;
  }
}

export interface ValidationResult {
  valid: boolean;
  tagCount: number;
  namespaceCount: number;
  semanticNamespaceCount: number;
  version?: string;
  error?: string;
}

export function validateTaxonomyYaml(yamlText: string): ValidationResult {
  try {
    if (!yamlText || !yamlText.trim()) {
      return {
        valid: false,
        tagCount: 0,
        namespaceCount: 0,
        semanticNamespaceCount: 0,
        error: 'Taxonomy YAML cannot be empty.',
      };
    }
    const taxonomy = parseTaxonomy(yamlText);
    const tags = taxonomy.tags();
    const namespaces = Object.keys(taxonomy.namespaces);
    const semanticNamespaces = taxonomy.classifier.semantic_namespaces;
    return {
      valid: true,
      tagCount: tags.size,
      namespaceCount: namespaces.length,
      semanticNamespaceCount: semanticNamespaces.length,
      version: taxonomy.version,
    };
  } catch (err: any) {
    let msg = err?.message || String(err);
    if (err?.issues && Array.isArray(err.issues)) {
      msg = err.issues.map((i: any) => `${i.path.join('.')}: ${i.message}`).join('; ');
    }
    return {
      valid: false,
      tagCount: 0,
      namespaceCount: 0,
      semanticNamespaceCount: 0,
      error: msg,
    };
  }
}

export function parseTaxonomy(yamlText: string): Taxonomy {
  const parsed = yaml.parse(yamlText);
  const validated = RawTaxonomySchema.parse(parsed);
  return new Taxonomy(validated);
}

