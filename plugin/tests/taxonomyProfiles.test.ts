import { describe, it, expect } from 'vitest';
import { parseTaxonomy } from '../src/core/taxonomy.js';
import {
  TAXONOMY_PROFILES,
  combineTaxonomyProfiles,
} from '../src/taxonomyProfiles.js';

describe('Taxonomy Profiles Registry & Combiner', () => {
  const profileIds = Object.keys(TAXONOMY_PROFILES);

  it('contains all 25 required academic profile definitions', () => {
    expect(profileIds).toHaveLength(25);
    expect(profileIds).toContain('general-scholar');
    expect(profileIds).toContain('mathematics-statistics');
    expect(profileIds).toContain('computer-information-sciences');
    expect(profileIds).toContain('physics-astronomy');
    expect(profileIds).toContain('chemistry-molecular-sciences');
    expect(profileIds).toContain('biological-sciences');
    expect(profileIds).toContain('biomedical-clinical-sciences');
    expect(profileIds).toContain('health-sciences');
    expect(profileIds).toContain('agricultural-veterinary-food');
    expect(profileIds).toContain('earth-atmospheric-ocean');
    expect(profileIds).toContain('environmental-sustainability');
    expect(profileIds).toContain('engineering-technology');
    expect(profileIds).toContain('built-environment-architecture');
    expect(profileIds).toContain('psychology-cognitive-sciences');
    expect(profileIds).toContain('economics');
    expect(profileIds).toContain('business-management-organisations');
    expect(profileIds).toContain('society-politics-human-geography');
    expect(profileIds).toContain('education-learning-sciences');
    expect(profileIds).toContain('law-criminology-justice');
    expect(profileIds).toContain('language-communication-culture');
    expect(profileIds).toContain('literature-writing');
    expect(profileIds).toContain('history-heritage-archaeology');
    expect(profileIds).toContain('philosophy-ethics-religious');
    expect(profileIds).toContain('creative-arts-design');
    expect(profileIds).toContain('indigenous-studies');
  });

  profileIds.forEach((id) => {
    it(`validates that profile '${id}' parses cleanly with parseTaxonomy`, () => {
      const profile = TAXONOMY_PROFILES[id];
      expect(profile).toBeDefined();
      expect(profile.yaml).toBeTruthy();

      const taxonomy = parseTaxonomy(profile.yaml);
      expect(taxonomy.schemaVersion).toBe(1);
      expect(taxonomy.version).toBe('1.0.0');

      // Check standard namespaces
      expect(taxonomy.namespaces).toHaveProperty('status');
      expect(taxonomy.namespaces).toHaveProperty('priority');
      expect(taxonomy.namespaces).toHaveProperty('role');
      expect(taxonomy.namespaces).toHaveProperty('topic');
      expect(taxonomy.namespaces).toHaveProperty('system');
      expect(taxonomy.namespaces).toHaveProperty('method');

      // Check status is workflow and priority is judgement
      expect(taxonomy.namespaces.status.kind).toBe('workflow');
      expect(taxonomy.namespaces.priority.kind).toBe('judgement');
      expect(taxonomy.namespaces.role.kind).toBe('semantic');
      expect(taxonomy.namespaces.topic.kind).toBe('semantic');
      expect(taxonomy.namespaces.system.kind).toBe('semantic');
      expect(taxonomy.namespaces.method.kind).toBe('semantic');

      // Check classifier tags
      const classifierTags = taxonomy.classifierTags();
      expect(classifierTags.size).toBeGreaterThanOrEqual(20);
      expect(classifierTags.has('status/read')).toBe(false);
      expect(classifierTags.has('priority/core')).toBe(false);
    });
  });

  it('combines a single profile and returns valid YAML', () => {
    const yamlOutput = combineTaxonomyProfiles(['physics-astronomy']);
    const taxonomy = parseTaxonomy(yamlOutput);
    expect(taxonomy.namespaces).toHaveProperty('topic');
    expect(taxonomy.namespaces.topic.values).toHaveProperty('quantum-physics');
    expect(taxonomy.namespaces.topic.values).toHaveProperty('condensed-matter');
  });

  it('combines two domain profiles (Physics & Astronomy + Chemistry & Molecular Sciences)', () => {
    const yamlOutput = combineTaxonomyProfiles(['physics-astronomy', 'chemistry-molecular-sciences']);
    const taxonomy = parseTaxonomy(yamlOutput);

    // Should have topics from both
    expect(taxonomy.namespaces.topic.values).toHaveProperty('quantum-physics');
    expect(taxonomy.namespaces.topic.values).toHaveProperty('organic-chemistry');
    expect(taxonomy.namespaces.system.values).toHaveProperty('quantum-devices');
    expect(taxonomy.namespaces.system.values).toHaveProperty('molecular-compounds');

    // Method tags from both
    expect(taxonomy.namespaces.method.values).toHaveProperty('theoretical-derivation');
    expect(taxonomy.namespaces.method.values).toHaveProperty('chemical-synthesis');
  });

  it('combines three domain profiles (Biological Sciences + Computer & Info Sciences + Economics)', () => {
    const yamlOutput = combineTaxonomyProfiles(['biological-sciences', 'computer-information-sciences', 'economics']);
    const taxonomy = parseTaxonomy(yamlOutput);

    expect(taxonomy.namespaces.topic.values).toHaveProperty('cell-biology');
    expect(taxonomy.namespaces.topic.values).toHaveProperty('machine-learning');
    expect(taxonomy.namespaces.topic.values).toHaveProperty('econometrics');

    const classifierTags = taxonomy.classifierTags();
    expect(classifierTags.has('topic/machine-learning')).toBe(true);
    expect(classifierTags.has('topic/cell-biology')).toBe(true);
    expect(classifierTags.has('topic/econometrics')).toBe(true);
  });

  it('combines all 25 academic profiles into a master taxonomy cleanly without duplicate tags', () => {
    const yamlOutput = combineTaxonomyProfiles(profileIds);
    const taxonomy = parseTaxonomy(yamlOutput);

    expect(taxonomy.schemaVersion).toBe(1);
    expect(taxonomy.namespaces.status.values).toHaveProperty('needs-triage');
    expect(taxonomy.namespaces.status.values).toHaveProperty('to-read');
    expect(taxonomy.namespaces.status.values).toHaveProperty('reading');
    expect(taxonomy.namespaces.status.values).toHaveProperty('read');
    expect(taxonomy.namespaces.status.values).toHaveProperty('processed');

    // Verify representations across domains
    expect(taxonomy.namespaces.topic.values).toHaveProperty('research-design'); // General Scholar
    expect(taxonomy.namespaces.topic.values).toHaveProperty('algebra'); // Math
    expect(taxonomy.namespaces.topic.values).toHaveProperty('machine-learning'); // CS
    expect(taxonomy.namespaces.topic.values).toHaveProperty('quantum-physics'); // Physics
    expect(taxonomy.namespaces.topic.values).toHaveProperty('organic-chemistry'); // Chemistry
    expect(taxonomy.namespaces.topic.values).toHaveProperty('cell-biology'); // Bio
    expect(taxonomy.namespaces.topic.values).toHaveProperty('neuroscience'); // Biomed
    expect(taxonomy.namespaces.topic.values).toHaveProperty('epidemiology'); // Health
    expect(taxonomy.namespaces.topic.values).toHaveProperty('agronomy'); // Ag
    expect(taxonomy.namespaces.topic.values).toHaveProperty('geology'); // Earth
    expect(taxonomy.namespaces.topic.values).toHaveProperty('ecology'); // Env
    expect(taxonomy.namespaces.topic.values).toHaveProperty('electrical-engineering'); // Eng
    expect(taxonomy.namespaces.topic.values).toHaveProperty('architecture'); // Built Env
    expect(taxonomy.namespaces.topic.values).toHaveProperty('cognition'); // Psych
    expect(taxonomy.namespaces.topic.values).toHaveProperty('macroeconomics'); // Econ
    expect(taxonomy.namespaces.topic.values).toHaveProperty('finance'); // Business
    expect(taxonomy.namespaces.topic.values).toHaveProperty('sociology'); // Society
    expect(taxonomy.namespaces.topic.values).toHaveProperty('pedagogy'); // Education
    expect(taxonomy.namespaces.topic.values).toHaveProperty('public-law'); // Law
    expect(taxonomy.namespaces.topic.values).toHaveProperty('linguistics'); // Lang
    expect(taxonomy.namespaces.topic.values).toHaveProperty('literature'); // Literature
    expect(taxonomy.namespaces.topic.values).toHaveProperty('history'); // History
    expect(taxonomy.namespaces.topic.values).toHaveProperty('philosophy'); // Philosophy
    expect(taxonomy.namespaces.topic.values).toHaveProperty('visual-arts'); // Creative Arts
    expect(taxonomy.namespaces.topic.values).toHaveProperty('indigenous-knowledge'); // Indigenous

    // Total unique classifier tags
    const allTags = taxonomy.tags();
    const classifierTags = taxonomy.classifierTags();
    expect(allTags.size).toBeGreaterThanOrEqual(200);
    expect(classifierTags.size).toBeGreaterThanOrEqual(180);
  });

  it('handles empty profileIds array by falling back to general-scholar', () => {
    const yamlOutput = combineTaxonomyProfiles([]);
    const taxonomy = parseTaxonomy(yamlOutput);
    expect(taxonomy.namespaces.topic.values).toHaveProperty('research-design');
  });

  it('handles invalid profile IDs gracefully', () => {
    const yamlOutput = combineTaxonomyProfiles(['nonexistent-profile', 'unknown']);
    const taxonomy = parseTaxonomy(yamlOutput);
    expect(taxonomy.namespaces.topic.values).toHaveProperty('research-design');
  });
});
