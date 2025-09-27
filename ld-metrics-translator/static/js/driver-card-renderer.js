/* Shared Driver Card Renderer */
(function (global) {
  'use strict';

  const STAGE_ICONS = {
    drives_behaviors: '🧠',
    driven_by_behaviors: '🧠',
    driven_by_concepts: '🧭',
    measures_behaviors: '📊',
    measured_by_kpis: '📈',
    indicates_concepts: '🎯',
    leads_to_outcomes: '🚀',
    default: '🔹'
  };

  function createEl(tag, className, textContent) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (typeof textContent === 'string') el.textContent = textContent;
    return el;
  }

  function toArray(value) {
    if (!value && value !== 0) return [];
    if (Array.isArray(value)) return value.slice();
    return [value];
  }

  function uniqueStrings(values) {
    const seen = new Set();
    const result = [];
    toArray(values).forEach((raw) => {
      if (raw === null || raw === undefined) return;
      const text = String(raw).trim();
      if (!text) return;
      const key = text.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      result.push(text);
    });
    return result;
  }

  function parseJsonMaybe(value) {
    if (typeof value === 'string') {
      try { return JSON.parse(value); } catch (_) { return value; }
    }
    return value;
  }

  function chainDefinition(identifierType) {
    switch ((identifierType || '').toLowerCase()) {
      case 'behavior':
        return [
          { key: 'driven_by_concepts', title: 'Driven by Concept', props: ['driven_by_concepts', 'drives_behaviors'] },
          { key: 'measured_by_kpis', title: 'Measured by KPI', props: ['measured_by_kpis'] },
          { key: 'leads_to_outcomes', title: 'Leads to Outcome', props: ['leads_to_outcomes'] }
        ];
      case 'kpi':
        return [
          { key: 'measures_behaviors', title: 'Measures Behavior', props: ['measures_behaviors', 'drives_behaviors'] },
          { key: 'indicates_concepts', title: 'Indicates Concept', props: ['indicates_concepts', 'driven_by_concepts'] },
          { key: 'leads_to_outcomes', title: 'Leads to Outcome', props: ['leads_to_outcomes'] }
        ];
      case 'outcome':
        return [
          { key: 'driven_by_behaviors', title: 'Driven by Behavior', props: ['driven_by_behaviors', 'drives_behaviors'] },
          { key: 'driven_by_concepts', title: 'Driven by Concept', props: ['driven_by_concepts'] },
          { key: 'measured_by_kpis', title: 'Measured by KPI', props: ['measured_by_kpis'] }
        ];
      case 'concept':
      default:
        return [
          { key: 'drives_behaviors', title: 'Drives Behavior', props: ['drives_behaviors'] },
          { key: 'measured_by_kpis', title: 'Measured by KPI', props: ['measured_by_kpis'] },
          { key: 'leads_to_outcomes', title: 'Leads to Outcome', props: ['leads_to_outcomes'] }
        ];
    }
  }

  function normalizeChain(rawChain, identifierType) {
    if (!rawChain) return [];
    const parsed = parseJsonMaybe(rawChain);
    if (Array.isArray(parsed)) {
      return parsed
        .filter((stage) => stage && stage.key && stage.key !== '_meta')
        .map((stage, index) => ({
          key: stage.key,
          title: stage.title || chainDefinition(identifierType)[index]?.title || stage.key,
          items: uniqueStrings(stage.items)
        }));
    }
    if (parsed && typeof parsed === 'object') {
      const def = chainDefinition(identifierType);
      return def.map((stage, index) => ({
        key: stage.key,
        title: stage.title || stage.key,
        items: uniqueStrings(stage.props.flatMap((prop) => uniqueStrings(parsed[prop])))
      }));
    }
    return [];
  }

  function extractMeta(raw) {
    if (raw && typeof raw === 'object') {
      if (Array.isArray(raw)) {
        return raw.find((stage) => stage && stage.key === '_meta') || {};
      }
      if (raw._meta) return raw._meta;
    }
    return {};
  }

  function normalizeFrameworks(rawFrameworks) {
    const result = [];
    const seen = new Set();
    toArray(rawFrameworks).forEach((fw) => {
      if (!fw) return;
      let name = '';
      let id = null;
      let slug = null;
      if (typeof fw === 'string') {
        name = fw.trim();
      } else {
        name = String(fw.name || fw.title || '').trim();
        id = fw.id ?? fw.framework_id ?? null;
        slug = fw.slug ?? null;
      }
      if (!name) return;
      const key = `${id || ''}|${slug || ''}|${name.toLowerCase()}`;
      if (seen.has(key)) return;
      seen.add(key);
      result.push({ id, name, slug });
    });
    return result;
  }

  function normalizeCard(raw) {
    if (!raw) return null;
    if (raw.__normalized) return raw;
    const identifierType = (raw.identifier_type || raw.kind || 'concept').toLowerCase();
    const chain = normalizeChain(raw.driver_chain, identifierType);
    const chainMeta = extractMeta(parseJsonMaybe(raw.driver_chain));
    const metaObj = Object.assign({}, raw.metric_type_meta || {}, chainMeta);

    const classification = Object.assign({
      ld_outcome: raw.classification?.ld_outcome || raw.outcome?.name || raw.outcome_name || null,
      metric_type: raw.classification?.metric_type || raw.metric_type?.name || raw.metric_type_name || null,
      data_collection: raw.classification?.data_collection || raw.data_collection || metaObj.data_collection || null,
      frequency: raw.classification?.frequency || raw.frequency || metaObj.frequency || null
    }, raw.classification || {});

    const frameworks = normalizeFrameworks(
      raw.frameworks || raw.associated_frameworks || raw.metric_frameworks || metaObj.frameworks || []
    );

    const normalized = {
      __normalized: true,
      id: raw.id,
      name: raw.name || raw.title,
      description: raw.description || raw.summary || '',
      identifier_type: identifierType,
      kind: (raw.kind || identifierType || 'driver').toLowerCase(),
      outcome: raw.outcome || (raw.outcome_name ? { name: raw.outcome_name } : null),
      metric_type: raw.metric_type || (classification.metric_type ? { name: classification.metric_type } : null),
      driver_chain: chain,
      tags: uniqueStrings(raw.tags || metaObj.tags || []),
      related_biases: uniqueStrings(raw.related_biases || raw.biases || metaObj.related_biases || []),
      related_nudges: uniqueStrings(raw.related_nudges || raw.nudges || metaObj.related_nudges || []),
      frameworks,
      classification,
      meta: metaObj,
      raw
    };

    return normalized;
  }

  function renderStage(stage, options) {
    const stageEl = createEl('div', 'dc-stage');
    const title = createEl('div', 'dc-stage-title');
    const icon = createEl('span', 'dc-stage-icon', STAGE_ICONS[stage.key] || STAGE_ICONS.default);
    title.appendChild(icon);
    title.appendChild(document.createTextNode(stage.title || 'Stage'));
    stageEl.appendChild(title);

    const list = createEl('ul', 'dc-stage-list');
    const limit = options?.compact ? (options?.compactStageItemLimit ?? 2) : options?.stageItemLimit;
    const displayItems = typeof limit === 'number' && limit >= 0 ? stage.items.slice(0, limit) : stage.items;
    displayItems.forEach((item) => {
      const li = document.createElement('li');
      if (options && typeof options.onItemClick === 'function') {
        const button = createEl('button', 'dc-pill-link', item);
        button.title = options.itemTooltip || `Open preview for ${item}`;
        button.addEventListener('click', () => options.onItemClick(item, stage));
        li.appendChild(button);
      } else {
        li.textContent = item;
      }
      list.appendChild(li);
    });
    if (displayItems.length === 0 && options?.showEmptySlots) {
      const li = document.createElement('li');
      li.className = 'dc-empty';
      li.textContent = options.emptyLabel || 'No entries yet';
      list.appendChild(li);
    } else if (displayItems.length < stage.items.length) {
      const remaining = stage.items.length - displayItems.length;
      const li = document.createElement('li');
      li.className = 'dc-more';
      li.textContent = `+${remaining} more`;
      list.appendChild(li);
    }
    stageEl.appendChild(list);
    return stageEl;
  }

  function renderChain(chain, options) {
    const classes = ['dc-chain'];
    if (options?.compact) classes.push('dc-compact');
    if (options?.chainLayout === 'vertical') classes.push('dc-vertical');
    const wrap = createEl('div', classes.join(' '));
    chain.forEach((stage, index) => {
      wrap.appendChild(renderStage(stage, options));
      if (index < chain.length - 1) {
        wrap.appendChild(createEl('div', 'dc-arrow', '→'));
      }
    });
    return wrap;
  }

  function renderList(label, items, chipClass, onClick) {
    if (!items || !items.length) return null;
    const block = createEl('div', 'dc-related');
    block.appendChild(createEl('div', 'dc-label', label));
    const list = createEl('div', 'dc-related-chips');
    items.forEach((item) => {
      const chip = createEl('button', `tag-chip${chipClass ? ` ${chipClass}` : ''}`, item);
      if (typeof onClick === 'function') {
        chip.addEventListener('click', () => onClick(item));
      }
      list.appendChild(chip);
    });
    block.appendChild(list);
    return block;
  }

  function renderFrameworkSection(frameworks, options) {
    if (!frameworks || !frameworks.length) return null;
    const fw = createEl('div', 'dc-fw');
    fw.appendChild(createEl('div', 'dc-label', 'Associated Frameworks'));
    const list = createEl('ul', 'dc-fw-list');
    frameworks.forEach((fwItem) => {
      const li = document.createElement('li');
      if (options && typeof options.onFrameworkClick === 'function') {
        const button = createEl('button', 'dc-fw-link', fwItem.name);
        button.addEventListener('click', () => options.onFrameworkClick(fwItem));
        li.appendChild(button);
      } else {
        const a = createEl('a', 'dc-fw-link', fwItem.name);
        a.href = `/playbook?q=${encodeURIComponent(fwItem.name)}`;
        li.appendChild(a);
      }
      list.appendChild(li);
    });
    fw.appendChild(list);
    return fw;
  }

  function renderClassification(classification) {
    const block = createEl('div', 'dc-class');
    block.appendChild(createEl('div', 'dc-label', 'Classification Details'));
    const grid = createEl('div', 'dc-grid');
    const entries = [
      ['L&D OUTCOME', classification.ld_outcome],
      ['METRIC TYPE', classification.metric_type],
      ['DATA COLLECTION', classification.data_collection],
      ['FREQUENCY', classification.frequency]
    ];
    entries.forEach(([label, value]) => {
      const pill = createEl('div', 'dc-pill');
      pill.appendChild(createEl('div', 'dc-pill-k', label));
      pill.appendChild(createEl('div', 'dc-pill-v', value || '—'));
      grid.appendChild(pill);
    });
    block.appendChild(grid);
    return block;
  }

  function createCardElement(rawCard, options) {
    const card = normalizeCard(rawCard);
    if (!card) return createEl('div', 'driver-card driver-card--empty', 'No card data');
    const root = createEl('div', 'driver-card');
    if (card.id) root.dataset.cardId = String(card.id);
    if (card.kind) root.dataset.cardKind = card.kind;
    const header = createEl('div', 'dc-header');
    header.appendChild(createEl('div', 'dc-title', card.name || 'Driver'));
    const badge = createEl('div', 'dc-badge', (card.identifier_type || 'concept').toString().toUpperCase());
    badge.dataset.kind = card.identifier_type || 'concept';
    header.appendChild(badge);
    root.appendChild(header);

    if (card.description) {
      root.appendChild(createEl('p', 'dc-desc', card.description));
    }

    if (options && typeof options.renderTags === 'function') {
      const tagsEl = options.renderTags(card);
      if (tagsEl) root.appendChild(tagsEl);
    } else if (card.tags && card.tags.length) {
      const tagsWrap = createEl('div', 'dc-tags');
      const list = createEl('div', 'dc-related-chips');
      card.tags.forEach((tag) => {
        const chip = createEl('span', 'tag-chip tag-chip--static', `#${tag}`);
        list.appendChild(chip);
      });
      tagsWrap.appendChild(list);
      root.appendChild(tagsWrap);
    }

    const fwSection = renderFrameworkSection(card.frameworks, options);
    if (fwSection) root.appendChild(fwSection);

    const chain = renderChain(card.driver_chain, options);
    root.appendChild(chain);

    const biasBlock = renderList('Related Biases', card.related_biases, '', options?.onBiasClick);
    if (biasBlock) root.appendChild(biasBlock);
    const nudgeBlock = renderList('Recommended Nudges', card.related_nudges, 'tag-chip--nudge', options?.onNudgeClick);
    if (nudgeBlock) root.appendChild(nudgeBlock);

    root.appendChild(renderClassification(card.classification));

    if (options && typeof options.renderActions === 'function') {
      const actions = createEl('div', 'dc-actions');
      options.renderActions(actions, card);
      root.appendChild(actions);
    }

    return root;
  }

  function renderInto(container, card, options) {
    const target = typeof container === 'string' ? document.getElementById(container) : container;
    if (!target) return null;
    target.innerHTML = '';
    const el = createCardElement(card, options);
    target.appendChild(el);
    return el;
  }

  const api = {
    normalize: normalizeCard,
    createCardElement,
    render: renderInto,
    renderChain,
    renderClassification
  };

  global.DriverCardRenderer = api;
})(window);
