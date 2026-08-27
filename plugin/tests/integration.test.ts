import { describe, expect, it } from 'vitest';
import { StateStore } from '../src/core/state.js';
import { ClassifierEngine } from '../src/classifier/engine.js';
import { parseTaxonomy } from '../src/core/taxonomy.js';
import { DEFAULT_TAXONOMY_YAML } from '../src/defaultTaxonomy.js';
import { computeDocumentVector, extractDocumentVector } from '../src/core/document.js';

describe('Tier 1 Preference Memory Pipeline (End-to-End)', () => {
  it('persists exemplars, restores on startup, and influences subsequent classifications', async () => {
    const taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);
    const stateStore = new StateStore();
    const classifier = new ClassifierEngine(taxonomy, {
      mode: 'local',
      autoAcceptThreshold: 0.85,
      triageThreshold: 0.65,
    });
    stateStore.setPreferenceMemory(classifier.preferenceMemory);

    // Initial state: doc about molecular dynamics and electrostatic screening
    const doc1 = {
      key: 'DOC1',
      version: 1,
      itemType: 'journalArticle',
      title: 'Molecular dynamics simulations of electrostatic screening in electrolytes',
      abstractNote: 'Ionic correlations and dielectric response in concentrated salt solutions.',
      publicationTitle: 'Journal of Chemical Physics',
      tags: [],
    };
    const vec1 = extractDocumentVector(doc1);

    // Create item in state store
    await stateStore.saveItem({
      itemKey: doc1.key,
      zoteroVersion: 1,
      state: 'needs_triage',
      autoTags: new Set<string>(),
      suppressedTags: new Set<string>(),
      triageTags: { 'topic/electrostatics': 0.74, 'system/peptide': 0.70 },
      candidateTags: {},
      retryCount: 0,
    });

    // 1. User accepts topic/electrostatics and rejects system/peptide
    await stateStore.acceptTriageTag(doc1, 'topic/electrostatics', {
      score: 0.74,
      vector: vec1,
    });
    await stateStore.rejectTriageTag(doc1.key, 'system/peptide', {
      score: 0.70,
      vector: vec1,
    });

    // Verify persisted in StateStore
    const storedExemplars = await stateStore.loadAllExemplars();
    expect(storedExemplars.length).toBe(2);

    // 2. Simulate plugin reload / startup: create new ClassifierEngine & StateStore
    const restoredStore = new StateStore();
    for (const ex of storedExemplars) {
      await restoredStore.saveExemplar(ex.itemKey, ex.tag, ex.label, ex.vector, ex.timestamp);
    }

    const restoredClassifier = new ClassifierEngine(taxonomy, {
      mode: 'local',
      autoAcceptThreshold: 0.85,
      triageThreshold: 0.65,
    });

    // Warm up from database
    const loaded = await restoredStore.loadAllExemplars();
    for (const ex of loaded) {
      restoredClassifier.preferenceMemory.addExemplar(ex);
    }

    expect(restoredClassifier.preferenceMemory.getStats().positiveCount).toBe(1);
    expect(restoredClassifier.preferenceMemory.getStats().negativeCount).toBe(1);

    // 3. Classify a second similar paper
    const doc2 = {
      key: 'DOC2',
      version: 1,
      itemType: 'journalArticle',
      title: 'Dielectric response and screening length in aqueous solutions',
      abstractNote: 'Investigating electrostatic interactions and ion pairing using molecular dynamics.',
      publicationTitle: 'Physical Review Letters',
      tags: [],
    };
    const vec2 = extractDocumentVector(doc2);

    const doc2Text = `Title: ${doc2.title}\nAbstract: ${doc2.abstractNote}`;
    const candidates = restoredClassifier.rankAllCandidates(doc2Text, vec2);

    const elec = candidates.find((c) => c.tag === 'topic/electrostatics');
    expect(elec).toBeDefined();
    expect(elec!.residual).toBeGreaterThan(0.05); // Boosted by previous positive exemplar
  });
});
