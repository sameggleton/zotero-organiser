import { TaxonomyManagerUI } from './taxonomyManager.js';

export class PreferencesUI {
  private static registered = false;

  public static register(rootURI?: string): void {
    if (
      typeof Zotero === 'undefined' ||
      !Zotero.PreferencePanes ||
      typeof Zotero.PreferencePanes.register !== 'function' ||
      this.registered
    ) {
      return;
    }

    try {
      const src = rootURI ? `${rootURI}chrome/content/preferences.xhtml` : 'chrome/content/preferences.xhtml';
      const image = rootURI ? `${rootURI}chrome/content/icons/tag-purple.svg` : 'chrome/content/icons/tag-purple.svg';
      const stylesheet = rootURI ? `${rootURI}chrome/content/preferences.css` : 'chrome/content/preferences.css';

      Zotero.PreferencePanes.register({
        pluginID: 'zotero-organiser@sameggleton.dev',
        src,
        label: 'Organiser',
        image,
        defaultXUL: true,
        stylesheets: [stylesheet, 'chrome://zoteroorganiser/content/preferences.css'],
      });
      this.registered = true;
      if (typeof Zotero.log === 'function') {
        Zotero.log(`[zotero-organiser] PreferencePane registered successfully with src: ${src}`);
      }
    } catch (e) {
      if (typeof Zotero.log === 'function') {
        Zotero.log(`[zotero-organiser] preferences pane registration note: ${e}`);
      }
    }
  }

  public static ensureStylesheet(doc: Document): void {
    if (!doc || typeof doc.createElement !== 'function') return;
    const linkId = 'zotero-organiser-preferences-stylesheet';
    if (typeof doc.getElementById === 'function' && doc.getElementById(linkId)) {
      return;
    }
    try {
      const link = doc.createElement('link') as HTMLLinkElement;
      link.id = linkId;
      if (typeof link.setAttribute === 'function') {
        link.setAttribute('rel', 'stylesheet');
        link.setAttribute('href', 'chrome://zoteroorganiser/content/preferences.css');
      } else {
        (link as any).rel = 'stylesheet';
        (link as any).href = 'chrome://zoteroorganiser/content/preferences.css';
      }
      if (doc.head) {
        doc.head.appendChild(link);
      } else if (doc.documentElement) {
        doc.documentElement.appendChild(link);
      }
    } catch (e) {
      // Ignore in non-standard DOM environments
    }
  }

  public static renderPreferences(win?: any): void {
    const windowObj =
      win ||
      (typeof window !== 'undefined' ? window : null) ||
      (typeof Zotero !== 'undefined' && typeof (Zotero as any).getMainWindow === 'function'
        ? (Zotero as any).getMainWindow()
        : null);

    const doc: Document = windowObj?.document || (typeof document !== 'undefined' ? document : (null as any));
    if (!doc) return;

    this.ensureStylesheet(doc);

    const mount = () => {
      const root =
        doc.getElementById('zotero-organiser-preferences-root') ||
        doc.getElementById('zotero-organiser-preferences-pane');
      if (root) {
        TaxonomyManagerUI.render(root as HTMLElement, doc, false);
      }
    };

    if (doc.readyState === 'loading') {
      doc.addEventListener('DOMContentLoaded', mount, { once: true });
    } else {
      mount();
    }
  }

  public static unregister(): void {
    if (
      typeof Zotero !== 'undefined' &&
      Zotero.PreferencePanes &&
      typeof Zotero.PreferencePanes.unregister === 'function' &&
      this.registered
    ) {
      try {
        Zotero.PreferencePanes.unregister('zotero-organiser@sameggleton.dev');
      } catch (e) {
        // Ignore unregister errors
      }
      this.registered = false;
    }
  }
}
