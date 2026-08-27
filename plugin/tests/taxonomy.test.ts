import { describe, it, expect } from 'vitest';
import { parseTaxonomy, Taxonomy } from '../src/core/taxonomy.js';
import { DEFAULT_TAXONOMY_YAML } from '../src/defaultTaxonomy.js';

describe('Taxonomy', () => {
  it('parses the default starter taxonomy correctly', () => {
    const taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);
    expect(taxonomy.version).toBe('1.2.0');
    expect(taxonomy.namespaces).toHaveProperty('status');
    expect(taxonomy.namespaces).toHaveProperty('priority');
    expect(taxonomy.namespaces).toHaveProperty('role');
    expect(taxonomy.namespaces).toHaveProperty('topic');
    expect(taxonomy.namespaces).toHaveProperty('system');
    expect(taxonomy.namespaces).toHaveProperty('method');
    expect(taxonomy.namespaces).toHaveProperty('type');
  });

  it('correctly filters classifier-eligible semantic tags', () => {
    const taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);
    const classifierTags = taxonomy.classifierTags();

    // status and priority should NOT be in classifierTags
    expect(classifierTags.has('status/to-read')).toBe(false);
    expect(classifierTags.has('priority/core')).toBe(false);

    // role, topic, system, method, and type tags SHOULD be in classifierTags
    expect(classifierTags.has('role/computational')).toBe(true);
    expect(classifierTags.has('role/review')).toBe(true);
    expect(classifierTags.has('topic/underscreening')).toBe(true);
    expect(classifierTags.has('topic/electrostatics')).toBe(true);
    expect(classifierTags.has('topic/parameterisation')).toBe(true);
    expect(classifierTags.has('topic/polymer-conformation')).toBe(true);
    expect(classifierTags.has('topic/selectivity')).toBe(true);
    expect(classifierTags.has('system/rare-earth')).toBe(true);
    expect(classifierTags.has('system/electrolyte')).toBe(true);
    expect(classifierTags.has('system/mineral')).toBe(true);
    expect(classifierTags.has('method/graph-neural-network')).toBe(true);
    expect(classifierTags.has('method/spectroscopy')).toBe(true);
    expect(classifierTags.has('type/software')).toBe(true);
  });

  it('validates tags against max_tags and eligibility constraints', () => {
    const taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);

    // Valid tags
    expect(() => {
      taxonomy.validateTags(['role/review', 'topic/electrostatics', 'topic/underscreening']);
    }).not.toThrow();

    // Ineligible tag throws
    expect(() => {
      taxonomy.validateTags(['status/reading']);
    }).toThrow(/not an eligible canonical taxonomy tag/);

    // Exceeding max_tags throws (role max is 3)
    expect(() => {
      taxonomy.validateTags(['role/review', 'role/theory', 'role/dataset', 'role/computational']);
    }).toThrow(/Too many role tags/);

    // Duplicates throw
    expect(() => {
      taxonomy.validateTags(['role/review', 'role/review']);
    }).toThrow(/Duplicate classifier tags/);
  });

  it('generates prompt definitions correctly', () => {
    const taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);
    const prompt = taxonomy.promptDefinitions();

    expect(prompt).toContain('role (at most 3):');
    expect(prompt).toContain('role/review: Synthesises an existing body of literature');
    expect(prompt).toContain('topic/underscreening: Anomalously long-range screening');
    expect(prompt).toContain('Include: narrative review, critical review.');
    expect(prompt).toContain('Exclude: brief background section in a primary research article.');
    expect(prompt).not.toContain('status');
  });

  it('generates NLI hypotheses with positive and exclusion scopes', () => {
    const taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);
    const hypotheses = taxonomy.localClassifierHypotheses();

    expect(hypotheses).toHaveProperty('role/review');
    expect(hypotheses['role/review'].positive).toContain('This scientific paper substantively studies role/review');
    expect(hypotheses['role/review'].exclusions).toHaveLength(1);
    expect(hypotheses['role/review'].exclusions[0]).toContain('brief background section in a primary research article');
  });

  it('enforces distinct tags on relationships', () => {
    const invalidYaml = `
schema_version: 1
version: "1.0.0"
namespaces:
  topic:
    kind: semantic
    max_tags: 2
    values:
      ai:
        description: "AI"
relationships:
  - tags: ["topic/ai", "topic/ai"]
    kind: "near_duplicate"
`;
    expect(() => parseTaxonomy(invalidYaml)).toThrow();
  });
});
