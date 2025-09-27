/* global bootstrap, Choices */
(function(){
  const apiBase = '/api/driver-cards';
  const allowedMetricTypeNames = new Set([
    'Behavioral Observation',
    'Self-Assessment/Survey',
    'Peer/360 Feedback',
    'Objective KPI',
    'Output/Deliverable Quality',
    'Formal Assessment/Test'
  ]);

  const state = {
    deleteTarget: null,
    alertTimer: null,
    modalInstance: null,
    deleteModalInstance: null,
    metricTypeChoices: null,
    frameworkOptions: [],
    frameworkMap: new Map(),
    selectedFrameworkIds: new Set(),
    frameworkSuggestionListenerAdded: false,
  };

  const els = {};

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function initFrameworkPicker(){
    if(!els.frameworkSelect) return;

    state.frameworkOptions = Array.from(els.frameworkSelect.options)
      .map(opt => ({ id: String(opt.value || '').trim(), name: (opt.text || '').trim() }))
      .filter(opt => opt.id !== '' && opt.name !== '');

    state.frameworkMap = new Map(state.frameworkOptions.map(opt => [opt.id, opt]));

    const initiallySelected = Array.from(els.frameworkSelect.selectedOptions).map(opt => String(opt.value));
    state.selectedFrameworkIds = new Set(initiallySelected);
    renderFrameworkChips();
    renderFrameworkSuggestions('');

    if(els.frameworkSearch && !state.frameworkSuggestionListenerAdded){
      els.frameworkSearch.addEventListener('input', handleFrameworkSearchInput);
      els.frameworkSearch.addEventListener('focus', () => renderFrameworkSuggestions(els.frameworkSearch.value));
      document.addEventListener('click', handleFrameworkSuggestionBlur);
      state.frameworkSuggestionListenerAdded = true;
    }
  }

  function handleFrameworkSearchInput(){
    const term = (els.frameworkSearch?.value || '').trim();
    renderFrameworkSuggestions(term);
  }

  function handleFrameworkSuggestionBlur(event){
    if(!els.frameworkSuggestions || !els.frameworkSearch) return;
    if(event.target === els.frameworkSearch || els.frameworkSuggestions.contains(event.target)) return;
    els.frameworkSuggestions.classList.add('d-none');
  }

  function renderFrameworkSuggestions(term){
    if(!els.frameworkSuggestions) return;
    const normalized = term.toLowerCase();
    const suggestions = state.frameworkOptions
      .filter(opt => !state.selectedFrameworkIds.has(opt.id))
      .filter(opt => !normalized || opt.name.toLowerCase().includes(normalized))
      .slice(0, 8);

    els.frameworkSuggestions.innerHTML = '';

    if(!suggestions.length){
      els.frameworkSuggestions.classList.add('d-none');
      return;
    }

    for(const opt of suggestions){
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'list-group-item list-group-item-action';
      item.textContent = opt.name;
      item.dataset.id = opt.id;
      item.addEventListener('click', () => {
        addFramework(opt.id);
        if(els.frameworkSearch){
          els.frameworkSearch.value = '';
        }
        renderFrameworkSuggestions('');
        els.frameworkSearch?.focus();
      });
      els.frameworkSuggestions.appendChild(item);
    }

    els.frameworkSuggestions.classList.remove('d-none');
  }

  function addFramework(id){
    if(!id || !state.frameworkMap.has(id)) return;
    state.selectedFrameworkIds.add(id);
    syncFrameworkSelect();
    renderFrameworkChips();
  }

  function removeFramework(id){
    if(!id) return;
    state.selectedFrameworkIds.delete(id);
    syncFrameworkSelect();
    renderFrameworkChips();
  }

  function renderFrameworkChips(){
    if(!els.frameworkChips) return;
    els.frameworkChips.innerHTML = '';
    if(state.selectedFrameworkIds.size === 0){
      const muted = document.createElement('span');
      muted.className = 'text-muted small';
      muted.textContent = 'No frameworks selected.';
      els.frameworkChips.appendChild(muted);
      syncFrameworkSelect();
      return;
    }

    for(const id of state.selectedFrameworkIds){
      const opt = state.frameworkMap.get(id);
      if(!opt) continue;
      const chip = document.createElement('span');
      chip.className = 'badge rounded-pill text-bg-primary d-inline-flex align-items-center gap-2 fw-medium';

      const label = document.createElement('span');
      label.textContent = opt.name;
      chip.appendChild(label);

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'btn btn-sm btn-outline-light rounded-circle d-flex align-items-center justify-content-center px-1 py-0 border-0';
      removeBtn.innerHTML = '<span aria-hidden="true">&times;</span>';
      removeBtn.setAttribute('aria-label', `Remove ${opt.name}`);
      removeBtn.addEventListener('click', () => {
        removeFramework(id);
        renderFrameworkSuggestions(els.frameworkSearch?.value || '');
      });

      chip.appendChild(removeBtn);
      els.frameworkChips.appendChild(chip);
    }

    syncFrameworkSelect();
  }

  function syncFrameworkSelect(){
    if(!els.frameworkSelect) return;
    const selectedArray = Array.from(state.selectedFrameworkIds);
    Array.from(els.frameworkSelect.options).forEach(opt => {
      opt.selected = selectedArray.includes(String(opt.value));
    });
  }

  function init(){
    cacheElements();
    if(!els.tableBody) return;
    initChoices();
    initFrameworkPicker();
    initModals();
    bindEvents();
    renderLoading();
    loadCards();
  }

  function cacheElements(){
    els.tableBody = document.querySelector('#driver-cards-table tbody');
    els.refreshBtn = document.getElementById('dc-refresh');
    els.addBtn = document.getElementById('dc-add');
    els.alertBox = document.getElementById('dc-alert');
    els.alertMessage = document.getElementById('dc-alert-message');
    els.form = document.getElementById('driver-card-form');
    els.modalElement = document.getElementById('driverCardModal');
    els.modalTitle = document.getElementById('driverCardModalLabel');
    els.saveBtn = document.getElementById('dc-save');
    els.deleteModalElement = document.getElementById('driverCardDeleteModal');
    els.deleteName = document.getElementById('dc-delete-name');
    els.deleteConfirm = document.getElementById('dc-confirm-delete');

    els.hiddenId = document.getElementById('dc-id');
    els.name = document.getElementById('dc-name');
    els.description = document.getElementById('dc-description');
    els.outcome = document.getElementById('dc-outcome');
    els.metricType = document.getElementById('dc-metric-type');
    els.frameworkSelect = document.getElementById('dc-frameworks');
    els.frameworkSearch = document.getElementById('dc-framework-search');
    els.frameworkSuggestions = document.getElementById('dc-framework-suggestions');
    els.frameworkChips = document.getElementById('dc-framework-chips');
    els.kind = document.getElementById('dc-kind');
    els.identifier = document.getElementById('dc-identifier');
    els.tags = document.getElementById('dc-tags');
    els.biases = document.getElementById('dc-biases');
    els.nudges = document.getElementById('dc-nudges');
    els.status = document.getElementById('dc-status');
    els.chainHidden = document.getElementById('dc-chain');
    els.chainDrives = document.getElementById('dc-chain-drives');
    els.chainKpis = document.getElementById('dc-chain-kpis');
    els.chainOutcomes = document.getElementById('dc-chain-outcomes');
    els.dataCollection = document.getElementById('dc-data-collection');
    els.frequency = document.getElementById('dc-frequency');
  }

  function initChoices(){
    if(els.metricType && !state.metricTypeChoices){
      state.metricTypeChoices = new Choices(els.metricType, {
        removeItemButton: true,
        removeItems: true,
        searchEnabled: true,
        searchResultLimit: 6,
        shouldSort: false,
        placeholder: true,
        placeholderValue: 'Select metric types',
        searchPlaceholderValue: 'Search metric types…',
        classNames: {
          containerInner: 'choices__inner',
        },
        callbackOnCreateTemplates: (template) => ({
          item: (classNames, data) => template(`
            <div class="${classNames.item} ${data.highlighted ? classNames.highlightedState : classNames.itemSelectable}" data-item data-id="${data.id}" data-value="${data.value}" ${data.active ? 'aria-selected="true"' : ''}>${data.label}</div>
          `),
          choice: (classNames, data) => template(`
            <div class="${classNames.item} ${classNames.itemChoice} ${data.disabled ? classNames.itemDisabled : classNames.itemSelectable}" data-select-text="" data-choice data-id="${data.id}" data-value="${data.value}" ${data.disabled ? 'data-choice-disabled aria-disabled="true"' : 'data-choice-selectable'}>
              ${data.label}
            </div>
          `)
        })
      });
      applyChoicesStyling(state.metricTypeChoices, { variant: 'metric' });
      enforceMetricTypeOptions();
    }
  }

  function applyChoicesStyling(instance, options = {}){
    if(!instance) return;
    const variant = options.variant || 'default';
    const inner = instance.containerInner;
    if(inner && inner.classList){
      if(variant === 'framework'){
        inner.classList.remove('form-control');
        inner.classList.add('choices-inner-plain');
      } else if(!inner.classList.contains('form-control')){
        inner.classList.add('form-control');
      }
    }
    const outer = instance.containerOuter;
    if(outer && outer.classList && variant === 'framework'){
      outer.classList.add('choices-framework');
    }
  }

  function enforceMetricTypeOptions(){
    if(!state.metricTypeChoices) return;
    const toDisable = [];
    state.metricTypeChoices._store.choices.forEach(choice => {
      if(choice.value && !allowedMetricTypeNames.has(choice.label.trim())){
        toDisable.push(choice.id);
      }
    });
    toDisable.forEach(id => state.metricTypeChoices._store.removeChoice(id));
    if(state.metricTypeChoices._store.choices.length === 0){
      const warn = document.createElement('div');
      warn.className = 'form-text text-warning';
      warn.textContent = 'No approved metric types available. Add them under Admin ? Metric Types.';
      els.metricType?.closest('.form-group, .col-md-6, .mb-3')?.appendChild(warn);
    }
  }

  function bindEvents(){
    if(els.refreshBtn){
      els.refreshBtn.addEventListener('click', loadCards);
    }
    if(els.addBtn){
      els.addBtn.addEventListener('click', openCreateModal);
    }
    if(els.saveBtn){
      els.saveBtn.addEventListener('click', handleSave);
    }
    if(els.deleteConfirm){
      els.deleteConfirm.addEventListener('click', handleDeleteConfirm);
    }
    if(els.tableBody){
      els.tableBody.addEventListener('click', handleTableClick);
    }
    if(els.modalElement){
      els.modalElement.addEventListener('hidden.bs.modal', resetForm);
    }
  }

  function initModals(){
    if(els.modalElement && !state.modalInstance && typeof bootstrap !== 'undefined'){
      state.modalInstance = new bootstrap.Modal(els.modalElement, { backdrop: 'static' });
    }
    if(els.deleteModalElement && !state.deleteModalInstance && typeof bootstrap !== 'undefined'){
      state.deleteModalInstance = new bootstrap.Modal(els.deleteModalElement);
    }
  }

  async function loadCards(){
    renderLoading();
    try{
      const res = await fetch(`${apiBase}?page_size=200&sort=name`, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' });
      const data = await res.json().catch(() => ({}));
      console.log('[driver-cards] API status', res.status, data);
      if(res.status === 401 || res.status === 403){
        throw new Error('Authentication failed. Please log in again.');
      }
      if(!res.ok){
        throw new Error(data.error || `Failed to load driver cards (${res.status})`);
      }
      const items = Array.isArray(data.items) ? data.items : [];
      console.log('[driver-cards] items length', items.length);
      renderTable(items);
    }catch(err){
      renderErrorRow(err.message || 'Unable to load driver cards.');
      showAlert('danger', err.message || 'Unable to load driver cards.');
    }
  }

  function renderLoading(){
    if(!els.tableBody) return;
    els.tableBody.innerHTML = '';
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="10" class="text-center py-4 text-muted">Loading…</td>';
    els.tableBody.appendChild(row);
  }

  function renderErrorRow(message){
    if(!els.tableBody) return;
    els.tableBody.innerHTML = '';
    const row = document.createElement('tr');
    row.innerHTML = `<td colspan="10" class="text-center text-danger py-4">${escapeHtml(message)}</td>`;
    els.tableBody.appendChild(row);
  }

  function renderTable(items){
    if(!els.tableBody) return;
    els.tableBody.innerHTML = '';
    if(!items.length){
      const row = document.createElement('tr');
      row.innerHTML = '<td colspan="10" class="text-center text-muted py-4">No driver cards found.</td>';
      els.tableBody.appendChild(row);
      console.log('[driver-cards] renderTable empty state rendered');
      return;
    }

    for(const item of items){
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="align-middle">${escapeHtml(item.name || '')}</td>
        <td class="align-middle">${formatTypeBadge(item.kind)}</td>
        <td class="align-middle">${formatBadge(item.outcome?.name)}</td>
        <td class="align-middle">${formatMetricTypeTags(item.metric_type)}</td>
        <td class="align-middle">${formatTextOrDash(item.classification?.data_collection)}</td>
        <td class="align-middle">${formatTextOrDash(item.classification?.frequency)}</td>
        <td class="align-middle">${formatIdentifier(item.identifier_type)}</td>
        <td class="align-middle">${formatTags(item.tags)}</td>
        <td class="align-middle">${formatStatus(item.is_active)}</td>
        <td class="align-middle text-nowrap">
          <button class="btn btn-outline-primary btn-sm me-1" data-action="edit" data-id="${item.id}"><i class="bi bi-pencil"></i></button>
          <button class="btn btn-outline-danger btn-sm" data-action="delete" data-id="${item.id}" data-name="${escapeHtml(item.name || '')}"><i class="bi bi-trash"></i></button>
        </td>
      `;
      els.tableBody.appendChild(tr);
    }
    console.log('[driver-cards] renderTable rows', els.tableBody.children.length);
  }

  function formatMetricTypeTags(metricType){
    if(!metricType) return '<span class="text-muted">—</span>';
    const types = [];
    if(metricType.name) types.push(metricType.name);
    if(Array.isArray(metricType.additional_types)){
      types.push(...metricType.additional_types);
    }
    if(!types.length) return '<span class="text-muted">—</span>';
    return types.map(label => `<span class="badge bg-primary-subtle text-primary me-1">${escapeHtml(label)}</span>`).join('');
  }

  function formatTextOrDash(value){
    if(!value) return '<span class="text-muted">—</span>';
    return escapeHtml(value);
  }

  function formatTypeBadge(kind){
    const normalized = (kind || 'driver').toLowerCase();
    const label = normalized.charAt(0).toUpperCase() + normalized.slice(1);
    return `<span class="badge bg-primary-subtle text-primary">${escapeHtml(label)}</span>`;
  }

  function formatBadge(value){
    if(!value) return '<span class="text-muted">—</span>';
    return `<span class="badge bg-light text-dark">${escapeHtml(value)}</span>`;
  }

  function formatIdentifier(value){
    if(!value) return '<span class="text-muted">—</span>';
    return `<span class="badge bg-light text-dark">${escapeHtml(String(value).toUpperCase())}</span>`;
  }

  function formatTags(tags){
    if(!Array.isArray(tags) || tags.length === 0) return '<span class="text-muted">—</span>';
    return tags.map(tag => `<span class="badge bg-secondary text-light me-1">${escapeHtml(tag)}</span>`).join('');
  }

  function formatStatus(isActive){
    if(isActive === false){
      return '<span class="badge bg-secondary">Inactive</span>';
    }
    return '<span class="badge bg-success-subtle text-success">Active</span>';
  }

  function handleTableClick(event){
    const actionBtn = event.target.closest('button[data-action]');
    if(!actionBtn) return;
    const id = Number(actionBtn.dataset.id);
    if(!Number.isFinite(id)) return;
    const action = actionBtn.dataset.action;
    if(action === 'edit'){
      openEditModal(id);
    } else if(action === 'delete'){
      openDeleteModal(id, actionBtn.dataset.name || 'this driver card');
    }
  }

  function openCreateModal(){
    resetForm();
    if(els.form){
      els.form.dataset.mode = 'create';
    }
    if(els.modalTitle){
      els.modalTitle.textContent = 'Add Driver Card';
    }
    clearAlert();
    state.modalInstance?.show();
  }

  async function openEditModal(id){
    try{
      setSavingState(false);
      clearAlert();
      const res = await fetch(`${apiBase}/${id}`, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' });
      const data = await res.json().catch(() => ({}));
      if(res.status === 401 || res.status === 403){
        throw new Error('Authentication failed. Please log in again.');
      }
      if(!res.ok){
        throw new Error(data.error || `Failed to load driver card (${res.status})`);
      }
      const card = data.driver_card || {};
      resetForm();
      populateForm(card);
      if(els.form){
        els.form.dataset.mode = 'edit';
      }
      if(els.modalTitle){
        els.modalTitle.textContent = 'Edit Driver Card';
      }
      clearAlert();
      state.modalInstance?.show();
    }catch(err){
      showAlert('danger', err.message || 'Failed to load driver card.');
    }
  }

  function populateForm(card){
    if(!els.form) return;
    if(els.hiddenId) els.hiddenId.value = card.id || '';
    if(els.name) els.name.value = card.name || '';
    if(els.description) els.description.value = card.description || '';
    if(els.outcome) els.outcome.value = card.outcome?.id || '';

    setMetricTypeSelection(card);

    if(els.kind) els.kind.value = (card.kind || 'driver').toLowerCase();
    if(els.identifier) els.identifier.value = (card.identifier_type || 'concept').toLowerCase();
    if(els.tags) els.tags.value = Array.isArray(card.tags) ? card.tags.join(', ') : '';
    if(els.biases) els.biases.value = Array.isArray(card.related_biases) ? card.related_biases.join(', ') : '';
    if(els.nudges) els.nudges.value = Array.isArray(card.related_nudges) ? card.related_nudges.join(', ') : '';
    if(els.status) els.status.value = card.is_active === false ? 'false' : 'true';
    if(els.dataCollection) els.dataCollection.value = card.classification?.data_collection || '';
    if(els.frequency) els.frequency.value = card.classification?.frequency || '';

    applyDriverChainToForm(card);
    setFrameworkSelection(card);
  }

  function setMetricTypeSelection(card){
    if(!state.metricTypeChoices) return;
    const selected = [];
    if(card.metric_type?.id){
      selected.push({ value: String(card.metric_type.id), label: card.metric_type.name || 'Metric Type' });
    }
    if(Array.isArray(card.metric_type?.additional_types)){
      card.metric_type.additional_types.forEach(label => {
        const choice = state.metricTypeChoices._store.choices.find(c => c.label === label);
        if(choice){
          selected.push({ value: choice.value, label: choice.label });
        } else {
          selected.push({ value: `label:${label}`, label });
        }
      });
    }
    state.metricTypeChoices.removeActiveItems();
    selected.forEach(item => {
      state.metricTypeChoices.setChoiceByValue(item.value);
    });
  }

  function setFrameworkSelection(card){
    if(!state.frameworkChoices) return;
    const selectedIds = Array.isArray(card.frameworks) ? card.frameworks
      .map(fw => fw?.id)
      .filter(id => id !== undefined && id !== null)
      .map(id => String(id)) : [];
    state.frameworkChoices.removeActiveItems();
    selectedIds.forEach(id => state.frameworkChoices.setChoiceByValue(id));
  }

  function resetForm(){
    if(!els.form) return;
    els.form.reset();
    els.form.dataset.mode = 'create';
    if(els.hiddenId) els.hiddenId.value = '';
    if(els.status) els.status.value = 'true';
    if(els.chainHidden) els.chainHidden.value = '';
    if(els.chainDrives) els.chainDrives.value = '';
    if(els.chainKpis) els.chainKpis.value = '';
    if(els.chainOutcomes) els.chainOutcomes.value = '';
    if(els.dataCollection) els.dataCollection.value = '';
    if(els.frequency) els.frequency.value = '';
    if(state.metricTypeChoices){
      state.metricTypeChoices.removeActiveItems();
    }
    if(state.frameworkChoices){
      state.frameworkChoices.removeActiveItems();
    }
    setSavingState(false);
  }

  async function handleSave(){
    if(!els.form) return;
    try{
      const payload = buildPayloadFromForm();
      const isEdit = els.form.dataset.mode === 'edit';
      const targetId = Number(els.hiddenId?.value);
      const url = isEdit ? `${apiBase}/${targetId}` : apiBase;
      const method = isEdit ? 'PUT' : 'POST';

      setSavingState(true);
      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
        credentials: 'same-origin',
      });
      const data = await res.json().catch(() => ({}));
      if(res.status === 401 || res.status === 403){
        throw new Error('Authentication failed. Please log in again.');
      }
      if(!res.ok){
        throw new Error(data.error || `Request failed (${res.status})`);
      }

      state.modalInstance?.hide();
      showAlert('success', isEdit ? 'Driver card updated successfully.' : 'Driver card created successfully.');
      resetForm();
      loadCards();
    }catch(err){
      showAlert('danger', err.message || 'Unable to save driver card.');
    }finally{
      setSavingState(false);
    }
  }

  function buildPayloadFromForm(){
    const name = (els.name?.value || '').trim();
    const description = (els.description?.value || '').trim();
    const outcomeId = parseInt(els.outcome?.value || '', 10);
    const metricTypeIds = getMetricTypeIds();
    const frameworkIds = getFrameworkIds();

    if(!name){
      throw new Error('Name is required.');
    }
    if(!Number.isFinite(outcomeId)){
      throw new Error('Select an L&D outcome.');
    }
    if(!metricTypeIds.length){
      throw new Error('Select at least one metric type.');
    }

    const payload = {
      name,
      description,
      outcome_id: outcomeId,
      metric_type_id: metricTypeIds[0],
      additional_metric_type_ids: metricTypeIds.slice(1),
      framework_ids: frameworkIds,
      kind: (els.kind?.value || 'driver').toLowerCase(),
      identifier_type: (els.identifier?.value || '').toLowerCase() || null,
      tags: splitCommaValues(els.tags?.value),
      related_biases: splitCommaValues(els.biases?.value),
      related_nudges: splitCommaValues(els.nudges?.value),
      is_active: String(els.status?.value) !== 'false',
      data_collection: (els.dataCollection?.value || '').trim() || null,
      frequency: (els.frequency?.value || '').trim() || null,
    };

    const drivers = splitCommaValues(els.chainDrives?.value);
    const kpis = splitCommaValues(els.chainKpis?.value);
    const outcomes = splitCommaValues(els.chainOutcomes?.value);
    const chain = buildDriverChainPayload(drivers, kpis, outcomes, payload);
    if(chain){
      payload.driver_chain = chain;
      if(els.chainHidden){
        els.chainHidden.value = JSON.stringify(chain, null, 2);
      }
    } else if(els.chainHidden){
      els.chainHidden.value = '';
    }

    return payload;
  }

  function getMetricTypeIds(){
    if(!state.metricTypeChoices) return [];
    return (state.metricTypeChoices.getValue(true) || [])
      .map(val => {
        if(String(val).startsWith('label:')) return null;
        const parsed = parseInt(val, 10);
        return Number.isFinite(parsed) ? parsed : null;
      })
      .filter((id, index, arr) => id !== null && arr.indexOf(id) === index);
  }

  function getFrameworkIds(){
    if(!state.frameworkChoices) return [];
    return (state.frameworkChoices.getValue(true) || [])
      .map(val => parseInt(val, 10))
      .filter((id, index, arr) => Number.isFinite(id) && arr.indexOf(id) === index);
  }

  function buildDriverChainPayload(drivers, kpis, outcomes, payload){
    const chain = {};
    if(drivers.length) chain.drives_behaviors = drivers;
    if(kpis.length) chain.measured_by_kpis = kpis;
    if(outcomes.length) chain.leads_to_outcomes = outcomes;
    if(payload.data_collection || payload.frequency || payload.kind || payload.tags.length || payload.related_biases.length || payload.related_nudges.length){
      chain._meta = {
        ...(payload.kind ? { kind: payload.kind } : {}),
        ...(payload.tags.length ? { tags: payload.tags } : {}),
        ...(payload.related_biases.length ? { related_biases: payload.related_biases } : {}),
        ...(payload.related_nudges.length ? { related_nudges: payload.related_nudges } : {}),
        ...(payload.data_collection ? { data_collection: payload.data_collection } : {}),
        ...(payload.frequency ? { frequency: payload.frequency } : {}),
      };
    }
    return Object.keys(chain).length ? chain : null;
  }

  function applyDriverChainToForm(card){
    const fields = extractChainFields(card);
    if(els.chainDrives) els.chainDrives.value = fields.drives.join(', ');
    if(els.chainKpis) els.chainKpis.value = fields.kpis.join(', ');
    if(els.chainOutcomes) els.chainOutcomes.value = fields.outcomes.join(', ');
    if(els.chainHidden) els.chainHidden.value = JSON.stringify(buildDriverChainPayload(fields.drives, fields.kpis, fields.outcomes, {
      kind: card.kind,
      tags: card.tags || [],
      related_biases: card.related_biases || [],
      related_nudges: card.related_nudges || [],
      data_collection: card.classification?.data_collection || null,
      frequency: card.classification?.frequency || null,
    }) || '', null, 2);
  }

  function extractChainFields(card){
    const result = { drives: [], kpis: [], outcomes: [] };
    if(!card) return result;

    const assign = (items, key) => {
      if(Array.isArray(items) && items.length){
        result[key] = items;
      }
    };

    if(Array.isArray(card.driver_chain)){
      for(const stage of card.driver_chain){
        const key = stage?.key;
        const items = Array.isArray(stage?.items) ? stage.items : [];
        if(key === 'drives_behaviors' || key === 'driven_by_behaviors' || key === 'driven_by_concepts'){
          assign(items, 'drives');
        }
        if(key === 'measured_by_kpis' || key === 'measures_behaviors'){
          assign(items, 'kpis');
        }
        if(key === 'leads_to_outcomes' || key === 'leads_to_outcome'){
          assign(items, 'outcomes');
        }
      }
    }

    return result;
  }

  function splitCommaValues(value){
    if(!value) return [];
    return value.split(',').map(v => v.trim()).filter(Boolean);
  }

  function openDeleteModal(id, name){
    state.deleteTarget = { id, name };
    if(els.deleteName){
      els.deleteName.textContent = name || 'this driver card';
    }
    clearAlert();
    state.deleteModalInstance?.show();
  }

  async function handleDeleteConfirm(){
    if(!state.deleteTarget) return;
    const { id, name } = state.deleteTarget;
    if(!Number.isFinite(Number(id))) return;

    if(els.deleteConfirm){
      els.deleteConfirm.disabled = true;
      els.deleteConfirm.textContent = 'Deleting…';
    }

    try{
      const res = await fetch(`${apiBase}/${id}`, {
        method: 'DELETE',
        headers: { 'Accept': 'application/json' },
        credentials: 'same-origin',
      });
      const data = await res.json().catch(() => ({}));
      if(res.status === 401 || res.status === 403){
        throw new Error('Authentication failed. Please log in again.');
      }
      if(!res.ok){
        throw new Error(data.error || `Failed to delete driver card (${res.status})`);
      }
      state.deleteModalInstance?.hide();
      showAlert('success', `Deleted driver card: ${name || id}.`);
      state.deleteTarget = null;
      loadCards();
    }catch(err){
      showAlert('danger', err.message || 'Unable to delete driver card.');
    }finally{
      if(els.deleteConfirm){
        els.deleteConfirm.disabled = false;
        els.deleteConfirm.textContent = 'Delete';
      }
    }
  }

  function setSavingState(isSaving){
    if(!els.saveBtn) return;
    if(isSaving){
      if(!els.saveBtn.dataset.originalText){
        els.saveBtn.dataset.originalText = els.saveBtn.textContent;
      }
      els.saveBtn.disabled = true;
      els.saveBtn.textContent = 'Saving…';
    } else {
      els.saveBtn.disabled = false;
      if(els.saveBtn.dataset.originalText){
        els.saveBtn.textContent = els.saveBtn.dataset.originalText;
      }
    }
  }

  function showAlert(type, message){
    if(!els.alertBox || !els.alertMessage) return;
    els.alertBox.classList.remove('alert-success', 'alert-danger', 'alert-warning', 'alert-info');
    els.alertBox.classList.add(`alert-${type}`);
    els.alertMessage.textContent = message;
    els.alertBox.style.display = 'block';
    if(state.alertTimer){
      window.clearTimeout(state.alertTimer);
    }
    state.alertTimer = window.setTimeout(() => {
      clearAlert();
    }, 5000);
  }

  function clearAlert(){
    if(state.alertTimer){
      window.clearTimeout(state.alertTimer);
      state.alertTimer = null;
    }
    if(els.alertBox){
      els.alertBox.style.display = 'none';
    }
  }

  function escapeHtml(str){
    return String(str || '').replace(/[&<>"']/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[char] || char);
  }
})();
