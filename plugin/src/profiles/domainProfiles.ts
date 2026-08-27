import {
  TAXONOMY_PROFILES,
  TaxonomyProfile,
  combineTaxonomyProfiles,
} from '../taxonomyProfiles.js';
import { parseTaxonomy, RawTaxonomy, Taxonomy } from '../core/taxonomy.js';

export interface DomainProfile {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: string;
  sampleTags: string[];
  subdomains?: string[];
  yaml: string;
}

export const DOMAIN_PROFILES: DomainProfile[] = Object.values(TAXONOMY_PROFILES).map((p) => ({
  id: p.id,
  name: p.name,
  category: p.category,
  description: p.description,
  icon: '',
  sampleTags: p.sampleTags || [],
  subdomains: p.subdomains,
  yaml: p.yaml,
}));

export function getDomainProfile(id: string): DomainProfile | undefined {
  return DOMAIN_PROFILES.find((p) => p.id === id || p.name.toLowerCase() === id.toLowerCase());
}

export { combineTaxonomyProfiles };
