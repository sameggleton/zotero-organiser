export interface TagScore {
  tag: string;
  confidence: number;
  baseScore?: number;
  residual?: number;
}

export interface Candidate {
  tag: string;
  denseScore: number;
  lexicalScore: number;
  sources: Set<string>;
}

export interface ClassificationResult {
  tags: TagScore[];
  version: string;
}

export interface ClassifierEngineConfig {
  mode: 'local' | 'remote';
  autoAcceptThreshold: number;
  triageThreshold: number;
  remoteEndpoint?: string;
  remoteApiKey?: string;
  remoteModel?: string;
}
