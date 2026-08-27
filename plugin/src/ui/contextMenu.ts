import { OrganiserNotifier } from '../events/notifier.js';
import { TaxonomyManagerUI } from './taxonomyManager.js';

export class ContextMenuUI {
  private static addedWindows = new WeakSet<any>();
  private static notifierInstance: OrganiserNotifier | null = null;

  public static init(notifier: OrganiserNotifier): void {
    this.notifierInstance = notifier;

    if (typeof Zotero === 'undefined') return;

    // Attach to all already open main windows
    const mainWindows =
      typeof (Zotero as any).getMainWindows === 'function'
        ? (Zotero as any).getMainWindows()
        : [typeof (Zotero as any).getMainWindow === 'function' ? (Zotero as any).getMainWindow() : null].filter(
            Boolean
          );

    for (const win of mainWindows) {
      this.addToWindow(win);
    }
  }

  public static addToWindow(win: any): void {
    if (!win || !win.document || this.addedWindows.has(win)) return;

    const doc = win.document;

    // 1. Item Context Menu
    const itemMenu = doc.getElementById('zotero-itemmenu');
    if (itemMenu) {
      const menuSeparator = doc.createElement('menuseparator');
      menuSeparator.id = 'zotero-organiser-separator';
      itemMenu.appendChild(menuSeparator);

      const menuItem = doc.createElement('menuitem');
      menuItem.id = 'zotero-organiser-classify-selected';
      menuItem.setAttribute('label', 'Classify with Taxonomy Organiser');
      menuItem.addEventListener('command', async () => {
        if (!this.notifierInstance) return;
        const pane = win.ZoteroPane || (typeof ZoteroPane !== 'undefined' ? ZoteroPane : null);
        if (!pane || typeof pane.getSelectedItems !== 'function') return;

        const selected = pane.getSelectedItems();
        for (const item of selected) {
          if (item.isRegularItem() && !item.isFeedItem) {
            await this.notifierInstance.processItem(item, true);
          }
        }
      });

      itemMenu.appendChild(menuItem);
    }

    // 2. Tools Menu: "Taxonomy Organiser Settings..."
    const toolsPopup =
      doc.getElementById('menu_ToolsPopup') ||
      doc.getElementById('tools-popup') ||
      doc.getElementById('zotero-tools-menu') ||
      doc.querySelector('#menu_ToolsPopup');

    if (toolsPopup) {
      const toolsSeparator = doc.createElement('menuseparator');
      toolsSeparator.id = 'zotero-organiser-tools-separator';
      toolsPopup.appendChild(toolsSeparator);

      const toolsItem = doc.createElement('menuitem');
      toolsItem.id = 'zotero-organiser-tools-settings';
      toolsItem.setAttribute('label', 'Taxonomy Organiser Settings...');
      toolsItem.addEventListener('command', () => {
        if (typeof Zotero !== 'undefined' && typeof (Zotero as any).openPreferences === 'function') {
          try {
            (Zotero as any).openPreferences('zotero-organiser@sameggleton.dev');
          } catch (e) {
            (Zotero as any).openPreferences();
          }
        } else {
          TaxonomyManagerUI.openDialog(win);
        }
      });
      toolsPopup.appendChild(toolsItem);
    }

    this.addedWindows.add(win);
  }

  public static removeFromWindow(win: any): void {
    if (!win || !win.document) return;
    const doc = win.document;

    const sep = doc.getElementById('zotero-organiser-separator');
    if (sep && sep.parentNode) sep.parentNode.removeChild(sep);
    const item = doc.getElementById('zotero-organiser-classify-selected');
    if (item && item.parentNode) item.parentNode.removeChild(item);

    const toolsSep = doc.getElementById('zotero-organiser-tools-separator');
    if (toolsSep && toolsSep.parentNode) toolsSep.parentNode.removeChild(toolsSep);
    const toolsItem = doc.getElementById('zotero-organiser-tools-settings');
    if (toolsItem && toolsItem.parentNode) toolsItem.parentNode.removeChild(toolsItem);
  }

  public static destroy(): void {
    if (typeof Zotero === 'undefined') return;
    const mainWindows =
      typeof (Zotero as any).getMainWindows === 'function'
        ? (Zotero as any).getMainWindows()
        : [typeof (Zotero as any).getMainWindow === 'function' ? (Zotero as any).getMainWindow() : null].filter(
            Boolean
          );

    for (const win of mainWindows) {
      this.removeFromWindow(win);
    }
    this.notifierInstance = null;
  }
}
