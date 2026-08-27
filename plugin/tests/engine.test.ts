import { describe, expect, it, beforeEach } from 'vitest';
import { ClassifierEngine } from '../src/classifier/engine.js';
import { PreferenceMemory } from '../src/classifier/preferenceMemory.js';
import { parseTaxonomy } from '../src/core/taxonomy.js';
import { DEFAULT_TAXONOMY_YAML } from '../src/defaultTaxonomy.js';
import { computeDocumentVector } from '../src/core/document.js';

describe('ClassifierEngine (PreferenceMemory & Residuals Integration)', () => {
  let taxonomy: any;
  let prefMem: PreferenceMemory;
  let engine: ClassifierEngine;

  beforeEach(() => {
    taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);
    prefMem = new PreferenceMemory({ alpha: 0.12, beta: 0.15, maxResidual: 0.18 });
    engine = new ClassifierEngine(
      taxonomy,
      {
        mode: 'local',
        autoAcceptThreshold: 0.85,
        triageThreshold: 0.65,
      },
      prefMem
    );
  });

  it('incorporates positive exemplar residual into classify() and rankAllCandidates()', async () => {
    const docText = 'Electrostatic screening, ionic correlations, and dielectric response in electrolyte solutions.';
    const docVector = computeDocumentVector(docText, 64);

    // Initial ranking without preference memory
    const initialCandidates = engine.rankAllCandidates(docText, docVector);
    const initialComp = initialCandidates.find((c) => c.tag === 'topic/electrostatics');
    expect(initialComp).toBeDefined();
    const initialScore = initialComp!.score;

    // Add positive exemplar for topic/electrostatics with identical vector
    prefMem.addExemplar({
      itemKey: 'DOC1',
      tag: 'topic/electrostatics',
      label: 'positive',
      vector: docVector,
      timestamp: new Date().toISOString(),
    });

    const personalizedCandidates = engine.rankAllCandidates(docText, docVector);
    const boostedComp = personalizedCandidates.find((c) => c.tag === 'topic/electrostatics')!;

    expect(boostedComp.residual).toBeGreaterThan(0.1);
    expect(boostedComp.score).toBeCloseTo(Math.min(1.0, initialScore + boostedComp.residual), 4);
    expect(boostedComp.score).toBeGreaterThanOrEqual(initialScore);

    // Classify result should also contain the boosted confidence and residual
    const result = await engine.classify(docText, docVector);
    const classifiedComp = result.tags.find((t) => t.tag === 'topic/electrostatics');
    expect(classifiedComp).toBeDefined();
    expect(classifiedComp!.confidence).toBe(boostedComp.score);
    expect(classifiedComp!.residual).toBe(boostedComp.residual);
  });

  it('incorporates negative exemplar residual to suppress rejected tags', async () => {
    const docText = 'Electrostatic screening, ionic correlations, and dielectric response in electrolyte solutions.';
    const docVector = computeDocumentVector(docText, 64);

    const initialCandidates = engine.rankAllCandidates(docText, docVector);
    const initialComp = initialCandidates.find((c) => c.tag === 'topic/electrostatics')!;

    // Add negative exemplar for topic/electrostatics
    prefMem.addExemplar({
      itemKey: 'DOC2',
      tag: 'topic/electrostatics',
      label: 'negative',
      vector: docVector,
      timestamp: new Date().toISOString(),
    });

    const penalizedCandidates = engine.rankAllCandidates(docText, docVector);
    const penalizedComp = penalizedCandidates.find((c) => c.tag === 'topic/electrostatics')!;

    expect(penalizedComp.residual).toBeLessThan(-0.1);
    expect(penalizedComp.score).toBeLessThan(initialComp.score);
    expect(penalizedComp.score).toBeCloseTo(initialComp.baseScore + penalizedComp.residual, 4);
  });

  it('strictly bounds the personalization residual to [-maxResidual, +maxResidual]', () => {
    const boundedEngine = new ClassifierEngine(
      taxonomy,
      { mode: 'local', autoAcceptThreshold: 0.85, triageThreshold: 0.65 },
      new PreferenceMemory({ alpha: 1.0, beta: 1.0, maxResidual: 0.15 })
    );

    const docText = 'Solvation thermodynamics and coordination chemistry of aqueous electrolytes.';
    const docVec = computeDocumentVector(docText, 64);

    // Add multiple strong positive exemplars for topic/solvation
    for (let i = 0; i < 5; i++) {
      boundedEngine.preferenceMemory.addExemplar({
        itemKey: `DOC_${i}`,
        tag: 'topic/solvation',
        label: 'positive',
        vector: docVec,
        timestamp: new Date().toISOString(),
      });
    }

    const res = boundedEngine.preferenceMemory.computeResidual(docVec, 'topic/solvation');
    expect(res.residual).toBe(0.15); // clamped to maxResidual
  });

  it('enforces taxonomy namespace quotas in classify() regardless of preference boosts', async () => {
    const docText = 'Classical and first-principles molecular dynamics simulations with enhanced sampling and free energy perturbation.';
    const docVec = computeDocumentVector(docText, 64);

    // Give high positive exemplars to 5 method tags
    const methodTags = [
      'method/molecular-dynamics',
      'method/ab-initio-md',
      'method/electronic-structure',
      'method/enhanced-sampling',
      'method/free-energy-calculation',
    ];

    for (const tag of methodTags) {
      engine.preferenceMemory.addExemplar({
        itemKey: 'EX',
        tag,
        label: 'positive',
        vector: docVec,
        timestamp: new Date().toISOString(),
      });
    }

    const classified = await engine.classify(docText, docVec);
    // Method quota is max_tags: 4 in taxonomy
    const methodClassified = classified.tags.filter((c) => c.tag.startsWith('method/'));
    expect(methodClassified.length).toBeLessThanOrEqual(4);
  });

  it('drops tags not recognized by taxonomy even if present in exemplars', () => {
    const docVec = computeDocumentVector('Some document', 64);

    engine.preferenceMemory.addExemplar({
      itemKey: 'EX_UNKNOWN',
      tag: 'nonexistent/fake-tag',
      label: 'positive',
      vector: docVec,
      timestamp: new Date().toISOString(),
    });

    const candidates = engine.rankAllCandidates('Some document', docVec);
    const fake = candidates.find((c) => c.tag === 'nonexistent/fake-tag');
    expect(fake).toBeUndefined();
  });
});
