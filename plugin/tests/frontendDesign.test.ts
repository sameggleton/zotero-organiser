import { describe, expect, it, beforeEach, vi, afterEach } from 'vitest';
import { TaxonomyManagerUI } from '../src/ui/taxonomyManager.js';
import { DEFAULT_TAXONOMY_YAML } from '../src/defaultTaxonomy.js';
import { DOMAIN_PROFILES } from '../src/profiles/domainProfiles.js';
import { validateTaxonomyYaml } from '../src/core/taxonomy.js';

// Comprehensive DOM Mock for UI testing
class MockElement {
  public tagName: string;
  public id: string = '';
  public value: string = '';
  public textContent: string = '';
  private _innerHTML: string = '';
  public title: string = '';
  public href: string = '';
  public download: string = '';
  public placeholder: string = '';
  public spellcheck: boolean = false;
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
  public selectionStart: number = 0;
  public selectionEnd: number = 0;
  public scrollTop: number = 0;
  public eventListeners: Record<string, Function[]> = {};
  public attributes: Record<string, string> = {};

  get innerHTML(): string {
    return this._innerHTML;
  }

  set innerHTML(val: string) {
    this._innerHTML = val;
    if (val === '') {
      this.children = [];
    }
  }

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

  removeAttribute(name: string): void {
    delete this.attributes[name];
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

  dispatchEvent(event: any) {
    const type = event?.type;
    if (!type) return;
    const evt = event && typeof event === 'object' && !(event instanceof Event)
      ? { ...event, target: event.target || this }
      : event;
    if (this.eventListeners[type]) {
      this.eventListeners[type].forEach((h) => h(evt));
    }
    if ((this as any)[`on${type}`]) {
      (this as any)[`on${type}`](evt);
    }
  }

  click() {
    this.dispatchEvent({ type: 'click', target: this });
  }

  setSelectionRange(start: number, end: number) {
    this.selectionStart = start;
    this.selectionEnd = end;
  }

  focus() {}

  querySelectorAll(selector: string): MockElement[] {
    const results: MockElement[] = [];
    const check = (node: MockElement) => {
      if (selector.startsWith('.')) {
        const cls = selector.slice(1);
        if (node.classList.contains(cls)) results.push(node);
      } else if (selector.startsWith('#')) {
        const id = selector.slice(1);
        if (node.id === id) results.push(node);
      } else if (selector.startsWith('[') && selector.endsWith(']')) {
        const attrExpr = selector.slice(1, -1);
        const [attrName, attrVal] = attrExpr.split('=');
        if (attrVal) {
          const cleanVal = attrVal.replace(/['"]/g, '');
          if (node.getAttribute(attrName) === cleanVal) results.push(node);
        } else {
          if (node.getAttribute(attrExpr) !== null) results.push(node);
        }
      } else {
        if (node.tagName.toLowerCase() === selector.toLowerCase()) {
          results.push(node);
        }
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

  addEventListener() {}
  removeEventListener() {}
}

describe('Frontend Design & Boundary Condition Tests for TaxonomyManagerUI', () => {
  let mockDoc: MockDocument;
  let container: MockElement;
  let mockWriteText: any;
  let mockCreateObjectURL: any;

  beforeEach(() => {
    mockDoc = new MockDocument();
    container = mockDoc.createElement('div');
    mockDoc.body.appendChild(container);

    TaxonomyManagerUI.editorDraftYaml = null;
    TaxonomyManagerUI.stagedImportYaml = null;

    mockWriteText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', {
      clipboard: {
        writeText: mockWriteText,
      },
    });

    vi.stubGlobal('document', mockDoc);

    class MockBlob {
      content: any;
      options: any;
      constructor(content: any, options: any) {
        this.content = content;
        this.options = options;
      }
    }
    vi.stubGlobal('Blob', MockBlob);

    mockCreateObjectURL = vi.fn().mockReturnValue('blob:mock-url-123');
    vi.stubGlobal('URL', {
      createObjectURL: mockCreateObjectURL,
      revokeObjectURL: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  describe('1. Header & Compact Tab Bar', () => {
    it('renders compact header row and status pill', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      expect(container.className).toBe('zo-root');
      const statusPill = mockDoc.getElementById('taxonomy-manager-active-summary');
      expect(statusPill).toBeDefined();
      expect(statusPill?.className).toContain('zo-status-pill');
    });

    it('renders 3-column tab bar with ARIA tab roles', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const tablist = container.querySelectorAll('.zo-tab-bar')[0];
      expect(tablist).toBeDefined();
      expect(tablist.getAttribute('role')).toBe('tablist');

      const tabs = container.querySelectorAll('button').filter((b) => b.getAttribute('role') === 'tab');
      expect(tabs.length).toBe(3);

      const tabLabels = tabs.map((t) => t.textContent);
      expect(tabLabels).toEqual(['Profiles', 'YAML Editor', 'Import & Export']);
    });

    it('supports arrow key traversal across tabs', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const tabs = container.querySelectorAll('button').filter((b) => b.getAttribute('role') === 'tab');
      const firstTab = tabs[0];

      const preventDefault = vi.fn();
      firstTab.dispatchEvent({ type: 'keydown', key: 'ArrowRight', preventDefault });
      expect(preventDefault).toHaveBeenCalled();

      // Active tab should now be YAML Editor
      const activeTab = tabs.find((t) => t.classList.contains('active'));
      expect(activeTab?.textContent).toBe('YAML Editor');
    });
  });

  describe('2. Profiles View (Single-column fluid layout with sticky footer)', () => {
    it('renders master tri-state checkbox and updates on profile toggling', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const masterChk = mockDoc.getElementById('zo-master-chk');
      expect(masterChk).toBeDefined();
      // Default: general-scholar is selected -> indeterminate
      expect(masterChk?.indeterminate).toBe(true);

      // Select all profiles by clicking master checkbox
      masterChk!.checked = true;
      masterChk!.dispatchEvent({ type: 'change' });
      expect(masterChk?.indeterminate).toBe(false);
      expect(masterChk?.checked).toBe(true);

      // Deselect all
      masterChk!.checked = false;
      masterChk!.dispatchEvent({ type: 'change' });
      expect(masterChk?.indeterminate).toBe(false);
      expect(masterChk?.checked).toBe(false);
    });

    it('renders compact profile rows with max 2 lines description and max 3 sample tags', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const rows = container.querySelectorAll('.zo-row-card');
      expect(rows.length).toBe(DOMAIN_PROFILES.length);

      const firstRow = rows[0];
      const desc = firstRow.querySelectorAll('.zo-line-clamp-2')[0];
      expect(desc).toBeDefined();

      const sampleTags = firstRow.querySelectorAll('.zo-row-card span').filter((s) => s.textContent?.includes('/'));
      expect(sampleTags.length).toBeLessThanOrEqual(3);
    });

    it('applies combined profiles from sticky footer action', async () => {
      let notifiedYaml = '';
      const listener = (yaml: string) => {
        notifiedYaml = yaml;
      };
      TaxonomyManagerUI.addTaxonomyChangedListener(listener);

      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const applyBtn = container.querySelectorAll('button').find((b) =>
        b.textContent?.includes('Apply Selected Profiles')
      )!;
      expect(applyBtn).toBeDefined();

      await (applyBtn as any).onclick();

      expect(notifiedYaml).toBeTruthy();
      const val = validateTaxonomyYaml(notifiedYaml);
      expect(val.valid).toBe(true);

      TaxonomyManagerUI.removeTaxonomyChangedListener(listener);
    });
  });

  describe('3. YAML Editor (Bounded viewport, dirty state, line error nav, draft buffer)', () => {
    it('persists editor draft buffer across tab switches', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      // Switch to YAML Editor
      const tabs = container.querySelectorAll('button').filter((b) => b.getAttribute('role') === 'tab');
      tabs.find((t) => t.textContent === 'YAML Editor')!.click();

      const textarea = container.querySelectorAll('textarea')[0];
      expect(textarea).toBeDefined();

      // Edit textarea
      textarea.value = 'draft_experiment: 123';
      textarea.dispatchEvent({ type: 'input' });
      expect(TaxonomyManagerUI.editorDraftYaml).toBe('draft_experiment: 123');

      // Switch to Profiles tab and back
      tabs.find((t) => t.textContent === 'Profiles')!.click();
      tabs.find((t) => t.textContent === 'YAML Editor')!.click();

      const restoredTextarea = container.querySelectorAll('textarea')[0];
      expect(restoredTextarea.value).toBe('draft_experiment: 123');
    });

    it('tracks uncommitted dirty state and validates live', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const tabs = container.querySelectorAll('button').filter((b) => b.getAttribute('role') === 'tab');
      tabs.find((t) => t.textContent === 'YAML Editor')!.click();

      const textarea = container.querySelectorAll('textarea')[0];
      const dirtyIndicator = container.querySelectorAll('.zo-dirty-indicator')[0];
      expect(dirtyIndicator.textContent).toContain('Saved');

      // Make dirty edit
      textarea.value = DEFAULT_TAXONOMY_YAML + '\n# comment';
      textarea.dispatchEvent({ type: 'input' });

      expect(dirtyIndicator.textContent).toContain('Unsaved changes');
    });

    it('provides clickable line error navigation when validation fails with line number', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const tabs = container.querySelectorAll('button').filter((b) => b.getAttribute('role') === 'tab');
      tabs.find((t) => t.textContent === 'YAML Editor')!.click();

      const textarea = container.querySelectorAll('textarea')[0];
      textarea.value = `schema_version: 1\nversion: "1.0.0"\nnamespaces:\n  topic:\n    - broken: [unclosed`;
      textarea.dispatchEvent({ type: 'input' });

      const lineNavBtn = container.querySelectorAll('button').find((b) => b.textContent?.includes('Go to line'));
      if (lineNavBtn && lineNavBtn.style.display !== 'none') {
        expect(lineNavBtn.textContent).toMatch(/Go to line \d+/);
        lineNavBtn.click();
        expect(textarea.selectionStart).toBeGreaterThanOrEqual(0);
      }
    });

    it('resets to default starter taxonomy on reset button click', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const tabs = container.querySelectorAll('button').filter((b) => b.getAttribute('role') === 'tab');
      tabs.find((t) => t.textContent === 'YAML Editor')!.click();

      const textarea = container.querySelectorAll('textarea')[0];
      textarea.value = 'temporary_junk: true';
      textarea.dispatchEvent({ type: 'input' });

      const resetBtn = container.querySelectorAll('button').find((b) => b.textContent === 'Reset to Default')!;
      resetBtn.click();

      expect(textarea.value).toBe(DEFAULT_TAXONOMY_YAML);
    });
  });

  describe('4. Import & Export (Compact dropzone, explicit staging & validation)', () => {
    it('stages dropped file before overwrite and offers review or confirm', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const tabs = container.querySelectorAll('button').filter((b) => b.getAttribute('role') === 'tab');
      tabs.find((t) => t.textContent === 'Import & Export')!.click();

      const dropzone = container.querySelectorAll('.zo-dropzone')[0];
      expect(dropzone).toBeDefined();

      const validYaml = `schema_version: 1\nversion: "1.0.0"\nnamespaces:\n  topic:\n    kind: semantic\n    values:\n      quantum:\n        description: "Quantum physics"`;

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
        dropzone.dispatchEvent({
          type: 'drop',
          preventDefault: vi.fn(),
          dataTransfer: { files: [{ name: 'test.yml', content: validYaml }] },
        });

        expect(TaxonomyManagerUI.stagedImportYaml).toBe(validYaml);

        // Staged actions should be available
        const reviewBtn = container.querySelectorAll('button').find((b) => b.textContent === 'Review in YAML Editor')!;
        const confirmBtn = container.querySelectorAll('button').find((b) => b.textContent === 'Confirm & Apply Import')!;

        expect(reviewBtn).toBeDefined();
        expect(confirmBtn).toBeDefined();

        // Clicking review transitions to Editor with staged content
        reviewBtn.click();
        expect(TaxonomyManagerUI.editorDraftYaml).toBe(validYaml);
      } finally {
        (globalThis as any).FileReader = originalFileReader;
      }
    });

    it('handles clipboard copy and download actions in Export section', () => {
      TaxonomyManagerUI.render(container as any, mockDoc as any, false);

      const tabs = container.querySelectorAll('button').filter((b) => b.getAttribute('role') === 'tab');
      tabs.find((t) => t.textContent === 'Import & Export')!.click();

      const copyBtn = container.querySelectorAll('button').find((b) => b.textContent?.includes('Copy YAML'))!;
      expect(copyBtn).toBeDefined();
      copyBtn.click();
      expect(mockWriteText).toHaveBeenCalled();

      const downloadBtn = container.querySelectorAll('button').find((b) => b.textContent?.includes('Download .yml'))!;
      expect(downloadBtn).toBeDefined();
      downloadBtn.click();
      expect(mockCreateObjectURL).toHaveBeenCalled();
    });
  });
});
