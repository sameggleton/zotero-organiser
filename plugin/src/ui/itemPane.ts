import { extractDocumentVector } from '../core/document.js';
import { StateStore } from '../core/state.js';
import { OrganiserNotifier } from '../events/notifier.js';
import { TaxonomyManagerUI } from './taxonomyManager.js';

export class ItemPaneUI {
  private static registeredID: string | null = null;
  private static showMoreExpanded = new Map<string, boolean>();
  private static lastActiveContext: {
    container: HTMLElement;
    item: Zotero.Item;
    stateStore: StateStore;
    notifier: OrganiserNotifier;
  } | null = null;

  public static refresh(): void {
    if (this.lastActiveContext && this.lastActiveContext.container && this.lastActiveContext.item) {
      try {
        this.renderSectionBody(
          this.lastActiveContext.container,
          this.lastActiveContext.item,
          this.lastActiveContext.stateStore,
          this.lastActiveContext.notifier
        );
      } catch (e) {}
    }
  }

  public static register(stateStore: StateStore, notifier: OrganiserNotifier, rootURI: string): void {
    if (typeof Zotero === 'undefined') return;

    const manager = (Zotero as any).ItemPaneManager || (Zotero as any).ItemPane;
    if (!manager || typeof manager.registerSection !== 'function') {
      if (typeof Zotero.log === 'function') {
        Zotero.log('[zotero-organiser] ItemPaneManager.registerSection API not found');
      }
      return;
    }

    if (this.registeredID) return;

    const iconURI = rootURI ? `${rootURI}chrome/content/icons/tag-purple.svg` : '';

    try {
      this.registeredID = manager.registerSection({
        paneID: 'zotero-organiser-section',
        pluginID: 'zotero-organiser@sameggleton.dev',
        header: {
          l10nID: 'zotero-organiser-section-header',
          label: 'Taxonomy Organiser',
          icon: iconURI,
        },
        sidenav: {
          l10nID: 'zotero-organiser-section-sidenav',
          label: 'Taxonomy',
          icon: iconURI,
        },
        onRender: ({ body, item }: { body: HTMLElement; item: Zotero.Item }) => {
          if (!body || !item) return;
          this.renderSectionBody(body, item, stateStore, notifier);
        },
      });

      if (typeof Zotero.log === 'function') {
        Zotero.log('[zotero-organiser] registered ItemPane section successfully with ID: ' + this.registeredID);
      }
    } catch (e) {
      if (typeof Zotero.log === 'function') {
        Zotero.log(`[zotero-organiser] error registering section: ${e}`);
      }
    }
  }

  public static unregister(): void {
    if (typeof Zotero === 'undefined') return;
    const manager = (Zotero as any).ItemPaneManager || (Zotero as any).ItemPane;
    if (manager && this.registeredID) {
      try {
        manager.unregisterSection(this.registeredID);
      } catch (e) {
        // Ignore unregister errors
      }
      this.registeredID = null;
    }
  }

  private static renderSectionBody(
    container: HTMLElement,
    item: Zotero.Item,
    stateStore: StateStore,
    notifier: OrganiserNotifier
  ): void {
    if (!container) return;
    const doc = container.ownerDocument;
    if (!doc) return;

    this.lastActiveContext = { container, item, stateStore, notifier };

    container.innerHTML = '';
    container.style.padding = '10px';
    container.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    container.style.fontSize = '12px';
    container.style.color = '#1e293b';

    const loading = doc.createElement('div');
    loading.textContent = 'Loading classification...';
    loading.style.color = '#94a3b8';
    container.appendChild(loading);

    stateStore.getItem(item.key).then((stored) => {
      container.innerHTML = '';

      // --- Header Row: Status Badge & Classify / Settings Actions ---
      const headerRow = doc.createElement('div');
      headerRow.style.display = 'flex';
      headerRow.style.alignItems = 'center';
      headerRow.style.justifyContent = 'space-between';
      headerRow.style.marginBottom = '10px';

      const stateBadge = doc.createElement('span');
      stateBadge.style.padding = '3px 8px';
      stateBadge.style.borderRadius = '4px';
      stateBadge.style.fontWeight = '600';
      stateBadge.style.fontSize = '11px';

      const triageKeys = stored && stored.triageTags ? Object.keys(stored.triageTags) : [];
      const hasTriage = triageKeys.length > 0;

      if (!stored || stored.state === 'discovered') {
        stateBadge.textContent = 'Unprocessed';
        stateBadge.style.background = '#e2e8f0';
        stateBadge.style.color = '#475569';
      } else if (hasTriage || stored.state === 'needs_triage') {
        stateBadge.textContent = `Awaiting Review (${triageKeys.length})`;
        stateBadge.style.background = '#fef3c7';
        stateBadge.style.color = '#92400e';
        stateBadge.style.border = '1px solid #fde68a';
      } else if (stored.state === 'organised' || (stored.autoTags && stored.autoTags.size > 0)) {
        stateBadge.textContent = 'Organised';
        stateBadge.style.background = '#dcfce7';
        stateBadge.style.color = '#166534';
      } else if (stored.state === 'no_matches') {
        stateBadge.textContent = 'No Matches';
        stateBadge.style.background = '#f1f5f9';
        stateBadge.style.color = '#64748b';
      } else {
        stateBadge.textContent = stored.state;
        stateBadge.style.background = '#fee2e2';
        stateBadge.style.color = '#991b1b';
      }

      headerRow.appendChild(stateBadge);

      const classifyBtn = doc.createElement('button');
      classifyBtn.textContent = 'Classify Now';
      classifyBtn.style.cursor = 'pointer';
      classifyBtn.style.padding = '4px 10px';
      classifyBtn.style.fontSize = '11px';
      classifyBtn.style.fontWeight = '500';
      classifyBtn.style.borderRadius = '4px';
      classifyBtn.style.border = '1px solid #cbd5e1';
      classifyBtn.style.background = '#ffffff';
      classifyBtn.style.color = '#0f172a';
      classifyBtn.style.boxShadow = '0 1px 2px rgba(0,0,0,0.05)';

      classifyBtn.onclick = async () => {
        classifyBtn.disabled = true;
        classifyBtn.textContent = 'Classifying...';
        try {
          await notifier.processItem(item, true);
          classifyBtn.textContent = 'Done!';
        } catch (err: any) {
          classifyBtn.textContent = 'Error';
          if (typeof Zotero !== 'undefined' && Zotero.log) {
            Zotero.log(`[zotero-organiser] manual classify error: ${err}`);
          }
        }
        setTimeout(() => {
          this.renderSectionBody(container, item, stateStore, notifier);
        }, 300);
      };
      headerRow.appendChild(classifyBtn);
      container.appendChild(headerRow);

      // --- Top Suggestions (Review Card) ---
      if (hasTriage && stored) {
        const triageBox = doc.createElement('div');
        triageBox.style.background = '#fffbeb';
        triageBox.style.border = '1px solid #fde68a';
        triageBox.style.borderRadius = '6px';
        triageBox.style.padding = '8px';
        triageBox.style.marginBottom = '10px';

        const triageHeader = doc.createElement('div');
        triageHeader.style.display = 'flex';
        triageHeader.style.justifyContent = 'space-between';
        triageHeader.style.alignItems = 'center';
        triageHeader.style.marginBottom = '6px';

        const triageTitle = doc.createElement('span');
        triageTitle.textContent = 'Top Suggestions:';
        triageTitle.style.fontWeight = '600';
        triageTitle.style.fontSize = '11px';
        triageTitle.style.color = '#92400e';
        triageHeader.appendChild(triageTitle);

        const bulkActions = doc.createElement('div');
        bulkActions.style.display = 'flex';
        bulkActions.style.gap = '6px';

        const acceptAllBtn = doc.createElement('a');
        acceptAllBtn.textContent = 'Accept All';
        acceptAllBtn.href = '#';
        acceptAllBtn.style.fontSize = '10px';
        acceptAllBtn.style.color = '#15803d';
        acceptAllBtn.style.textDecoration = 'none';
        acceptAllBtn.style.fontWeight = '600';
        acceptAllBtn.onclick = async (e) => {
          e.preventDefault();
          const docVec = extractDocumentVector(item);
          for (let i = 0; i < triageKeys.length; i++) {
            const t = triageKeys[i];
            await stateStore.acceptTriageTag(item, t, {
              rank: i + 1,
              displayed: triageKeys,
              score: stored.triageTags[t],
              vector: docVec,
            });
          }
          this.renderSectionBody(container, item, stateStore, notifier);
        };
        bulkActions.appendChild(acceptAllBtn);

        const dismissAllBtn = doc.createElement('a');
        dismissAllBtn.textContent = 'Dismiss All';
        dismissAllBtn.href = '#';
        dismissAllBtn.style.fontSize = '10px';
        dismissAllBtn.style.color = '#b91c1c';
        dismissAllBtn.style.textDecoration = 'none';
        dismissAllBtn.style.fontWeight = '600';
        dismissAllBtn.onclick = async (e) => {
          e.preventDefault();
          const docVec = extractDocumentVector(item);
          for (let i = 0; i < triageKeys.length; i++) {
            const t = triageKeys[i];
            await stateStore.rejectTriageTag(item, t, {
              rank: i + 1,
              displayed: triageKeys,
              score: stored.triageTags[t],
              vector: docVec,
            });
          }
          this.renderSectionBody(container, item, stateStore, notifier);
        };
        bulkActions.appendChild(dismissAllBtn);
        triageHeader.appendChild(bulkActions);
        triageBox.appendChild(triageHeader);

        const triageList = doc.createElement('div');
        triageList.style.display = 'flex';
        triageList.style.flexDirection = 'column';
        triageList.style.gap = '5px';

        let rankCounter = 1;
        for (const [triageTag, score] of Object.entries(stored.triageTags)) {
          const currentRank = rankCounter++;
          const row = doc.createElement('div');
          row.style.display = 'flex';
          row.style.alignItems = 'center';
          row.style.justifyContent = 'space-between';
          row.style.background = '#ffffff';
          row.style.border = '1px solid #fef08a';
          row.style.borderRadius = '4px';
          row.style.padding = '3px 6px';

          const tagInfo = doc.createElement('div');
          tagInfo.style.display = 'flex';
          tagInfo.style.alignItems = 'center';
          tagInfo.style.gap = '6px';

          const tagName = doc.createElement('span');
          tagName.textContent = triageTag;
          tagName.style.fontWeight = '500';
          tagName.style.fontSize = '11px';
          tagName.style.color = '#334155';
          tagInfo.appendChild(tagName);

          const scorePill = doc.createElement('span');
          scorePill.textContent = `${Math.round(score * 100)}%`;
          scorePill.style.fontSize = '9px';
          scorePill.style.color = '#854d0e';
          scorePill.style.background = '#fef9c3';
          scorePill.style.padding = '1px 4px';
          scorePill.style.borderRadius = '3px';
          tagInfo.appendChild(scorePill);
          row.appendChild(tagInfo);

          const btns = doc.createElement('div');
          btns.style.display = 'flex';
          btns.style.gap = '4px';

          // Accept button
          const acceptBtn = doc.createElement('button');
          acceptBtn.textContent = '✓';
          acceptBtn.title = 'Accept tag';
          acceptBtn.style.cursor = 'pointer';
          acceptBtn.style.border = 'none';
          acceptBtn.style.borderRadius = '3px';
          acceptBtn.style.background = '#22c55e';
          acceptBtn.style.color = '#ffffff';
          acceptBtn.style.padding = '1px 6px';
          acceptBtn.style.fontSize = '11px';
          acceptBtn.style.fontWeight = 'bold';
          acceptBtn.onclick = async () => {
            await stateStore.acceptTriageTag(item, triageTag, {
              rank: currentRank,
              displayed: triageKeys,
              score,
              vector: extractDocumentVector(item),
            });
            this.renderSectionBody(container, item, stateStore, notifier);
          };
          btns.appendChild(acceptBtn);

          // Reject button
          const rejectBtn = doc.createElement('button');
          rejectBtn.textContent = '✗';
          rejectBtn.title = 'Suppress tag';
          rejectBtn.style.cursor = 'pointer';
          rejectBtn.style.border = 'none';
          rejectBtn.style.borderRadius = '3px';
          rejectBtn.style.background = '#ef4444';
          rejectBtn.style.color = '#ffffff';
          rejectBtn.style.padding = '1px 6px';
          rejectBtn.style.fontSize = '11px';
          rejectBtn.style.fontWeight = 'bold';
          rejectBtn.onclick = async () => {
            await stateStore.rejectTriageTag(item, triageTag, {
              rank: currentRank,
              displayed: triageKeys,
              score,
              vector: extractDocumentVector(item),
            });
            this.renderSectionBody(container, item, stateStore, notifier);
          };
          btns.appendChild(rejectBtn);

          row.appendChild(btns);
          triageList.appendChild(row);
        }
        triageBox.appendChild(triageList);
        container.appendChild(triageBox);
      }

      // --- Expandable Lower-Scoring Candidates Section ---
      const candidateEntries = stored && stored.candidateTags ? Object.entries(stored.candidateTags) : [];
      if (candidateEntries.length > 0 && stored) {
        const isExpanded = this.showMoreExpanded.get(item.key) || false;

        const moreToggle = doc.createElement('div');
        moreToggle.style.display = 'flex';
        moreToggle.style.alignItems = 'center';
        moreToggle.style.justifyContent = 'space-between';
        moreToggle.style.padding = '4px 6px';
        moreToggle.style.background = '#f8fafc';
        moreToggle.style.border = '1px solid #e2e8f0';
        moreToggle.style.borderRadius = '4px';
        moreToggle.style.cursor = 'pointer';
        moreToggle.style.marginBottom = '8px';
        moreToggle.onclick = () => {
          this.showMoreExpanded.set(item.key, !isExpanded);
          this.renderSectionBody(container, item, stateStore, notifier);
        };

        const toggleLabel = doc.createElement('span');
        toggleLabel.textContent = isExpanded
          ? `▲ Hide Additional Candidates`
          : `▼ More Suggestions (${candidateEntries.length})`;
        toggleLabel.style.fontSize = '11px';
        toggleLabel.style.fontWeight = '500';
        toggleLabel.style.color = '#475569';
        moreToggle.appendChild(toggleLabel);

        const subHint = doc.createElement('span');
        subHint.textContent = isExpanded ? '' : 'Lower match scores';
        subHint.style.fontSize = '9px';
        subHint.style.color = '#94a3b8';
        moreToggle.appendChild(subHint);
        container.appendChild(moreToggle);

        if (isExpanded) {
          const candBox = doc.createElement('div');
          candBox.style.display = 'flex';
          candBox.style.flexDirection = 'column';
          candBox.style.gap = '4px';
          candBox.style.marginBottom = '10px';
          candBox.style.padding = '6px';
          candBox.style.background = '#f8fafc';
          candBox.style.border = '1px solid #e2e8f0';
          candBox.style.borderRadius = '4px';

          const displayedSecondary = candidateEntries.slice(0, 10).map((c) => c[0]);

          for (let i = 0; i < candidateEntries.slice(0, 10).length; i++) {
            const [candTag, score] = candidateEntries[i];
            const secondaryRank = triageKeys.length + i + 1;

            const row = doc.createElement('div');
            row.style.display = 'flex';
            row.style.alignItems = 'center';
            row.style.justifyContent = 'space-between';
            row.style.background = '#ffffff';
            row.style.border = '1px solid #e2e8f0';
            row.style.borderRadius = '3px';
            row.style.padding = '2px 6px';

            const tagInfo = doc.createElement('div');
            tagInfo.style.display = 'flex';
            tagInfo.style.alignItems = 'center';
            tagInfo.style.gap = '6px';

            const tagName = doc.createElement('span');
            tagName.textContent = candTag;
            tagName.style.fontSize = '11px';
            tagName.style.color = '#64748b';
            tagInfo.appendChild(tagName);

            const scorePill = doc.createElement('span');
            scorePill.textContent = `${Math.round(score * 100)}%`;
            scorePill.style.fontSize = '9px';
            scorePill.style.color = '#64748b';
            scorePill.style.background = '#f1f5f9';
            scorePill.style.padding = '1px 3px';
            scorePill.style.borderRadius = '2px';
            tagInfo.appendChild(scorePill);
            row.appendChild(tagInfo);

            const addBtn = doc.createElement('button');
            addBtn.textContent = '+ Add';
            addBtn.style.cursor = 'pointer';
            addBtn.style.border = '1px solid #cbd5e1';
            addBtn.style.borderRadius = '3px';
            addBtn.style.background = '#ffffff';
            addBtn.style.color = '#334155';
            addBtn.style.padding = '1px 5px';
            addBtn.style.fontSize = '10px';
            addBtn.onclick = async () => {
              await stateStore.acceptTriageTag(item, candTag, {
                rank: secondaryRank,
                displayed: displayedSecondary,
                score,
                vector: extractDocumentVector(item),
              });
              this.renderSectionBody(container, item, stateStore, notifier);
            };
            row.appendChild(addBtn);
            candBox.appendChild(row);
          }
          container.appendChild(candBox);
        }
      }

      // --- Quick Taxonomy Tag Search / Add ---
      const searchBox = doc.createElement('div');
      searchBox.style.marginBottom = '10px';

      const taxonomy = notifier.getTaxonomy();
      const allTags = taxonomy ? Array.from(taxonomy.classifierTags()).sort() : [];
      const currentApplied = stored ? stored.autoTags : new Set<string>();
      const availableToAdd = allTags.filter((t) => !currentApplied.has(t));

      if (availableToAdd.length > 0) {
        const searchInput = doc.createElement('input');
        searchInput.type = 'text';
        searchInput.placeholder = '🔍 Search & add taxonomy tag...';
        searchInput.style.width = '100%';
        searchInput.style.boxSizing = 'border-box';
        searchInput.style.padding = '4px 6px';
        searchInput.style.fontSize = '11px';
        searchInput.style.border = '1px solid #cbd5e1';
        searchInput.style.borderRadius = '4px';

        const dropdown = doc.createElement('div');
        dropdown.style.display = 'none';
        dropdown.style.maxHeight = '120px';
        dropdown.style.overflowY = 'auto';
        dropdown.style.background = '#ffffff';
        dropdown.style.border = '1px solid #cbd5e1';
        dropdown.style.borderRadius = '4px';
        dropdown.style.marginTop = '2px';
        dropdown.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';

        searchInput.oninput = () => {
          const query = searchInput.value.toLowerCase().trim();
          dropdown.innerHTML = '';
          if (!query) {
            dropdown.style.display = 'none';
            return;
          }

          const matches = availableToAdd.filter((t) => t.toLowerCase().includes(query)).slice(0, 8);
          if (matches.length === 0) {
            dropdown.style.display = 'none';
            return;
          }

          for (const match of matches) {
            const itemDiv = doc.createElement('div');
            itemDiv.textContent = match;
            itemDiv.style.padding = '4px 8px';
            itemDiv.style.cursor = 'pointer';
            itemDiv.style.fontSize = '11px';
            itemDiv.onmouseover = () => {
              itemDiv.style.background = '#f1f5f9';
            };
            itemDiv.onmouseout = () => {
              itemDiv.style.background = '#ffffff';
            };
            itemDiv.onclick = async () => {
              await stateStore.addCustomTaxonomyTag(
                item,
                match,
                taxonomy?.version,
                extractDocumentVector(item)
              );
              searchInput.value = '';
              dropdown.style.display = 'none';
              this.renderSectionBody(container, item, stateStore, notifier);
            };
            dropdown.appendChild(itemDiv);
          }
          dropdown.style.display = 'block';
        };

        searchBox.appendChild(searchInput);
        searchBox.appendChild(dropdown);
        container.appendChild(searchBox);
      }

      // --- Active Organiser Tags Section ---
      if (stored && stored.autoTags.size > 0) {
        const autoSection = doc.createElement('div');
        autoSection.style.marginBottom = '8px';

        const autoTitle = doc.createElement('div');
        autoTitle.style.fontWeight = '600';
        autoTitle.style.fontSize = '11px';
        autoTitle.style.color = '#475569';
        autoTitle.style.marginBottom = '4px';
        autoTitle.textContent = `Organiser Tags (${stored.autoTags.size}):`;
        autoSection.appendChild(autoTitle);

        const tagList = doc.createElement('div');
        tagList.style.display = 'flex';
        tagList.style.flexWrap = 'wrap';
        tagList.style.gap = '4px';

        for (const tag of stored.autoTags) {
          const pill = doc.createElement('span');
          pill.style.display = 'inline-flex';
          pill.style.alignItems = 'center';
          pill.style.gap = '4px';
          pill.style.padding = '2px 6px';
          pill.style.background = '#f3e8ff';
          pill.style.color = '#6b21a8';
          pill.style.borderRadius = '12px';
          pill.style.fontSize = '11px';
          pill.style.border = '1px solid #e9d5ff';

          const tagText = doc.createElement('span');
          tagText.textContent = tag;
          pill.appendChild(tagText);

          const removeBtn = doc.createElement('span');
          removeBtn.textContent = '×';
          removeBtn.title = 'Remove and suppress tag';
          removeBtn.style.cursor = 'pointer';
          removeBtn.style.fontWeight = 'bold';
          removeBtn.style.marginLeft = '2px';
          removeBtn.style.color = '#9333ea';
          removeBtn.onclick = async () => {
            await stateStore.removeAutoTag(item, tag, extractDocumentVector(item));
            this.renderSectionBody(container, item, stateStore, notifier);
          };
          pill.appendChild(removeBtn);
          tagList.appendChild(pill);
        }
        autoSection.appendChild(tagList);
        container.appendChild(autoSection);
      } else if (stored && stored.state === 'no_matches' && !hasTriage) {
        const noMatchMsg = doc.createElement('div');
        noMatchMsg.textContent = 'No matching tags found. Use the search box above to add tags.';
        noMatchMsg.style.fontSize = '11px';
        noMatchMsg.style.color = '#94a3b8';
        noMatchMsg.style.fontStyle = 'italic';
        noMatchMsg.style.marginBottom = '6px';
        container.appendChild(noMatchMsg);
      }

      // --- Suppressed Tags Section ---
      if (stored && stored.suppressedTags.size > 0) {
        const suppSection = doc.createElement('div');
        suppSection.style.marginTop = '8px';
        suppSection.style.paddingTop = '6px';
        suppSection.style.borderTop = '1px dashed #e2e8f0';

        const suppTitle = doc.createElement('div');
        suppTitle.style.fontWeight = '600';
        suppTitle.style.fontSize = '10px';
        suppTitle.style.color = '#94a3b8';
        suppTitle.style.marginBottom = '2px';
        suppTitle.textContent = `Suppressed Tags (${stored.suppressedTags.size}):`;
        suppSection.appendChild(suppTitle);

        const suppList = doc.createElement('div');
        suppList.style.display = 'flex';
        suppList.style.flexWrap = 'wrap';
        suppList.style.gap = '4px';

        for (const suppTag of stored.suppressedTags) {
          const suppPill = doc.createElement('span');
          suppPill.style.display = 'inline-flex';
          suppPill.style.alignItems = 'center';
          suppPill.style.gap = '3px';
          suppPill.style.fontSize = '10px';
          suppPill.style.color = '#94a3b8';
          suppPill.style.background = '#f8fafc';
          suppPill.style.border = '1px solid #e2e8f0';
          suppPill.style.borderRadius = '3px';
          suppPill.style.padding = '1px 4px';

          const text = doc.createElement('span');
          text.textContent = suppTag;
          suppPill.appendChild(text);

          const unsuppBtn = doc.createElement('a');
          unsuppBtn.textContent = '↺';
          unsuppBtn.title = 'Unsuppress tag';
          unsuppBtn.href = '#';
          unsuppBtn.style.textDecoration = 'none';
          unsuppBtn.style.color = '#64748b';
          unsuppBtn.style.fontWeight = 'bold';
          unsuppBtn.onclick = async (e) => {
            e.preventDefault();
            await stateStore.unsuppressTag(item.key, suppTag);
            this.renderSectionBody(container, item, stateStore, notifier);
          };
          suppPill.appendChild(unsuppBtn);
          suppList.appendChild(suppPill);
        }
        suppSection.appendChild(suppList);
        container.appendChild(suppSection);
      }
    });
  }
}
