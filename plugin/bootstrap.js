/* global ChromeUtils, Services */

var ZoteroOrganiser = null;

function install(data, reason) {
  // Setup if needed on initial install
}

async function startup({ id, version, rootURI }, reason) {
  try {
    // Load bundled script into current scope
    Services.scriptloader.loadSubScript(rootURI + 'build/addon.js', this);
    const organiser =
      this.ZoteroOrganiser ||
      globalThis.ZoteroOrganiser ||
      (typeof Zotero !== 'undefined' && Zotero.ZoteroOrganiser);

    if (organiser) {
      ZoteroOrganiser = organiser;
      await ZoteroOrganiser.init({ id, version, rootURI });
      if (typeof Zotero !== 'undefined' && Zotero.log) {
        Zotero.log('[zotero-organiser] plugin startup completed successfully');
      }
    } else {
      if (typeof Zotero !== 'undefined' && Zotero.log) {
        Zotero.log('[zotero-organiser] ZoteroOrganiser object not found after loadSubScript');
      }
    }
  } catch (err) {
    if (typeof Zotero !== 'undefined' && Zotero.log) {
      Zotero.log('[zotero-organiser] startup error: ' + err);
    }
  }
}

function onMainWindowLoad({ window }) {
  try {
    if (ZoteroOrganiser && typeof ZoteroOrganiser.addToWindow === 'function') {
      ZoteroOrganiser.addToWindow(window);
    }
  } catch (err) {
    if (typeof Zotero !== 'undefined' && Zotero.log) {
      Zotero.log('[zotero-organiser] onMainWindowLoad error: ' + err);
    }
  }
}

function onMainWindowUnload({ window }) {
  try {
    if (ZoteroOrganiser && typeof ZoteroOrganiser.removeFromWindow === 'function') {
      ZoteroOrganiser.removeFromWindow(window);
    }
  } catch (err) {
    // Ignore unload errors
  }
}

async function shutdown({ id, version, rootURI }, reason) {
  try {
    if (ZoteroOrganiser) {
      await ZoteroOrganiser.shutdown();
      ZoteroOrganiser = null;
    }
  } catch (err) {
    if (typeof Zotero !== 'undefined' && Zotero.log) {
      Zotero.log('[zotero-organiser] shutdown error: ' + err);
    }
  }
}

function uninstall(data, reason) {
  // Cleanup on uninstall
}
