import { Taxonomy } from '../core/taxonomy.js';
import { TagScore } from './types.js';

export interface RemoteClassifierOptions {
  endpoint: string;
  apiKey: string;
  model?: string;
}

export class RemoteClassifier {
  private taxonomy: Taxonomy;
  private endpoint: string;
  private apiKey: string;
  private model: string;

  constructor(taxonomy: Taxonomy, options: RemoteClassifierOptions) {
    this.taxonomy = taxonomy;
    this.endpoint = options.endpoint.replace(/\/+$/, '');
    this.apiKey = options.apiKey;
    this.model = options.model || 'gpt-4.1-mini';
  }

  get version(): string {
    return `remote:${this.model}`;
  }

  async classify(
    document: string,
    allowedCandidates?: Set<string>
  ): Promise<TagScore[]> {
    if (!this.apiKey) {
      throw new Error('Remote classification requires an API key');
    }

    const promptDefs = this.taxonomy.promptDefinitions(allowedCandidates);
    const validTags = Array.from(allowedCandidates || this.taxonomy.classifierTags());

    const systemPrompt = `You are a conservative scientific metadata classifier.
Analyze the scientific paper details and select only the appropriate canonical tags from the taxonomy below.
Follow all inclusion/exclusion rules strictly. Apply tags only with high confidence.

Taxonomy:
${promptDefs}`;

    const jsonSchema = {
      name: 'classification',
      strict: true,
      schema: {
        type: 'object',
        properties: {
          tags: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                tag: {
                  type: 'string',
                  enum: validTags,
                },
                confidence: {
                  type: 'number',
                  minimum: 0.0,
                  maximum: 1.0,
                },
              },
              required: ['tag', 'confidence'],
              additionalProperties: false,
            },
          },
        },
        required: ['tags'],
        additionalProperties: false,
      },
    };

    const payload = {
      model: this.model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: document },
      ],
      response_format: {
        type: 'json_schema',
        json_schema: jsonSchema,
      },
      temperature: 0.0,
    };

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Remote classifier error (${response.status}): ${errText}`);
    }

    const resJson = await response.json();
    const messageContent = resJson.choices?.[0]?.message?.content;
    if (!messageContent) {
      throw new Error('Remote classifier returned empty response');
    }

    const parsed = JSON.parse(messageContent);
    const results: TagScore[] = [];

    if (Array.isArray(parsed.tags)) {
      for (const item of parsed.tags) {
        if (typeof item.tag === 'string' && typeof item.confidence === 'number') {
          results.push({
            tag: item.tag,
            confidence: item.confidence,
          });
        }
      }
    }

    return results;
  }
}
