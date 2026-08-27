import { ClassifierEngine } from './classifier/engine.js';
import { StateStore } from './core/state.js';
import { parseTaxonomy, Taxonomy } from './core/taxonomy.js';
import { DEFAULT_TAXONOMY_YAML } from './defaultTaxonomy.js';
import { OrganiserNotifier } from './events/notifier.js';
import { ContextMenuUI } from './ui/contextMenu.js';
import { ItemPaneUI } from './ui/itemPane.js';
import { PreferencesUI } from './ui/preferences.js';
import { TaxonomyManagerUI } from './ui/taxonomyManager.js';

export interface PluginOptions {
  id: string;
  version: string;
  rootURI: string;
}

export class ZoteroOrganiser {
  private static _instance: ZoteroOrganiser | null = null;

  public stateStore: StateStore;
  public taxonomy: Taxonomy;
  public activeTaxonomyYaml: string;
  public classifier: ClassifierEngine;
  public notifier: OrganiserNotifier;
  public options: PluginOptions;

  constructor(options: PluginOptions) {
    this.options = options;
    this.stateStore = new StateStore();
    this.activeTaxonomyYaml = DEFAULT_TAXONOMY_YAML;
    this.taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);

    // Read stored prefs or fall back to safe active defaults
    const writeEnabled =
      typeof Zotero !== 'undefined' && Zotero.Prefs
        ? Zotero.Prefs.get('extensions.zotero-organiser.writeEnabled') ?? true
        : true;
    const onlyNewItems =
      typeof Zotero !== 'undefined' && Zotero.Prefs
        ? Zotero.Prefs.get('extensions.zotero-organiser.onlyNewItems') ?? true
        : true;
    const allowTagRemoval =
      typeof Zotero !== 'undefined' && Zotero.Prefs
        ? Zotero.Prefs.get('extensions.zotero-organiser.allowTagRemoval') ?? false
        : false;
    const autoThreshold =
      typeof Zotero !== 'undefined' && Zotero.Prefs
        ? Zotero.Prefs.get('extensions.zotero-organiser.autoThreshold') ?? 0.85
        : 0.85;
    const triageThreshold =
      typeof Zotero !== 'undefined' && Zotero.Prefs
        ? Zotero.Prefs.get('extensions.zotero-organiser.triageThreshold') ?? 0.65
        : 0.65;

    this.classifier = new ClassifierEngine(this.taxonomy, {
      mode: 'local',
      autoAcceptThreshold: autoThreshold,
      triageThreshold: triageThreshold,
    });

    this.stateStore.setPreferenceMemory(this.classifier.preferenceMemory);

    this.notifier = new OrganiserNotifier(this.stateStore, this.classifier, this.taxonomy, {
      writeEnabled,
      onlyNewItems,
      allowTagRemoval,
      autoThreshold,
      triageThreshold,
      settleMs: 3000,
    });
  }

  public static get instance(): ZoteroOrganiser {
    if (!this._instance) {
      throw new Error('ZoteroOrganiser not initialized');
    }
    return this._instance;
  }

  public getTaxonomyYaml(): string {
    return this.activeTaxonomyYaml || DEFAULT_TAXONOMY_YAML;
  }

  /**
   * Sets, validates, persists, and propagates a new active taxonomy configuration.
   */
  public async setTaxonomy(yamlString: string): Promise<{ success: boolean; error?: string }> {
    try {
      const newTaxonomy = parseTaxonomy(yamlString);
      this.taxonomy = newTaxonomy;
      this.activeTaxonomyYaml = yamlString;
      this.classifier.updateTaxonomy(this.taxonomy);
      this.notifier.updateTaxonomy(this.taxonomy);
      await this.stateStore.setActiveTaxonomyYaml(yamlString);
      ItemPaneUI.refresh();
      TaxonomyManagerUI.notifyTaxonomyChanged(yamlString);
      return { success: true };
    } catch (err: any) {
      const msg = err?.message || String(err);
      return { success: false, error: msg };
    }
  }

  public static openTaxonomyManager(parentWin?: any): HTMLElement {
    return TaxonomyManagerUI.openDialog(parentWin);
  }

  public static async init(options: PluginOptions): Promise<ZoteroOrganiser> {
    if (this._instance) return this._instance;

    const instance = new ZoteroOrganiser(options);
    await instance.stateStore.init();

    // Load saved taxonomy YAML from SQLite state store if previously saved
    const savedYaml = await instance.stateStore.getActiveTaxonomyYaml();
    if (savedYaml) {
      try {
        const customTaxonomy = parseTaxonomy(savedYaml);
        instance.taxonomy = customTaxonomy;
        instance.activeTaxonomyYaml = savedYaml;
        instance.classifier.updateTaxonomy(customTaxonomy);
        instance.notifier.updateTaxonomy(customTaxonomy);
      } catch (err) {
        if (typeof Zotero !== 'undefined' && Zotero.log) {
          Zotero.log(
            `[zotero-organiser] note loading active_taxonomy_yaml: ${err}; using default starter taxonomy`
          );
        }
      }
    }

    // Restore exemplars from SQLite StateStore into ClassifierEngine's PreferenceMemory
    const exemplars = await instance.stateStore.loadAllExemplars();
    for (const exemplar of exemplars) {
      instance.classifier.preferenceMemory.addExemplar(exemplar);
    }

    instance.notifier.init();

    ItemPaneUI.register(instance.stateStore, instance.notifier, options.rootURI);
    PreferencesUI.register(options.rootURI);
    ContextMenuUI.init(instance.notifier);

    this._instance = instance;
    if (typeof Zotero !== 'undefined' && Zotero.log) {
      Zotero.log(
        `[zotero-organiser] initialized plugin version ${options.version}, loaded ${exemplars.length} preference exemplars`
      );
    }

    return instance;
  }

  public static renderPreferences(win?: any): void {
    PreferencesUI.renderPreferences(win);
  }

  public static addToWindow(win: any): void {
    if (this._instance) {
      ContextMenuUI.addToWindow(win);
    }
  }

  public static removeFromWindow(win: any): void {
    if (this._instance) {
      ContextMenuUI.removeFromWindow(win);
    }
  }

  public static async shutdown(): Promise<void> {
    if (!this._instance) return;

    this._instance.notifier.destroy();
    TaxonomyManagerUI.closeDialog();
    ItemPaneUI.unregister();
    PreferencesUI.unregister();
    ContextMenuUI.destroy();
    await this._instance.stateStore.close();

    if (typeof Zotero !== 'undefined' && Zotero.log) {
      Zotero.log('[zotero-organiser] plugin shut down cleanly');
    }

    this._instance = null;
  }
}

// Global exports for Zotero's bootstrap environment
(globalThis as any).ZoteroOrganiser = ZoteroOrganiser;
if (typeof Zotero !== 'undefined') {
  (Zotero as any).ZoteroOrganiser = ZoteroOrganiser;
}
