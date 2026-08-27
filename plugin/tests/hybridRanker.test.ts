import { describe, it, expect } from 'vitest';
import { HybridRanker } from '../src/classifier/hybridRanker.js';
import { parseTaxonomy } from '../src/core/taxonomy.js';
import { DEFAULT_TAXONOMY_YAML } from '../src/defaultTaxonomy.js';

describe('HybridRanker', () => {
  it('computes lexical token overlap correctly', () => {
    const taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);
    const ranker = new HybridRanker(taxonomy);

    const doc = `Title: A Review of Molecular Dynamics Simulations of Electrolyte Solutions
Abstract: This paper presents electrostatic screening, ionic correlations, and free energy calculations in concentrated salt solutions.`;

    const scores = ranker.lexicalScores(doc);

    expect(scores['topic/electrostatics']).toBeGreaterThan(0);
    expect(scores['method/molecular-dynamics']).toBeGreaterThan(0);
    expect(scores['role/review']).toBeGreaterThan(0);
    expect(scores['system/electrolyte']).toBeGreaterThan(0);
  });

  it('ranks candidates using dense and lexical scores with namespace quotas', () => {
    const taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);
    const ranker = new HybridRanker(taxonomy);

    const doc = 'Molecular dynamics simulations of electrolyte solutions and electrostatic screening.';
    const denseScores = {
      'topic/electrostatics': 0.88,
      'method/molecular-dynamics': 0.85,
      'system/electrolyte': 0.79,
      'role/review': 0.65,
    };

    const candidates = ranker.rank(doc, denseScores);

    expect(candidates.length).toBeGreaterThan(0);
    expect(candidates[0].tag).toBe('topic/electrostatics');
    expect(candidates[0].denseScore).toBe(0.88);
    expect(candidates[0].sources.has('dense')).toBe(true);
  });
});
