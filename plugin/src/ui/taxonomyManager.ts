import { DEFAULT_TAXONOMY_YAML } from '../defaultTaxonomy.js';
import { combineTaxonomyProfiles, DOMAIN_PROFILES, DomainProfile } from '../profiles/domainProfiles.js';
import { validateTaxonomyYaml, ValidationResult } from '../core/taxonomy.js';
import { ZoteroOrganiser } from '../index.js';

export class TaxonomyManagerUI {
  private static activeModal: HTMLElement | null = null;
  private static activeKeyHandler: ((e: KeyboardEvent) => void) | null = null;
  private static activeDoc: Document | null = null;
  private static onTaxonomyChangedListeners: Array<(yaml: string) => void> = [];

  // Persistent editor draft buffer across tab switches
  public static editorDraftYaml: string | null = null;
  // Staged import buffer
  public static stagedImportYaml: string | null = null;

  public static addTaxonomyChangedListener(listener: (yaml: string) => void): void {
    this.onTaxonomyChangedListeners.push(listener);
  }

  public static removeTaxonomyChangedListener(listener: (yaml: string) => void): void {
    this.onTaxonomyChangedListeners = this.onTaxonomyChangedListeners.filter((l) => l !== listener);
  }

  public static notifyTaxonomyChanged(yaml: string): void {
    for (const listener of this.onTaxonomyChangedListeners) {
      try {
        listener(yaml);
      } catch (e) {}
    }
  }

  /**
   * Opens the Taxonomy Manager modal dialog in the current or specified window.
   */
  public static openDialog(parentWin?: any): HTMLElement {
    const win =
      parentWin ||
      (typeof window !== 'undefined' ? window : null) ||
      (typeof Zotero !== 'undefined' && typeof (Zotero as any).getMainWindow === 'function'
        ? (Zotero as any).getMainWindow()
        : null);

    const doc: Document = win && win.document ? win.document : (typeof document !== 'undefined' ? document : (null as any));
    if (!doc) {
      throw new Error('No DOM document available to render Taxonomy Manager dialog');
    }

    this.closeDialog();

    const overlay = doc.createElement('div');
    overlay.id = 'zotero-organiser-modal-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100vw';
    overlay.style.height = '100vh';
    overlay.style.backgroundColor = 'rgba(15, 23, 42, 0.5)';
    overlay.style.zIndex = '999999';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';
    overlay.style.padding = '16px';
    overlay.style.boxSizing = 'border-box';

    const modal = doc.createElement('div');
    modal.id = 'zotero-organiser-modal';
    modal.style.width = '640px';
    modal.style.maxWidth = '96vw';
    modal.style.height = '560px';
    modal.style.maxHeight = '92vh';
    modal.style.backgroundColor = 'var(--zo-bg, #ffffff)';
    modal.style.borderRadius = '8px';
    modal.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.15)';
    modal.style.display = 'flex';
    modal.style.flexDirection = 'column';
    modal.style.overflow = 'hidden';
    modal.style.border = '1px solid var(--zo-border, #e2e8f0)';

    overlay.appendChild(modal);

    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        this.closeDialog();
      }
    };
    doc.addEventListener('keydown', keyHandler);
    this.activeKeyHandler = keyHandler;
    this.activeDoc = doc;

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        this.closeDialog();
      }
    });

    this.render(modal, doc, true);

    doc.body.appendChild(overlay);
    this.activeModal = overlay;

    return overlay;
  }

  public static closeDialog(): void {
    if (this.activeKeyHandler && this.activeDoc) {
      try {
        this.activeDoc.removeEventListener('keydown', this.activeKeyHandler);
      } catch (e) {}
      this.activeKeyHandler = null;
      this.activeDoc = null;
    }
    if (this.activeModal && this.activeModal.parentNode) {
      this.activeModal.parentNode.removeChild(this.activeModal);
      this.activeModal = null;
    }
  }

  /**
   * Renders the complete Taxonomy Manager UI inside any container element.
   * Responsive to ~560x500px min viewport.
   */
  public static render(container: HTMLElement, doc: Document = container.ownerDocument || document, isModal = false): void {
    container.innerHTML = '';
    container.className = 'zo-root';

    let activeTab: 'profiles' | 'editor' | 'import-export' = 'profiles';
    let currentSavedYaml = this.getActiveTaxonomyYaml();

    // Initialise draft buffer if empty
    if (this.editorDraftYaml === null) {
      this.editorDraftYaml = currentSavedYaml;
    }

    // --- 1. Compact Header Row (~38px) ---
    const header = doc.createElement('div');
    header.style.display = 'flex';
    header.style.alignItems = 'center';
    header.style.justifyContent = 'space-between';
    header.style.padding = '8px 12px';
    header.style.height = '38px';
    header.style.flexShrink = '0';
    header.style.backgroundColor = 'var(--zo-surface, #f8fafc)';
    header.style.borderBottom = '1px solid var(--zo-border, #e2e8f0)';
    header.style.boxSizing = 'border-box';

    const titleGroup = doc.createElement('div');
    titleGroup.style.display = 'flex';
    titleGroup.style.alignItems = 'center';
    titleGroup.style.gap = '8px';

    const title = doc.createElement('span');
    title.textContent = 'Taxonomy Organiser';
    title.style.fontSize = '12.5px';
    title.style.fontWeight = '600';
    title.style.color = 'var(--zo-text-primary, #0f172a)';
    titleGroup.appendChild(title);

    const subtitle = doc.createElement('span');
    subtitle.id = 'taxonomy-manager-active-summary';
    subtitle.className = 'zo-status-pill';
    this.updateHeaderSubtitle(subtitle, currentSavedYaml);
    titleGroup.appendChild(subtitle);

    header.appendChild(titleGroup);

    if (isModal) {
      const closeBtn = doc.createElement('button');
      closeBtn.textContent = '✕';
      closeBtn.title = 'Close Dialog';
      closeBtn.className = 'zo-btn zo-btn-sm';
      closeBtn.style.padding = '2px 6px';
      closeBtn.style.border = 'none';
      closeBtn.style.background = 'transparent';
      closeBtn.onclick = () => this.closeDialog();
      header.appendChild(closeBtn);
    }

    container.appendChild(header);

    // --- 2. Compact 3-Column Tab Bar ---
    const navBar = doc.createElement('div');
    navBar.className = 'zo-tab-bar';
    navBar.setAttribute('role', 'tablist');

    const tabs: Array<{ id: 'profiles' | 'editor' | 'import-export'; label: string }> = [
      { id: 'profiles', label: 'Profiles' },
      { id: 'editor', label: 'YAML Editor' },
      { id: 'import-export', label: 'Import & Export' },
    ];

    const tabButtons: Record<string, HTMLButtonElement> = {};

    const contentArea = doc.createElement('div');
    contentArea.style.flex = '1';
    contentArea.style.minHeight = '0';
    contentArea.style.display = 'flex';
    contentArea.style.flexDirection = 'column';
    contentArea.style.overflow = 'hidden';
    contentArea.style.backgroundColor = 'var(--zo-bg, #ffffff)';
    contentArea.style.boxSizing = 'border-box';

    const switchTab = (tabId: 'profiles' | 'editor' | 'import-export') => {
      activeTab = tabId;
      for (const [id, btn] of Object.entries(tabButtons)) {
        const isActive = id === tabId;
        if (isActive) {
          btn.classList.add('active');
          btn.setAttribute('aria-selected', 'true');
          btn.setAttribute('tabindex', '0');
        } else {
          btn.classList.remove('active');
          btn.setAttribute('aria-selected', 'false');
          btn.setAttribute('tabindex', '-1');
        }
      }

      contentArea.innerHTML = '';
      if (tabId === 'profiles') {
        this.renderTabProfiles(contentArea, doc, (newYaml) => {
          currentSavedYaml = newYaml;
          this.editorDraftYaml = newYaml;
          this.updateHeaderSubtitle(subtitle, currentSavedYaml);
          switchTab('editor');
        });
      } else if (tabId === 'editor') {
        this.renderTabEditor(contentArea, doc, currentSavedYaml, (savedYaml) => {
          currentSavedYaml = savedYaml;
          this.editorDraftYaml = savedYaml;
          this.updateHeaderSubtitle(subtitle, currentSavedYaml);
        });
      } else if (tabId === 'import-export') {
        this.renderTabImportExport(
          contentArea,
          doc,
          currentSavedYaml,
          (reviewedYaml) => {
            this.editorDraftYaml = reviewedYaml;
            switchTab('editor');
          },
          (appliedYaml) => {
            currentSavedYaml = appliedYaml;
            this.editorDraftYaml = appliedYaml;
            this.updateHeaderSubtitle(subtitle, currentSavedYaml);
            switchTab('editor');
          }
        );
      }
    };

    tabs.forEach((tab, index) => {
      const btn = doc.createElement('button');
      btn.textContent = tab.label;
      btn.className = 'zo-tab-btn';
      btn.setAttribute('role', 'tab');
      btn.setAttribute('id', `zo-tab-${tab.id}`);
      btn.setAttribute('aria-controls', `zo-panel-${tab.id}`);
      btn.onclick = () => switchTab(tab.id);

      // Keyboard navigation for tabs
      btn.onkeydown = (e: KeyboardEvent) => {
        let targetIndex = -1;
        if (e.key === 'ArrowRight') targetIndex = (index + 1) % tabs.length;
        else if (e.key === 'ArrowLeft') targetIndex = (index - 1 + tabs.length) % tabs.length;
        else if (e.key === 'Home') targetIndex = 0;
        else if (e.key === 'End') targetIndex = tabs.length - 1;

        if (targetIndex !== -1) {
          e.preventDefault();
          const targetTab = tabs[targetIndex];
          switchTab(targetTab.id);
          tabButtons[targetTab.id]?.focus();
        }
      };

      tabButtons[tab.id] = btn;
      navBar.appendChild(btn);
    });

    container.appendChild(navBar);
    container.appendChild(contentArea);

    // Initialise active tab
    switchTab('profiles');
  }

  private static updateHeaderSubtitle(element: HTMLElement, yamlString: string): void {
    const val = validateTaxonomyYaml(yamlString);
    if (val.valid) {
      element.textContent = `v${val.version || '1.0.0'} (${val.tagCount} tags)`;
      element.style.color = 'var(--zo-accent-text, #1d4ed8)';
      element.style.backgroundColor = 'var(--zo-accent-subtle, #eff6ff)';
    } else {
      element.textContent = 'Invalid Config';
      element.style.color = 'var(--zo-error-text, #b91c1c)';
      element.style.backgroundColor = 'var(--zo-error-bg, #fef2f2)';
    }
  }

  /**
   * Tab 1: Profiles View (Single-column fluid layout with sticky footer)
   */
  private static renderTabProfiles(
    container: HTMLElement,
    doc: Document,
    onApplied: (combinedYaml: string) => void
  ): void {
    const panel = doc.createElement('div');
    panel.id = 'zo-panel-profiles';
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', 'zo-tab-profiles');
    panel.style.display = 'flex';
    panel.style.flexDirection = 'column';
    panel.style.height = '100%';
    panel.style.width = '100%';
    panel.style.boxSizing = 'border-box';
    panel.style.overflow = 'hidden';

    // Top Master Selection Bar (~34px)
    const masterBar = doc.createElement('div');
    masterBar.style.display = 'flex';
    masterBar.style.alignItems = 'center';
    masterBar.style.justifyContent = 'space-between';
    masterBar.style.padding = '6px 12px';
    masterBar.style.backgroundColor = 'var(--zo-bg, #ffffff)';
    masterBar.style.borderBottom = '1px solid var(--zo-border, #e2e8f0)';
    masterBar.style.flexShrink = '0';
    masterBar.style.boxSizing = 'border-box';

    const masterLeft = doc.createElement('div');
    masterLeft.style.display = 'flex';
    masterLeft.style.alignItems = 'center';
    masterLeft.style.gap = '8px';

    const masterChk = doc.createElement('input');
    masterChk.type = 'checkbox';
    masterChk.id = 'zo-master-chk';
    masterChk.style.cursor = 'pointer';
    masterLeft.appendChild(masterChk);

    const masterLabel = doc.createElement('label');
    masterLabel.htmlFor = 'zo-master-chk';
    masterLabel.textContent = 'Select All Profiles';
    masterLabel.style.fontSize = '12px';
    masterLabel.style.fontWeight = '500';
    masterLabel.style.color = 'var(--zo-text-primary, #0f172a)';
    masterLabel.style.cursor = 'pointer';
    masterLeft.appendChild(masterLabel);

    masterBar.appendChild(masterLeft);

    const countStatus = doc.createElement('span');
    countStatus.style.fontSize = '11.5px';
    countStatus.style.color = 'var(--zo-text-secondary, #475569)';
    masterBar.appendChild(countStatus);

    panel.appendChild(masterBar);

    // Scrollable Profiles List
    const listContainer = doc.createElement('div');
    listContainer.style.flex = '1';
    listContainer.style.overflowY = 'auto';
    listContainer.style.padding = '8px 12px';
    listContainer.style.display = 'flex';
    listContainer.style.flexDirection = 'column';
    listContainer.style.gap = '6px';
    listContainer.style.boxSizing = 'border-box';

    const selectedProfiles = new Set<string>(['general-scholar']);
    const checkboxes: Record<string, HTMLInputElement> = {};
    const rowElements: Record<string, HTMLElement> = {};

    const updateUIState = () => {
      const count = selectedProfiles.size;
      countStatus.textContent = `${count} of ${DOMAIN_PROFILES.length} selected`;

      if (count === 0) {
        masterChk.checked = false;
        masterChk.indeterminate = false;
      } else if (count === DOMAIN_PROFILES.length) {
        masterChk.checked = true;
        masterChk.indeterminate = false;
      } else {
        masterChk.checked = false;
        masterChk.indeterminate = true;
      }

      applyBtn.disabled = count === 0;
      footerSummary.textContent = `${count} profile${count === 1 ? '' : 's'} selected`;
    };

    masterChk.onchange = () => {
      const checkAll = masterChk.checked;
      selectedProfiles.clear();
      DOMAIN_PROFILES.forEach((p) => {
        if (checkAll) selectedProfiles.add(p.id);
        if (checkboxes[p.id]) checkboxes[p.id].checked = checkAll;
        if (rowElements[p.id]) {
          if (checkAll) {
            rowElements[p.id].classList.add('selected');
            rowElements[p.id].setAttribute('aria-checked', 'true');
          } else {
            rowElements[p.id].classList.remove('selected');
            rowElements[p.id].setAttribute('aria-checked', 'false');
          }
        }
      });
      updateUIState();
    };

    DOMAIN_PROFILES.forEach((profile) => {
      const row = doc.createElement('div');
      row.className = 'zo-row-card';
      row.setAttribute('role', 'checkbox');
      row.setAttribute('tabindex', '0');
      row.setAttribute('aria-checked', selectedProfiles.has(profile.id) ? 'true' : 'false');
      rowElements[profile.id] = row;

      const chk = doc.createElement('input');
      chk.type = 'checkbox';
      chk.checked = selectedProfiles.has(profile.id);
      chk.style.cursor = 'pointer';
      chk.style.marginTop = '2px';
      chk.style.flexShrink = '0';
      checkboxes[profile.id] = chk;

      const toggleSelection = () => {
        if (chk.checked) {
          selectedProfiles.add(profile.id);
          row.classList.add('selected');
          row.setAttribute('aria-checked', 'true');
        } else {
          selectedProfiles.delete(profile.id);
          row.classList.remove('selected');
          row.setAttribute('aria-checked', 'false');
        }
        updateUIState();
      };

      chk.onchange = (e) => {
        e.stopPropagation();
        toggleSelection();
      };

      row.onclick = (e) => {
        if (e.target !== chk) {
          chk.checked = !chk.checked;
          toggleSelection();
        }
      };

      row.onkeydown = (e: KeyboardEvent) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          chk.checked = !chk.checked;
          toggleSelection();
        }
      };

      row.appendChild(chk);

      const content = doc.createElement('div');
      content.style.flex = '1';
      content.style.minWidth = '0';
      content.style.display = 'flex';
      content.style.flexDirection = 'column';
      content.style.gap = '2px';

      // Line 1: Title + Category Pill
      const titleRow = doc.createElement('div');
      titleRow.style.display = 'flex';
      titleRow.style.alignItems = 'center';
      titleRow.style.justifyContent = 'space-between';
      titleRow.style.gap = '6px';

      const nameEl = doc.createElement('span');
      nameEl.textContent = profile.name;
      nameEl.style.fontSize = '12px';
      nameEl.style.fontWeight = '600';
      nameEl.style.color = 'var(--zo-text-primary, #0f172a)';
      titleRow.appendChild(nameEl);

      const catBadge = doc.createElement('span');
      catBadge.textContent = profile.category;
      catBadge.style.fontSize = '9.5px';
      catBadge.style.fontWeight = '500';
      catBadge.style.padding = '1px 5px';
      catBadge.style.borderRadius = '3px';
      catBadge.style.backgroundColor = 'var(--zo-surface-alt, #f1f5f9)';
      catBadge.style.color = 'var(--zo-text-muted, #64748b)';
      catBadge.style.whiteSpace = 'nowrap';
      titleRow.appendChild(catBadge);

      content.appendChild(titleRow);

      // Line 2: Description (max 2 lines)
      const descEl = doc.createElement('div');
      descEl.textContent = profile.description;
      descEl.className = 'zo-line-clamp-2 zo-wrap';
      descEl.style.fontSize = '11px';
      descEl.style.color = 'var(--zo-text-secondary, #475569)';
      descEl.style.lineHeight = '1.35';
      content.appendChild(descEl);

      // Line 3: Sample Tags (max 3 tags + '+N more' pill)
      const tagsRow = doc.createElement('div');
      tagsRow.style.display = 'flex';
      tagsRow.style.alignItems = 'center';
      tagsRow.style.gap = '4px';
      tagsRow.style.marginTop = '2px';
      tagsRow.style.flexWrap = 'wrap';

      const visibleTags = profile.sampleTags.slice(0, 3);
      visibleTags.forEach((tag) => {
        const tagPill = doc.createElement('span');
        tagPill.textContent = tag;
        tagPill.style.fontSize = '9.5px';
        tagPill.style.padding = '1px 4px';
        tagPill.style.borderRadius = '3px';
        tagPill.style.backgroundColor = 'var(--zo-surface, #f8fafc)';
        tagPill.style.color = 'var(--zo-text-secondary, #475569)';
        tagPill.style.border = '1px solid var(--zo-border, #e2e8f0)';
        tagsRow.appendChild(tagPill);
      });

      if (profile.sampleTags.length > 3) {
        const morePill = doc.createElement('span');
        morePill.textContent = `+${profile.sampleTags.length - 3} more`;
        morePill.style.fontSize = '9.5px';
        morePill.style.padding = '1px 4px';
        morePill.style.borderRadius = '3px';
        morePill.style.color = 'var(--zo-text-muted, #64748b)';
        tagsRow.appendChild(morePill);
      }

      content.appendChild(tagsRow);
      row.appendChild(content);

      if (chk.checked) {
        row.classList.add('selected');
      }

      listContainer.appendChild(row);
    });

    panel.appendChild(listContainer);

    // Sticky Bottom Action Footer
    const footer = doc.createElement('div');
    footer.style.display = 'flex';
    footer.style.alignItems = 'center';
    footer.style.justifyContent = 'space-between';
    footer.style.padding = '8px 12px';
    footer.style.backgroundColor = 'var(--zo-surface, #f8fafc)';
    footer.style.borderTop = '1px solid var(--zo-border, #e2e8f0)';
    footer.style.flexShrink = '0';
    footer.style.boxSizing = 'border-box';

    const footerSummary = doc.createElement('span');
    footerSummary.style.fontSize = '11.5px';
    footerSummary.style.color = 'var(--zo-text-secondary, #475569)';
    footer.appendChild(footerSummary);

    const applyBtn = doc.createElement('button');
    applyBtn.textContent = 'Apply Selected Profiles';
    applyBtn.className = 'zo-btn zo-btn-primary';
    applyBtn.onclick = async () => {
      if (selectedProfiles.size === 0) return;
      applyBtn.disabled = true;
      applyBtn.textContent = 'Applying...';

      try {
        const combinedYaml = combineTaxonomyProfiles(Array.from(selectedProfiles));
        const res = await this.setTaxonomy(combinedYaml);
        if (res.success) {
          onApplied(combinedYaml);
        } else {
          alert(`Failed to apply combined taxonomy: ${res.error}`);
        }
      } catch (err: any) {
        alert(`Error combining profiles: ${err?.message || err}`);
      } finally {
        applyBtn.disabled = false;
        applyBtn.textContent = 'Apply Selected Profiles';
      }
    };
    footer.appendChild(applyBtn);

    panel.appendChild(footer);

    updateUIState();
    container.appendChild(panel);
  }

  /**
   * Tab 2: YAML Editor View (Bounded ~280-330px internally scrollable viewport, uncommitted state, line error navigation)
   */
  private static renderTabEditor(
    container: HTMLElement,
    doc: Document,
    currentSavedYaml: string,
    onSaved: (yamlString: string) => void
  ): void {
    const panel = doc.createElement('div');
    panel.id = 'zo-panel-editor';
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', 'zo-tab-editor');
    panel.style.display = 'flex';
    panel.style.flexDirection = 'column';
    panel.style.height = '100%';
    panel.style.width = '100%';
    panel.style.boxSizing = 'border-box';
    panel.style.overflow = 'hidden';

    // Status & Error Navigation Bar (~34px)
    const statusBar = doc.createElement('div');
    statusBar.style.display = 'flex';
    statusBar.style.alignItems = 'center';
    statusBar.style.justifyContent = 'space-between';
    statusBar.style.padding = '6px 12px';
    statusBar.style.backgroundColor = 'var(--zo-surface, #f8fafc)';
    statusBar.style.borderBottom = '1px solid var(--zo-border, #e2e8f0)';
    statusBar.style.flexShrink = '0';
    statusBar.style.boxSizing = 'border-box';
    statusBar.style.gap = '8px';

    const statusLeft = doc.createElement('div');
    statusLeft.style.display = 'flex';
    statusLeft.style.alignItems = 'center';
    statusLeft.style.gap = '8px';
    statusLeft.style.minWidth = '0';
    statusLeft.style.flex = '1';

    const validationMsg = doc.createElement('span');
    validationMsg.className = 'zo-wrap';
    validationMsg.style.fontSize = '11.5px';
    validationMsg.style.fontWeight = '500';
    statusLeft.appendChild(validationMsg);

    const lineNavBtn = doc.createElement('button');
    lineNavBtn.className = 'zo-btn zo-btn-sm';
    lineNavBtn.style.display = 'none';
    lineNavBtn.style.fontSize = '10px';
    lineNavBtn.style.padding = '1px 6px';
    statusLeft.appendChild(lineNavBtn);

    statusBar.appendChild(statusLeft);

    // Uncommitted State Indicator
    const dirtyIndicator = doc.createElement('div');
    dirtyIndicator.className = 'zo-dirty-indicator';
    dirtyIndicator.style.flexShrink = '0';
    statusBar.appendChild(dirtyIndicator);

    panel.appendChild(statusBar);

    // Bounded Scrollable Editor (~280-330px height, responsive)
    const editorFrame = doc.createElement('div');
    editorFrame.style.flex = '1';
    editorFrame.style.minHeight = '240px';
    editorFrame.style.maxHeight = '340px';
    editorFrame.style.margin = '8px 12px';
    editorFrame.style.border = '1px solid var(--zo-border-strong, #cbd5e1)';
    editorFrame.style.borderRadius = '4px';
    editorFrame.style.backgroundColor = 'var(--zo-editor-bg, #ffffff)';
    editorFrame.style.overflow = 'hidden';
    editorFrame.style.display = 'flex';
    editorFrame.style.boxSizing = 'border-box';

    const textarea = doc.createElement('textarea');
    textarea.value = this.editorDraftYaml ?? currentSavedYaml;
    textarea.spellcheck = false;
    textarea.style.width = '100%';
    textarea.style.height = '100%';
    textarea.style.padding = '8px 10px';
    textarea.style.fontFamily = 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';
    textarea.style.fontSize = '11.5px';
    textarea.style.lineHeight = '1.45';
    textarea.style.color = 'var(--zo-editor-text, #0f172a)';
    textarea.style.backgroundColor = 'transparent';
    textarea.style.border = 'none';
    textarea.style.outline = 'none';
    textarea.style.resize = 'none';
    textarea.style.overflow = 'auto';
    textarea.style.boxSizing = 'border-box';

    // Tab key indentation support
    textarea.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        textarea.value = textarea.value.substring(0, start) + '  ' + textarea.value.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + 2;
        textarea.dispatchEvent(new Event('input'));
      }
    });

    const updateValidation = () => {
      const text = textarea.value;
      this.editorDraftYaml = text;
      const isDirty = text !== currentSavedYaml;

      if (isDirty) {
        dirtyIndicator.textContent = '● Unsaved changes';
        dirtyIndicator.style.color = 'var(--zo-warning-text, #b45309)';
      } else {
        dirtyIndicator.textContent = 'Saved';
        dirtyIndicator.style.color = 'var(--zo-text-muted, #64748b)';
      }

      const val = validateTaxonomyYaml(text);
      if (val.valid) {
        validationMsg.textContent = `Valid (${val.tagCount} tags, ${val.namespaceCount} namespaces)`;
        validationMsg.style.color = 'var(--zo-success-text, #15803d)';
        lineNavBtn.style.display = 'none';
        saveBtn.disabled = !isDirty;
      } else {
        validationMsg.textContent = `Error: ${val.error || 'Invalid syntax'}`;
        validationMsg.style.color = 'var(--zo-error-text, #b91c1c)';
        saveBtn.disabled = true;

        // Parse line number for clickable error navigation
        const lineMatch = (val.error || '').match(/line\s+(\d+)/i) || (val.error || '').match(/at line (\d+)/i);
        if (lineMatch && lineMatch[1]) {
          const targetLine = parseInt(lineMatch[1], 10);
          lineNavBtn.textContent = `Go to line ${targetLine}`;
          lineNavBtn.style.display = 'inline-block';
          lineNavBtn.onclick = () => {
            const lines = text.split('\n');
            let charOffset = 0;
            for (let i = 0; i < targetLine - 1 && i < lines.length; i++) {
              charOffset += lines[i].length + 1;
            }
            const lineLength = lines[targetLine - 1] ? lines[targetLine - 1].length : 0;
            textarea.focus();
            textarea.setSelectionRange(charOffset, charOffset + lineLength);
            textarea.scrollTop = Math.max(0, (targetLine - 3) * 18);
          };
        } else {
          lineNavBtn.style.display = 'none';
        }
      }
    };

    textarea.addEventListener('input', updateValidation);
    editorFrame.appendChild(textarea);
    panel.appendChild(editorFrame);

    // Bottom Action Toolbar (~40px)
    const toolbar = doc.createElement('div');
    toolbar.style.display = 'flex';
    toolbar.style.alignItems = 'center';
    toolbar.style.justifyContent = 'space-between';
    toolbar.style.padding = '8px 12px';
    toolbar.style.backgroundColor = 'var(--zo-surface, #f8fafc)';
    toolbar.style.borderTop = '1px solid var(--zo-border, #e2e8f0)';
    toolbar.style.flexShrink = '0';
    toolbar.style.boxSizing = 'border-box';

    const resetBtn = doc.createElement('button');
    resetBtn.textContent = 'Reset to Default';
    resetBtn.className = 'zo-btn zo-btn-sm';
    resetBtn.onclick = () => {
      textarea.value = DEFAULT_TAXONOMY_YAML;
      updateValidation();
    };
    toolbar.appendChild(resetBtn);

    const saveBtn = doc.createElement('button');
    saveBtn.textContent = 'Save & Apply Changes';
    saveBtn.className = 'zo-btn zo-btn-primary';
    saveBtn.onclick = async () => {
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving...';
      const res = await this.setTaxonomy(textarea.value);
      if (res.success) {
        currentSavedYaml = textarea.value;
        this.editorDraftYaml = textarea.value;
        onSaved(textarea.value);
        updateValidation();
      } else {
        alert(`Failed to save: ${res.error}`);
      }
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save & Apply Changes';
    };
    toolbar.appendChild(saveBtn);

    panel.appendChild(toolbar);

    updateValidation();
    container.appendChild(panel);
  }

  /**
   * Tab 3: Import & Export View (Compact drop target 80-100px, explicit staging/validation step)
   */
  private static renderTabImportExport(
    container: HTMLElement,
    doc: Document,
    currentSavedYaml: string,
    onReviewInEditor: (stagedYaml: string) => void,
    onConfirmApplied: (appliedYaml: string) => void
  ): void {
    const panel = doc.createElement('div');
    panel.id = 'zo-panel-import-export';
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', 'zo-tab-import-export');
    panel.style.display = 'flex';
    panel.style.flexDirection = 'column';
    panel.style.height = '100%';
    panel.style.width = '100%';
    panel.style.overflowY = 'auto';
    panel.style.padding = '10px 12px';
    panel.style.gap = '10px';
    panel.style.boxSizing = 'border-box';

    // --- Section 1: Import Taxonomy ---
    const importCard = doc.createElement('div');
    importCard.style.padding = '10px 12px';
    importCard.style.border = '1px solid var(--zo-border, #e2e8f0)';
    importCard.style.borderRadius = '6px';
    importCard.style.backgroundColor = 'var(--zo-bg, #ffffff)';
    importCard.style.display = 'flex';
    importCard.style.flexDirection = 'column';
    importCard.style.gap = '6px';
    importCard.style.boxSizing = 'border-box';

    const importTitle = doc.createElement('div');
    importTitle.textContent = 'Import Taxonomy';
    importTitle.style.fontSize = '12px';
    importTitle.style.fontWeight = '600';
    importTitle.style.color = 'var(--zo-text-primary, #0f172a)';
    importCard.appendChild(importTitle);

    // Compact Drop Target (80-90px height)
    const dropzone = doc.createElement('div');
    dropzone.className = 'zo-dropzone';
    dropzone.style.height = '85px';

    const dropText = doc.createElement('span');
    dropText.textContent = 'Drop a .yml file here, or click to browse';
    dropzone.appendChild(dropText);

    const fileInput = doc.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.yml,.yaml,text/yaml,text/x-yaml,text/plain';
    fileInput.style.display = 'none';
    dropzone.appendChild(fileInput);

    dropzone.onclick = () => fileInput.click();

    // Drag-and-drop event handlers
    dropzone.addEventListener('dragover', (e: any) => {
      e.preventDefault();
      dropzone.classList.add('drag-active');
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('drag-active');
    });

    dropzone.addEventListener('drop', (e: any) => {
      e.preventDefault();
      dropzone.classList.remove('drag-active');
      const file = e.dataTransfer?.files?.[0];
      if (file) {
        readFile(file);
      }
    });

    fileInput.onchange = () => {
      const file = fileInput.files?.[0];
      if (file) {
        readFile(file);
      }
    };

    const readFile = (file: File) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const text = ev.target?.result as string;
        stageYaml(text);
      };
      reader.readAsText(file);
    };

    importCard.appendChild(dropzone);

    // Compact Paste Textarea (~65px)
    const pasteArea = doc.createElement('textarea');
    pasteArea.placeholder = 'Or paste taxonomy YAML content directly here...';
    pasteArea.style.width = '100%';
    pasteArea.style.height = '65px';
    pasteArea.style.padding = '6px 8px';
    pasteArea.style.fontFamily = 'ui-monospace, monospace';
    pasteArea.style.fontSize = '11px';
    pasteArea.style.border = '1px solid var(--zo-border-strong, #cbd5e1)';
    pasteArea.style.borderRadius = '4px';
    pasteArea.style.boxSizing = 'border-box';
    pasteArea.style.resize = 'none';

    pasteArea.addEventListener('input', () => {
      stageYaml(pasteArea.value);
    });

    importCard.appendChild(pasteArea);

    // Explicit Staging & Validation Section
    const stagingBox = doc.createElement('div');
    stagingBox.style.display = 'none';
    stagingBox.style.padding = '8px 10px';
    stagingBox.style.borderRadius = '4px';
    stagingBox.style.fontSize = '11.5px';
    stagingBox.style.boxSizing = 'border-box';
    stagingBox.style.marginTop = '4px';

    const stagingMsg = doc.createElement('div');
    stagingMsg.className = 'zo-wrap';
    stagingBox.appendChild(stagingMsg);

    const stagingActions = doc.createElement('div');
    stagingActions.style.display = 'flex';
    stagingActions.style.gap = '8px';
    stagingActions.style.marginTop = '6px';

    const reviewBtn = doc.createElement('button');
    reviewBtn.textContent = 'Review in YAML Editor';
    reviewBtn.className = 'zo-btn zo-btn-sm';
    stagingActions.appendChild(reviewBtn);

    const confirmApplyBtn = doc.createElement('button');
    confirmApplyBtn.textContent = 'Confirm & Apply Import';
    confirmApplyBtn.className = 'zo-btn zo-btn-sm zo-btn-primary';
    stagingActions.appendChild(confirmApplyBtn);

    stagingBox.appendChild(stagingActions);
    importCard.appendChild(stagingBox);

    const stageYaml = (text: string) => {
      this.stagedImportYaml = text;
      if (!text.trim()) {
        stagingBox.style.display = 'none';
        return;
      }

      const val = validateTaxonomyYaml(text);
      stagingBox.style.display = 'block';
      stagingMsg.textContent = '';
      const strongLabel = doc.createElement('strong');

      if (val.valid) {
        stagingBox.style.backgroundColor = 'var(--zo-success-bg, #f0fdf4)';
        stagingBox.style.border = '1px solid var(--zo-success-border, #bbf7d0)';
        stagingBox.style.color = 'var(--zo-success-text, #15803d)';
        strongLabel.textContent = 'Staged for Import: ';
        stagingMsg.appendChild(strongLabel);
        const detailSpan = doc.createElement('span');
        detailSpan.textContent = `${val.tagCount} tags across ${val.namespaceCount} namespaces (v${val.version || '1.0.0'})`;
        stagingMsg.appendChild(detailSpan);
        reviewBtn.style.display = 'inline-block';
        confirmApplyBtn.style.display = 'inline-block';

        reviewBtn.onclick = () => {
          onReviewInEditor(text);
        };

        confirmApplyBtn.onclick = async () => {
          confirmApplyBtn.disabled = true;
          confirmApplyBtn.textContent = 'Applying...';
          const res = await this.setTaxonomy(text);
          if (res.success) {
            onConfirmApplied(text);
          } else {
            alert(`Failed to apply imported taxonomy: ${res.error}`);
          }
          confirmApplyBtn.disabled = false;
          confirmApplyBtn.textContent = 'Confirm & Apply Import';
        };
      } else {
        stagingBox.style.backgroundColor = 'var(--zo-error-bg, #fef2f2)';
        stagingBox.style.border = '1px solid var(--zo-error-border, #fecaca)';
        stagingBox.style.color = 'var(--zo-error-text, #b91c1c)';
        strongLabel.textContent = 'Validation Error: ';
        stagingMsg.appendChild(strongLabel);
        const errorSpan = doc.createElement('span');
        errorSpan.textContent = val.error || 'Invalid syntax';
        stagingMsg.appendChild(errorSpan);
        reviewBtn.style.display = 'inline-block';
        confirmApplyBtn.style.display = 'none';

        reviewBtn.onclick = () => {
          onReviewInEditor(text);
        };
      }
    };

    panel.appendChild(importCard);

    // --- Section 2: Export Active Taxonomy ---
    const exportCard = doc.createElement('div');
    exportCard.style.padding = '10px 12px';
    exportCard.style.border = '1px solid var(--zo-border, #e2e8f0)';
    exportCard.style.borderRadius = '6px';
    exportCard.style.backgroundColor = 'var(--zo-bg, #ffffff)';
    exportCard.style.display = 'flex';
    exportCard.style.alignItems = 'center';
    exportCard.style.justifyContent = 'space-between';
    exportCard.style.boxSizing = 'border-box';

    const exportTitle = doc.createElement('div');
    exportTitle.textContent = 'Export Active Taxonomy';
    exportTitle.style.fontSize = '12px';
    exportTitle.style.fontWeight = '600';
    exportTitle.style.color = 'var(--zo-text-primary, #0f172a)';
    exportCard.appendChild(exportTitle);

    const exportBtns = doc.createElement('div');
    exportBtns.style.display = 'flex';
    exportBtns.style.gap = '6px';

    const downloadBtn = doc.createElement('button');
    downloadBtn.textContent = 'Download .yml';
    downloadBtn.className = 'zo-btn zo-btn-sm';
    downloadBtn.onclick = () => {
      this.downloadFile(currentSavedYaml, 'zotero-taxonomy.yml');
    };
    exportBtns.appendChild(downloadBtn);

    const copyBtn = doc.createElement('button');
    copyBtn.textContent = 'Copy YAML';
    copyBtn.className = 'zo-btn zo-btn-sm';
    copyBtn.onclick = async () => {
      if (typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(currentSavedYaml);
        copyBtn.textContent = '✓ Copied!';
        setTimeout(() => (copyBtn.textContent = 'Copy YAML'), 2000);
      }
    };
    exportBtns.appendChild(copyBtn);

    exportCard.appendChild(exportBtns);
    panel.appendChild(exportCard);

    container.appendChild(panel);
  }

  private static downloadFile(content: string, filename: string): void {
    if (typeof Blob !== 'undefined' && typeof document !== 'undefined') {
      const blob = new Blob([content], { type: 'text/yaml;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 200);
    }
  }

  private static getActiveTaxonomyYaml(): string {
    try {
      if (typeof ZoteroOrganiser !== 'undefined') {
        const inst = (ZoteroOrganiser as any)._instance;
        if (inst && typeof inst.getTaxonomyYaml === 'function') {
          return inst.getTaxonomyYaml();
        }
      }
    } catch (e) {}
    return DEFAULT_TAXONOMY_YAML;
  }

  private static async setTaxonomy(yamlString: string): Promise<{ success: boolean; error?: string }> {
    try {
      if (typeof ZoteroOrganiser !== 'undefined') {
        const inst = (ZoteroOrganiser as any)._instance;
        if (inst && typeof inst.setTaxonomy === 'function') {
          const res = await inst.setTaxonomy(yamlString);
          if (res.success) {
            this.notifyTaxonomyChanged(yamlString);
          }
          return res;
        }
      }
      // Standalone fallback
      const val = validateTaxonomyYaml(yamlString);
      if (val.valid) {
        this.notifyTaxonomyChanged(yamlString);
        return { success: true };
      }
      return { success: false, error: val.error };
    } catch (err: any) {
      return { success: false, error: err?.message || String(err) };
    }
  }
}
