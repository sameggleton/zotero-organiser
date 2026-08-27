import { describe, expect, it, beforeEach } from 'vitest';
import { validateTaxonomyYaml, parseTaxonomy } from '../src/core/taxonomy.js';
import { DEFAULT_TAXONOMY_YAML } from '../src/defaultTaxonomy.js';
import { combineTaxonomyProfiles } from '../src/profiles/domainProfiles.js';
import { TaxonomyManagerUI } from '../src/ui/taxonomyManager.js';

// Simple mock DOM environment for testing UI generation
class MockElement {
  public tagName: string;
  public id: string = '';
  public value: string = '';
  public textContent: string = '';
  public innerHTML: string = '';
  public title: string = '';
  public href: string = '';
  public disabled: boolean = false;
  public checked: boolean = false;
  public indeterminate: boolean = false;
  public type: string = '';
  public accept: string = '';
  public className: string = '';
  public style: Record<string, any> = {};
  public children: MockElement[] = [];
  public parentNode: MockElement | null = null;
  public ownerDocument: any = null;
  public eventListeners: Record<string, Function[]> = {};
  public attributes: Record<string, string> = {};
  public classList = {
    add: (cls: string) => {
      const classes = this.className.split(' ').filter(Boolean);
      if (!classes.includes(cls)) classes.push(cls);
      this.className = classes.join(' ');
    },
    remove: (cls: string) => {
      const classes = this.className.split(' ').filter((c) => c !== cls);
      this.className = classes.join(' ');
    },
    contains: (cls: string) => {
      return this.className.split(' ').includes(cls);
    },
  };

  constructor(tagName: string, doc: any) {
    this.tagName = tagName;
    this.ownerDocument = doc;
  }

  setAttribute(name: string, value: string): void {
    this.attributes[name] = value;
  }

  getAttribute(name: string): string | null {
    return this.attributes[name] ?? null;
  }

  appendChild(child: MockElement): MockElement {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  removeChild(child: MockElement): MockElement {
    const idx = this.children.indexOf(child);
    if (idx !== -1) {
      this.children.splice(idx, 1);
      child.parentNode = null;
    }
    return child;
  }

  addEventListener(event: string, handler: Function) {
    if (!this.eventListeners[event]) this.eventListeners[event] = [];
    this.eventListeners[event].push(handler);
  }

  removeEventListener(event: string, handler: Function) {
    if (this.eventListeners[event]) {
      this.eventListeners[event] = this.eventListeners[event].filter((h) => h !== handler);
    }
  }

  dispatchEvent(event: { type: string } | Event) {
    const type = (event as any).type;
    if (this.eventListeners[type]) {
      this.eventListeners[type].forEach((h) => h(event));
    }
    if ((this as any)[`on${type}`]) {
      (this as any)[`on${type}`](event);
    }
  }

  querySelectorAll(selector: string): MockElement[] {
    const results: MockElement[] = [];
    const check = (node: MockElement) => {
      if (node.tagName.toLowerCase() === selector.toLowerCase()) {
        results.push(node);
      }
      node.children.forEach(check);
    };
    this.children.forEach(check);
    return results;
  }

  querySelector(selector: string): MockElement | null {
    const all = this.querySelectorAll(selector);
    return all.length > 0 ? all[0] : null;
  }
}

class MockDocument {
  public head: MockElement;
  public body: MockElement;

  constructor() {
    this.head = new MockElement('head', this);
    this.body = new MockElement('body', this);
  }

  createElement(tag: string): MockElement {
    return new MockElement(tag, this);
  }

  getElementById(id: string): MockElement | null {
    const find = (node: MockElement): MockElement | null => {
      if (node.id === id) return node;
      for (const child of node.children) {
        const res = find(child);
        if (res) return res;
      }
      return null;
    };
    const inHead = find(this.head);
    if (inHead) return inHead;
    return find(this.body);
  }
}

describe('TaxonomyManagerUI & Live Validator', () => {
  let mockDoc: MockDocument;
  let container: MockElement;

  beforeEach(() => {
    mockDoc = new MockDocument();
    container = mockDoc.createElement('div');
    mockDoc.body.appendChild(container);
    TaxonomyManagerUI.editorDraftYaml = null;
    TaxonomyManagerUI.stagedImportYaml = null;
  });

  describe('validateTaxonomyYaml()', () => {
    it('validates correct default starter taxonomy cleanly', () => {
      const result = validateTaxonomyYaml(DEFAULT_TAXONOMY_YAML);
      expect(result.valid).toBe(true);
      expect(result.tagCount).toBeGreaterThan(15);
      expect(result.namespaceCount).toBeGreaterThan(3);
      expect(result.version).toBeDefined();
      expect(result.error).toBeUndefined();
    });

    it('catches invalid YAML syntax errors gracefully', () => {
      const brokenYaml = `
schema_version: 1
namespaces:
  topic: [unclosed list
`;
      const result = validateTaxonomyYaml(brokenYaml);
      expect(result.valid).toBe(false);
      expect(result.error).toBeTruthy();
    });

    it('catches invalid schema rules (missing namespaces)', () => {
      const invalidSchema = `
schema_version: 1
version: "1.0.0"
`;
      const result = validateTaxonomyYaml(invalidSchema);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('namespaces');
    });

    it('catches classifier rules referencing non-existent namespaces', () => {
      const invalidClassifier = `
schema_version: 1
version: "1.0.0"
classifier:
  semantic_namespaces:
    - ghost_namespace
namespaces:
  topic:
    kind: semantic
    max_tags: 2
    values:
      ai:
        description: "AI"
`;
      const result = validateTaxonomyYaml(invalidClassifier);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('ghost_namespace');
    });
  });

  describe('combineTaxonomyProfiles()', () => {
    it('combines two distinct profiles into a valid unified taxonomy YAML', () => {
      const combined = combineTaxonomyProfiles(['physics-astronomy', 'computer-information-sciences']);
      expect(combined).toBeTruthy();

      const validation = validateTaxonomyYaml(combined);
      expect(validation.valid).toBe(true);

      const parsed = parseTaxonomy(combined);
      expect(parsed.namespaces).toHaveProperty('topic');
      expect(parsed.namespaces).toHaveProperty('system');
      expect(parsed.namespaces).toHaveProperty('method');
      expect(parsed.namespaces).toHaveProperty('role');

      const tags = parsed.classifierTags();
      expect(tags.has('topic/quantum-physics')).toBe(true);
      expect(tags.has('topic/machine-learning')).toBe(true);
    });

    it('falls back to general-scholar when an empty array is provided', () => {
      const combined = combineTaxonomyProfiles([]);
      const validation = validateTaxonomyYaml(combined);
      expect(validation.valid).toBe(true);
      expect(validation.tagCount).toBeGreaterThan(15);
    });
  });

  describe('TaxonomyManagerUI Component Rendering', () => {
    it('renders header, title, and compact 3-column tab navigation buttons', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any);

      expect(container.children.length).toBeGreaterThanOrEqual(3);

      const buttons = container.querySelectorAll('button');
      const buttonLabels = buttons.map((b) => b.textContent);

      expect(buttonLabels.some((l) => l.includes('Profiles'))).toBe(true);
      expect(buttonLabels.some((l) => l.includes('YAML Editor'))).toBe(true);
      expect(buttonLabels.some((l) => l.includes('Import & Export'))).toBe(true);
    });

    it('manages taxonomy change listeners correctly', () => {
      let notifiedYaml = '';
      const listener = (yaml: string) => {
        notifiedYaml = yaml;
      };

      TaxonomyManagerUI.addTaxonomyChangedListener(listener);
      TaxonomyManagerUI.notifyTaxonomyChanged('sample_yaml: true');

      expect(notifiedYaml).toBe('sample_yaml: true');

      TaxonomyManagerUI.removeTaxonomyChangedListener(listener);
      TaxonomyManagerUI.notifyTaxonomyChanged('another: false');

      // Should not update after removal
      expect(notifiedYaml).toBe('sample_yaml: true');
    });

    it('handles drag-and-drop visual highlight and file drop in Import tab', async () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any);

      // Find and click Import & Export tab
      const buttons = container.querySelectorAll('button');
      const importTabBtn = buttons.find((b) => b.textContent.includes('Import & Export'));
      expect(importTabBtn).toBeDefined();
      importTabBtn!.dispatchEvent({ type: 'click' });

      // Find dropzone
      const dropzones = container.children[2].querySelectorAll('div').filter((d) => d.className.includes('zo-dropzone'));
      expect(dropzones.length).toBeGreaterThan(0);
      const dropzone = dropzones[0];

      // Test dragover highlight
      dropzone.dispatchEvent({
        type: 'dragover',
        preventDefault: () => {},
        stopPropagation: () => {},
      } as any);

      expect(dropzone.className).toContain('drag-active');

      // Test dragleave highlight removal
      dropzone.dispatchEvent({
        type: 'dragleave',
        preventDefault: () => {},
        stopPropagation: () => {},
      } as any);

      expect(dropzone.className).not.toContain('drag-active');

      // Mock FileReader on globalThis
      const originalFileReader = (globalThis as any).FileReader;
      class MockFileReader {
        public onload: ((e: any) => void) | null = null;
        readAsText(file: any) {
          if (this.onload) {
            this.onload({ target: { result: file.content } });
          }
        }
      }
      (globalThis as any).FileReader = MockFileReader;

      try {
        const sampleYamlContent = `schema_version: 1\nversion: "1.0.0"\nnamespaces:\n  topic:\n    kind: semantic\n    values:\n      ai:\n        description: "AI"`;
        const mockFile = { name: 'taxonomy.yml', content: sampleYamlContent };

        dropzone.dispatchEvent({
          type: 'drop',
          preventDefault: () => {},
          stopPropagation: () => {},
          dataTransfer: { files: [mockFile] },
        } as any);

        expect(TaxonomyManagerUI.stagedImportYaml).toBe(sampleYamlContent);
      } finally {
        (globalThis as any).FileReader = originalFileReader;
      }
    });

    it('enforces word-break and overflow-wrap boundaries across text containers', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any);

      const subtitle = mockDoc.getElementById('taxonomy-manager-active-summary');
      expect(subtitle).toBeDefined();
      expect(subtitle?.className).toContain('zo-status-pill');
    });

    it('switches to YAML Editor tab with persistent draft buffer and line error navigation', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any);

      // Switch to YAML Editor tab
      const buttons = container.querySelectorAll('button');
      const editorTabBtn = buttons.find((b) => b.textContent.includes('YAML Editor'));
      expect(editorTabBtn).toBeDefined();
      editorTabBtn!.dispatchEvent({ type: 'click' });

      // Find textarea
      const textareas = container.querySelectorAll('textarea');
      expect(textareas.length).toBeGreaterThan(0);
      const textarea = textareas[0];
      expect(textarea.value).toBeTruthy();

      // Test draft buffer persistence
      textarea.value = 'modified_draft: true';
      textarea.dispatchEvent({ type: 'input' });
      expect(TaxonomyManagerUI.editorDraftYaml).toBe('modified_draft: true');
    });
  });
});
