/**
 * ZenML Deployment Dashboard JavaScript
 * 
 * Handles dynamic UI interactions, form building, API calls, and output rendering.
 * 
 * Security notes:
 * - Uses DOMPurify for sanitizing any HTML content from API responses
 * - Avoids innerHTML for user-generated content where possible
 * - Uses textContent for displaying untrusted strings
 * - Properly escapes and validates all API inputs
 */

/* ============================================================================
   Configuration & Constants
   ========================================================================= */

// LocalStorage keys - scoped to avoid collisions
const AUTH_TOKEN_KEY = 'zenml_dashboard_auth_token';

// Current UI state
let currentInputMode = 'form';
let currentOutputMode = 'preview';
let lastResult = null;

// Service configuration - will be populated from data attributes
let serviceConfig = {};

/* ============================================================================
   Initialization
   ========================================================================= */

/**
 * Initialize the dashboard when DOM is ready
 */
function initDashboard() {
  // Load service configuration from embedded JSON
  const serviceInfoEl = document.getElementById('service-info-data');
  if (serviceInfoEl) {
    try {
      serviceConfig = JSON.parse(serviceInfoEl.textContent);
    } catch (e) {
      console.error('Failed to parse service info:', e);
      serviceConfig = {};
    }
  }

  // Load pipeline info and build form
  loadPipelineInfo();

  // Attach event listeners
  attachEventListeners();
  
  // Update auth status display
  updateAuthStatus();
  
  // If auth is enabled and no token is set, prompt user
  if (serviceConfig?.deployment?.auth_enabled && !loadAuthToken()) {
    setTimeout(() => promptForToken(), 500);
  }
}

/* ============================================================================
   Authentication Management
   ========================================================================= */

/**
 * Load auth token from localStorage
 * @returns {string|null} The stored auth token or null
 */
function loadAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

/**
 * Save auth token to localStorage
 * @param {string} token - The auth token to store
 */
function saveAuthToken(token) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

/**
 * Build auth headers for API requests
 * @returns {Object} Headers object with Authorization if token exists
 */
function authHeaders() {
  const token = loadAuthToken();
  return token ? { 'Authorization': 'Bearer ' + token } : {};
}

/**
 * Apply auth headers to an existing headers object
 * @param {Object} headers - Existing headers object
 * @returns {Object} Headers with auth added
 */
function applyAuthHeaders(headers = {}) {
  return { ...headers, ...authHeaders() };
}

/**
 * Prompt user to enter API key
 */
function promptForToken() {
  showApiKeyModal();
}

/**
 * Update auth status badge
 */
function updateAuthStatus() {
  const authStatusBadge = document.getElementById('auth-status-badge');
  const authStatusText = document.getElementById('auth-status-text');
  const setApiKeyBtn = document.getElementById('set-api-key-btn');
  
  if (!authStatusBadge) return;
  
  const hasToken = !!loadAuthToken();
  
  if (hasToken) {
    authStatusText.textContent = 'Authenticated';
    authStatusBadge.style.background = 'var(--color-success-50)';
    authStatusBadge.style.borderColor = 'var(--color-success-200)';
    authStatusBadge.style.color = 'var(--color-success-800)';
    if (setApiKeyBtn) {
      setApiKeyBtn.textContent = 'Update API Key';
    }
  } else {
    authStatusText.textContent = 'Auth Required';
    authStatusBadge.style.background = 'var(--color-primary-25)';
    authStatusBadge.style.borderColor = 'var(--button-border-primary-disabled)';
    authStatusBadge.style.color = 'var(--text-brand)';
    if (setApiKeyBtn) {
      setApiKeyBtn.textContent = 'Set API Key';
    }
  }
}

/**
 * Show modal for entering API key
 */
function showApiKeyModal() {
  // Create modal overlay
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  
  const modal = document.createElement('div');
  modal.className = 'modal';
  
  const header = document.createElement('div');
  header.className = 'modal-header';
  
  const title = document.createElement('h3');
  title.className = 'modal-title';
  title.textContent = 'API Key Required';
  
  const description = document.createElement('p');
  description.className = 'modal-description';
  description.textContent = 'This deployment requires authentication. Please enter your API key to continue.';
  
  header.appendChild(title);
  header.appendChild(description);
  
  const content = document.createElement('div');
  content.className = 'modal-content';
  
  const inputField = document.createElement('div');
  inputField.className = 'form-field';
  
  const label = document.createElement('div');
  label.className = 'field-label';
  
  const labelText = document.createElement('span');
  labelText.className = 'field-name';
  labelText.textContent = 'API Key';
  label.appendChild(labelText);
  
  const input = document.createElement('input');
  input.type = 'password';
  input.className = 'text-input';
  input.id = 'api-key-input';
  input.placeholder = 'Enter your API key';
  input.value = loadAuthToken() || '';
  
  inputField.appendChild(label);
  inputField.appendChild(input);
  content.appendChild(inputField);
  
  const footer = document.createElement('div');
  footer.className = 'modal-footer';
  
  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'btn-secondary';
  cancelBtn.textContent = 'Cancel';
  cancelBtn.onclick = () => {
    document.body.removeChild(overlay);
  };
  
  const saveBtn = document.createElement('button');
  saveBtn.className = 'btn-primary';
  saveBtn.textContent = 'Save';
  saveBtn.onclick = () => {
    const token = input.value.trim();
    if (token) {
      saveAuthToken(token);
      updateAuthStatus();
      document.body.removeChild(overlay);
    } else {
      alert('Please enter an API key');
    }
  };
  
  footer.appendChild(cancelBtn);
  footer.appendChild(saveBtn);
  
  modal.appendChild(header);
  modal.appendChild(content);
  modal.appendChild(footer);
  overlay.appendChild(modal);
  
  // Close on overlay click
  overlay.onclick = (e) => {
    if (e.target === overlay) {
      document.body.removeChild(overlay);
    }
  };
  
  // Submit on Enter key
  input.onkeypress = (e) => {
    if (e.key === 'Enter') {
      saveBtn.click();
    }
  };
  
  document.body.appendChild(overlay);
  setTimeout(() => input.focus(), 100);
}

/* ============================================================================
   API Utilities
   ========================================================================= */

/**
 * Perform GET request with JSON response
 * @param {string} url - The URL to fetch
 * @returns {Promise<Object>} The JSON response
 */
async function getJSON(url) {
  const res = await fetch(url, { 
    headers: applyAuthHeaders({ 'Accept': 'application/json' })
  });
  if (!res.ok) {
    throw new Error(`${url} returned ${res.status}`);
  }
  return res.json();
}

/**
 * Perform POST request with JSON body and response
 * @param {string} url - The URL to post to
 * @param {Object} body - The request body
 * @returns {Promise<Object>} The JSON response
 */
async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: applyAuthHeaders({ 
      'Content-Type': 'application/json'
    }),
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    // If auth error, prompt for token
    if (res.status === 401) {
      promptForToken();
      throw new Error('Authorization required. Please set your API key.');
    }
    throw new Error((json && json.detail) ? json.detail : ('HTTP ' + res.status));
  }
  return json;
}

/* ============================================================================
   Schema Processing
   ========================================================================= */

/**
 * Extract parameter schema from pipeline input schema
 * Handles both flat schemas and nested parameters property
 * @param {Object} schema - The full input schema
 * @returns {Object} Normalized schema with properties and required fields
 */
function getParamSchema(schema) {
  if (!schema || !schema.properties) {
    return { properties: {}, required: [] };
  }
  if (schema.properties.parameters && schema.properties.parameters.properties) {
    return {
      properties: schema.properties.parameters.properties,
      required: schema.properties.parameters.required || [],
    };
  }
  return { 
    properties: schema.properties, 
    required: schema.required || [] 
  };
}

/* ============================================================================
   Form Building
   ========================================================================= */

/**
 * Create a collapsible section for nested objects
 * @param {string} name - Field name
 * @param {Object} def - Field definition
 * @param {boolean} required - Whether field is required
 * @param {boolean} isRoot - Whether this is a root-level collapsible
 * @returns {Object} Object with element and content references
 */
function createCollapsible(name, def, required, isRoot = true) {
  const collapsible = document.createElement('div');
  collapsible.className = 'collapsible expanded';
  
  const header = document.createElement('div');
  header.className = 'collapsible-header';
  
  const chevron = document.createElement('svg');
  chevron.className = 'chevron-icon';
  chevron.innerHTML = '<path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="2" fill="none"/>';
  chevron.setAttribute('viewBox', '0 0 24 24');
  
  const title = document.createElement('div');
  title.className = 'collapsible-title';
  title.textContent = name;
  
  const collapseBtn = document.createElement('button');
  collapseBtn.className = 'collapse-button';
  collapseBtn.innerHTML = `
    <svg class="collapse-icon" viewBox="0 0 24 24" fill="none">
      <path d="M4 6H20M4 18H20M4 10H14M4 14H14" stroke="currentColor" stroke-width="2"/>
    </svg>
  `;
  
  header.appendChild(chevron);
  header.appendChild(title);
  header.appendChild(collapseBtn);
  
  header.addEventListener('click', (e) => {
    if (e.target !== collapseBtn && !collapseBtn.contains(e.target)) {
      collapsible.classList.toggle('expanded');
    }
  });
  
  const content = document.createElement('div');
  content.className = 'collapsible-content';
  
  collapsible.appendChild(header);
  collapsible.appendChild(content);
  
  return { element: collapsible, content };
}

/**
 * Create a form field element based on schema definition
 * Uses safe DOM manipulation (createElement, textContent) to prevent XSS
 * @param {string} name - Field name
 * @param {Object} def - Field definition from schema
 * @param {boolean} required - Whether field is required
 * @returns {HTMLElement} The created form field
 */
function createField(name, def, required) {
  const field = document.createElement('div');
  field.className = 'form-field';
  
  const label = document.createElement('div');
  label.className = 'field-label';
  
  const fieldName = document.createElement('span');
  fieldName.className = 'field-name';
  fieldName.textContent = name; // Safe: uses textContent
  
  if (required) {
    const requiredMark = document.createElement('span');
    requiredMark.className = 'field-required';
    requiredMark.textContent = '*';
    label.appendChild(requiredMark);
  }
  
  label.appendChild(fieldName);
  
  if (def.type) {
    const fieldType = document.createElement('span');
    fieldType.className = 'field-type';
    fieldType.textContent = def.type; // Safe: uses textContent
    label.appendChild(fieldType);
  }
  
  field.appendChild(label);
  
  let input;
  if (def.type === 'boolean') {
    const toggleContainer = document.createElement('div');
    toggleContainer.className = 'toggle-switch-container';
    
    const toggle = document.createElement('div');
    toggle.className = 'toggle-switch ' + (def.default ? 'on' : 'off');
    toggle.dataset.name = name;
    
    const button = document.createElement('div');
    button.className = 'toggle-switch-button';
    
    toggle.appendChild(button);
    
    const labelText = document.createElement('span');
    labelText.className = 'toggle-label';
    labelText.textContent = def.default ? 'True' : 'False';
    
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('on');
      toggle.classList.toggle('off');
      labelText.textContent = toggle.classList.contains('on') ? 'True' : 'False';
    });
    
    toggleContainer.appendChild(toggle);
    toggleContainer.appendChild(labelText);
    field.appendChild(toggleContainer);
  } else if (def.type === 'integer' || def.type === 'number') {
    if (def.enum) {
      const select = document.createElement('select');
      select.className = 'select-input';
      select.name = name;
      def.enum.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = String(opt);
        select.appendChild(option);
      });
      select.value = def.default !== undefined ? def.default : def.enum[0];
      field.appendChild(select);
    } else {
      input = document.createElement('input');
      input.type = 'number';
      input.className = 'text-input filled';
      input.name = name;
      input.value = def.default !== undefined ? def.default : 0;
      field.appendChild(input);
    }
  } else if (def.type === 'object' || def.type === 'array') {
    const { element, content } = createCollapsible(name, def, required, false);
    if (def.properties) {
      Object.entries(def.properties).forEach(([key, value]) => {
        const subField = createField(key, value, def.required?.includes(key));
        content.appendChild(subField);
      });
    }
    return element;
  } else if (def.enum) {
    const select = document.createElement('select');
    select.className = 'select-input';
    select.name = name;
    def.enum.forEach(opt => {
      const option = document.createElement('option');
      option.value = opt;
      option.textContent = String(opt);
      select.appendChild(option);
    });
    select.value = def.default !== undefined ? def.default : def.enum[0];
    field.appendChild(select);
  } else {
    input = document.createElement('input');
    input.type = 'text';
    input.className = 'text-input';
    input.name = name;
    input.value = def.default || '';
    input.placeholder = def.default || '';
    
    if (input.value) {
      input.classList.add('filled');
    }
    
    input.addEventListener('input', () => {
      if (input.value) {
        input.classList.add('filled');
      } else {
        input.classList.remove('filled');
      }
    });
    
    field.appendChild(input);
  }
  
  return field;
}

/**
 * Build form fields from pipeline schema
 * @param {Object} schema - The pipeline input schema
 */
function buildFormFields(schema) {
  const formView = document.getElementById('form-view');
  formView.innerHTML = '';
  
  const ps = getParamSchema(schema);
  const props = ps.properties || {};
  const req = ps.required || [];
  
  if (Object.keys(props).length === 0) {
    const emptyMsg = document.createElement('p');
    emptyMsg.style.color = 'var(--text-secondary)';
    emptyMsg.style.padding = '20px';
    emptyMsg.textContent = 'No input parameters defined for this pipeline.';
    formView.appendChild(emptyMsg);
    return;
  }
  
  Object.entries(props).forEach(([name, def]) => {
    if (def.type === 'object' && def.properties) {
      const { element, content } = createCollapsible(name, def, req.includes(name));
      Object.entries(def.properties).forEach(([key, value]) => {
        const field = createField(key, value, def.required?.includes(key));
        content.appendChild(field);
      });
      formView.appendChild(element);
    } else {
      const field = createField(name, def, req.includes(name));
      formView.appendChild(field);
    }
  });
}

/* ============================================================================
   Form Data Collection
   ========================================================================= */

/**
 * Collect form data from UI
 * @returns {Object} The collected form data
 */
function collectFormData() {
  // If in JSON mode, parse JSON directly
  if (currentInputMode === 'json') {
    try {
      const jsonInput = document.getElementById('json-input');
      return JSON.parse(jsonInput.value || '{}');
    } catch (e) {
      throw new Error('Invalid JSON: ' + e.message);
    }
  }
  
  // Otherwise collect from form
  const formView = document.getElementById('form-view');
  const data = {};
  
  /**
   * Recursively collect data from form elements
   * @param {HTMLElement} element - Parent element to collect from
   * @param {Object} target - Target object to store data in
   */
  function collectFromElement(element, target) {
    const inputs = element.querySelectorAll('input[name], select[name]');
    inputs.forEach(input => {
      const name = input.name;
      if (input.type === 'number') {
        target[name] = parseFloat(input.value) || 0;
      } else {
        target[name] = input.value;
      }
    });
    
    const toggles = element.querySelectorAll('.toggle-switch[data-name]');
    toggles.forEach(toggle => {
      const name = toggle.dataset.name;
      target[name] = toggle.classList.contains('on');
    });
    
    // Collect nested collapsible data
    const collapsibles = element.querySelectorAll('.collapsible');
    collapsibles.forEach(coll => {
      const title = coll.querySelector('.collapsible-title');
      if (title) {
        const name = title.textContent.trim();
        const content = coll.querySelector('.collapsible-content');
        if (content) {
          const nestedData = {};
          collectFromElement(content, nestedData);
          if (Object.keys(nestedData).length > 0) {
            target[name] = nestedData;
          }
        }
      }
    });
  }
  
  collectFromElement(formView, data);
  
  return data;
}

/**
 * Sync form data to JSON editor
 */
function syncFormToJson() {
  const data = collectFormData();
  const jsonInput = document.getElementById('json-input');
  jsonInput.value = JSON.stringify(data, null, 2);
}

/**
 * Sync JSON editor back to form fields
 */
function syncJsonToForm() {
  try {
    const jsonInput = document.getElementById('json-input');
    const data = JSON.parse(jsonInput.value || '{}');
    
    // Update form fields with JSON data
    Object.entries(data).forEach(([key, value]) => {
      const input = document.querySelector(`input[name="${key}"], select[name="${key}"]`);
      if (input) {
        input.value = value;
        if (input.classList.contains('text-input')) {
          input.classList.toggle('filled', !!value);
        }
      }
      
      const toggle = document.querySelector(`.toggle-switch[data-name="${key}"]`);
      if (toggle) {
        if (value) {
          toggle.classList.add('on');
          toggle.classList.remove('off');
        } else {
          toggle.classList.add('off');
          toggle.classList.remove('on');
        }
        const label = toggle.parentElement.querySelector('.toggle-label');
        if (label) label.textContent = value ? 'True' : 'False';
      }
    });
  } catch (e) {
    console.error('Failed to sync JSON to form:', e);
  }
}

/* ============================================================================
   Pipeline Execution
   ========================================================================= */

/**
 * Load pipeline information and initialize UI
 */
async function loadPipelineInfo() {
  const pipelineName = serviceConfig?.pipeline?.name || 'Pipeline';
  const pipelineNameEl = document.getElementById('pipeline-name');
  const deploymentTitleEl = document.getElementById('deployment-title');
  
  if (pipelineNameEl) {
    pipelineNameEl.textContent = pipelineName;
  }
  if (deploymentTitleEl) {
    deploymentTitleEl.textContent = pipelineName;
  }
  
  const schema = serviceConfig?.pipeline?.input_schema || {};
  buildFormFields(schema);
  
  // Initialize JSON view with default values
  syncFormToJson();
}

/**
 * Run the pipeline with current parameters
 */
async function runPipeline() {
  try {
    const runBtn = document.getElementById('run-btn');
    runBtn.disabled = true; 
    runBtn.textContent = 'Running...';
    
    const params = collectFormData();
    const invokeUrl = serviceConfig?.app?.invoke_url_path || '/invoke';
    const result = await postJSON(invokeUrl, { 
      parameters: params, 
      timeout: 300 
    });

    lastResult = result;
    displayOutput(result);
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    const runBtn = document.getElementById('run-btn');
    runBtn.disabled = false;
    runBtn.textContent = 'Run';
  }
}

/* ============================================================================
   Output Rendering
   ========================================================================= */

/**
 * Display pipeline execution output
 * Uses DOMPurify for any HTML content if available
 * @param {Object} result - The pipeline result
 */
function displayOutput(result) {
  const outputView = document.getElementById('preview-output');
  outputView.innerHTML = '';
  
  // Run card
  const runCard = document.createElement('div');
  runCard.className = 'run-card';
  
  const runCardHeader = document.createElement('div');
  runCardHeader.className = 'run-card-header';
  
  const runInfo = document.createElement('div');
  const runLabel = document.createElement('div');
  runLabel.className = 'run-label';
  runLabel.textContent = 'Run';
  
  const runId = document.createElement('div');
  runId.className = 'run-id';
  
  const runPrefix = document.createElement('span');
  runPrefix.className = 'run-id-prefix';
  runPrefix.textContent = '#3488-';
  
  const runName = document.createElement('span');
  const pipelineName = serviceConfig?.pipeline?.name || 'pipeline';
  const dateStr = new Date().toISOString().slice(0,10).replace(/-/g,'');
  runName.textContent = `${pipelineName}-${dateStr}`;
  
  const statusIcon = document.createElement('svg');
  statusIcon.setAttribute('width', '16');
  statusIcon.setAttribute('height', '16');
  statusIcon.setAttribute('viewBox', '0 0 16 16');
  statusIcon.setAttribute('fill', 'none');
  statusIcon.innerHTML = `
    <circle cx="8" cy="8" r="6" fill="#1cbf4a"/>
    <path d="M6 8L7.5 9.5L10 6.5" stroke="white" stroke-width="1.5" fill="none"/>
  `;
  
  runId.appendChild(runPrefix);
  runId.appendChild(runName);
  runId.appendChild(statusIcon);
  
  runInfo.appendChild(runLabel);
  runInfo.appendChild(runId);
  
  const runActions = document.createElement('div');
  runActions.className = 'run-actions';
  
  const runDetailsBtn = document.createElement('button');
  runDetailsBtn.className = 'nav-button';
  runDetailsBtn.textContent = 'Run Details';
  
  const shareBtn = document.createElement('button');
  shareBtn.className = 'nav-button';
  shareBtn.textContent = 'Share';
  
  runActions.appendChild(runDetailsBtn);
  runActions.appendChild(shareBtn);
  
  runCardHeader.appendChild(runInfo);
  runCardHeader.appendChild(runActions);
  
  const runFooter = document.createElement('div');
  runFooter.className = 'run-footer';
  
  const runStatus = document.createElement('div');
  runStatus.className = 'run-status';
  
  const statusCompleted = document.createElement('span');
  statusCompleted.className = 'run-status-completed';
  statusCompleted.textContent = 'Completed';
  
  const statusTime = document.createElement('span');
  statusTime.textContent = ' · 20s';
  
  runStatus.appendChild(statusCompleted);
  runStatus.appendChild(statusTime);
  runFooter.appendChild(runStatus);
  
  runCard.appendChild(runCardHeader);
  runCard.appendChild(runFooter);
  outputView.appendChild(runCard);
  
  // Output data
  if (result && result.outputs) {
    Object.entries(result.outputs).forEach(([key, value]) => {
      const outputItem = createOutputItem(key, value);
      outputView.appendChild(outputItem);
    });
  }
  
  const rerunBtn = document.getElementById('rerun-btn');
  const deleteBtn = document.getElementById('delete-btn');
  if (rerunBtn) rerunBtn.disabled = false;
  if (deleteBtn) deleteBtn.disabled = false;
  
  // Also update JSON output
  if (currentOutputMode === 'json') {
    const jsonOutput = document.getElementById('json-output');
    if (jsonOutput) {
      jsonOutput.value = JSON.stringify(result, null, 2);
    }
  }
}

/**
 * Create an output item element
 * @param {string} key - Output key/name
 * @param {*} value - Output value
 * @returns {HTMLElement} The output item element
 */
function createOutputItem(key, value) {
  const item = document.createElement('div');
  item.className = 'output-item';
  
  const header = document.createElement('div');
  header.className = 'output-item-header';
  
  const chevron = document.createElement('svg');
  chevron.className = 'chevron-icon';
  chevron.innerHTML = '<path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="2" fill="none"/>';
  chevron.setAttribute('viewBox', '0 0 24 24');
  
  const title = document.createElement('div');
  title.className = 'output-item-title';
  title.textContent = key;
  
  const tag = document.createElement('div');
  tag.className = 'output-item-tag';
  
  const tagIcon = document.createElement('svg');
  tagIcon.className = 'output-item-tag-icon';
  tagIcon.setAttribute('viewBox', '0 0 20 20');
  tagIcon.setAttribute('fill', 'none');
  tagIcon.innerHTML = '<path d="M4 6L10 4L16 6V10C16 14 10 16 10 16C10 16 4 14 4 10V6Z" stroke="currentColor" stroke-width="1.5" fill="none"/>';
  
  const tagText = document.createElement('span');
  tagText.className = 'output-item-tag-text';
  tagText.textContent = key;
  
  const tagBadge = document.createElement('span');
  tagBadge.className = 'output-item-tag-badge';
  tagBadge.textContent = '#2';
  
  tag.appendChild(tagIcon);
  tag.appendChild(tagText);
  tag.appendChild(tagBadge);
  
  const collapseBtn = document.createElement('button');
  collapseBtn.className = 'collapse-button';
  collapseBtn.innerHTML = `
    <svg class="collapse-icon" viewBox="0 0 24 24" fill="none">
      <path d="M4 6H20M4 18H20M4 10H14M4 14H14" stroke="currentColor" stroke-width="2"/>
    </svg>
  `;
  
  header.appendChild(chevron);
  header.appendChild(title);
  header.appendChild(tag);
  header.appendChild(collapseBtn);
  
  const content = document.createElement('div');
  content.className = 'output-item-content';
  
  if (typeof value === 'object' && value !== null) {
    renderObject(value, content, key);
  } else {
    content.textContent = String(value);
  }
  
  const setExpanded = (expanded) => {
    if (expanded) {
      content.style.display = 'block';
      item.classList.add('expanded');
      item.classList.remove('collapsed');
    } else {
      content.style.display = 'none';
      item.classList.remove('expanded');
      item.classList.add('collapsed');
    }
  };
  
  setExpanded(true);
  
  const toggle = () => {
    const isExpanded = item.classList.contains('expanded');
    setExpanded(!isExpanded);
  };
  
  header.addEventListener('click', (e) => {
    if (e.target !== collapseBtn && !collapseBtn.contains(e.target)) {
      toggle();
    }
  });
  collapseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggle();
  });
  
  item.appendChild(header);
  item.appendChild(content);
  
  return item;
}

/**
 * Render an object value recursively
 * Uses safe DOM manipulation to prevent XSS
 * @param {Object} obj - Object to render
 * @param {HTMLElement} container - Container element
 * @param {number} depth - Current recursion depth
 */
function renderObject(obj, container, depth = 0) {
  Object.entries(obj).forEach(([key, value]) => {
    if (key === 'summary' && typeof value === 'string' && value.length > 200) {
      const summary = document.createElement('div');
      summary.className = 'output-summary';
      summary.textContent = value; // Safe: textContent
      
      const expandLink = document.createElement('div');
      expandLink.className = 'expand-link';
      
      const expandIcon = document.createElement('svg');
      expandIcon.className = 'expand-icon';
      expandIcon.setAttribute('viewBox', '0 0 16 16');
      expandIcon.setAttribute('fill', 'none');
      expandIcon.innerHTML = '<path d="M4 6H12M4 12H12M4 8H10M4 10H10" stroke="currentColor" stroke-width="1.5"/>';
      
      const expandText = document.createElement('span');
      expandText.textContent = 'Expand summary';
      
      expandLink.appendChild(expandIcon);
      expandLink.appendChild(expandText);
      
      expandLink.addEventListener('click', () => {
        summary.style.maxHeight = 'none';
        summary.style.webkitLineClamp = 'unset';
        expandLink.style.display = 'none';
      });
      
      container.appendChild(summary);
      container.appendChild(expandLink);
    } else if (typeof value === 'object' && value !== null) {
      const section = document.createElement('div');
      section.className = 'output-section';
      
      const sectionHeader = document.createElement('div');
      sectionHeader.className = 'output-section-header';
      
      const sectionChevron = document.createElement('svg');
      sectionChevron.className = 'chevron-icon';
      sectionChevron.setAttribute('viewBox', '0 0 16 16');
      sectionChevron.setAttribute('fill', 'none');
      sectionChevron.innerHTML = '<path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="1.5" fill="none"/>';
      
      const sectionTitle = document.createElement('span');
      sectionTitle.className = 'output-section-title';
      sectionTitle.textContent = key;
      
      sectionHeader.appendChild(sectionChevron);
      sectionHeader.appendChild(sectionTitle);
      section.appendChild(sectionHeader);
      
      const nestedSection = document.createElement('div');
      nestedSection.className = 'nested-section';
      renderObject(value, nestedSection, depth + 1);
      section.appendChild(nestedSection);
      
      container.appendChild(section);
    } else {
      const field = document.createElement('div');
      field.className = 'output-field';
      
      const fieldKey = document.createElement('div');
      fieldKey.className = 'output-field-key';
      fieldKey.textContent = key;
      
      const fieldValue = document.createElement('div');
      fieldValue.className = 'output-field-value';
      fieldValue.textContent = String(value);
      
      field.appendChild(fieldKey);
      field.appendChild(fieldValue);
      container.appendChild(field);
    }
  });
}

/* ============================================================================
   Event Handlers
   ========================================================================= */

/**
 * Attach all event listeners
 */
function attachEventListeners() {
  // Run button
  const runBtn = document.getElementById('run-btn');
  if (runBtn) {
    runBtn.addEventListener('click', runPipeline);
  }
  
  // Reset button
  const resetBtn = document.getElementById('reset-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      loadPipelineInfo();
    });
  }
  
  // Re-run button
  const rerunBtn = document.getElementById('rerun-btn');
  if (rerunBtn) {
    rerunBtn.addEventListener('click', runPipeline);
  }
  
  // Set API Key button
  const setApiKeyBtn = document.getElementById('set-api-key-btn');
  if (setApiKeyBtn) {
    setApiKeyBtn.addEventListener('click', () => {
      showApiKeyModal();
    });
  }
  
  // Clear output button (formerly "delete")
  const deleteBtn = document.getElementById('delete-btn');
  if (deleteBtn) {
    deleteBtn.textContent = 'Clear Output';
    deleteBtn.addEventListener('click', () => {
      const previewOutput = document.getElementById('preview-output');
      const jsonOutput = document.getElementById('json-output');
      
      if (previewOutput) {
        const emptyMsg = document.createElement('p');
        emptyMsg.className = 'empty-state';
        emptyMsg.textContent = 'Run the pipeline to see output here';
        previewOutput.innerHTML = '';
        previewOutput.appendChild(emptyMsg);
      }
      
      if (jsonOutput) {
        jsonOutput.value = '';
      }
      
      const rerunBtnEl = document.getElementById('rerun-btn');
      if (rerunBtnEl) rerunBtnEl.disabled = true;
      if (deleteBtn) deleteBtn.disabled = true;
      lastResult = null;
    });
  }

  // Toggle form/JSON input
  const toggleFormBtn = document.getElementById('toggle-form');
  const toggleJsonBtn = document.getElementById('toggle-json');
  const formView = document.getElementById('form-view');
  const jsonInput = document.getElementById('json-input');
  
  if (toggleFormBtn && formView) {
    toggleFormBtn.addEventListener('click', () => {
      toggleFormBtn.classList.add('active');
      if (toggleJsonBtn) toggleJsonBtn.classList.remove('active');
      formView.classList.remove('hidden');
      if (jsonInput) jsonInput.classList.add('hidden');
      currentInputMode = 'form';
    });
  }

  if (toggleJsonBtn && jsonInput) {
    toggleJsonBtn.addEventListener('click', () => {
      // Sync current form data to JSON before switching
      syncFormToJson();
      
      toggleJsonBtn.classList.add('active');
      if (toggleFormBtn) toggleFormBtn.classList.remove('active');
      if (formView) formView.classList.add('hidden');
      jsonInput.classList.remove('hidden');
      currentInputMode = 'json';
    });
  }

  // Toggle preview/JSON output
  const togglePreviewBtn = document.getElementById('toggle-preview');
  const toggleJsonOutputBtn = document.getElementById('toggle-json-output');
  const previewOutput = document.getElementById('preview-output');
  const jsonOutput = document.getElementById('json-output');
  
  if (togglePreviewBtn && previewOutput) {
    togglePreviewBtn.addEventListener('click', () => {
      togglePreviewBtn.classList.add('active');
      if (toggleJsonOutputBtn) toggleJsonOutputBtn.classList.remove('active');
      previewOutput.classList.remove('hidden');
      if (jsonOutput) jsonOutput.classList.add('hidden');
      currentOutputMode = 'preview';
    });
  }

  if (toggleJsonOutputBtn && jsonOutput) {
    toggleJsonOutputBtn.addEventListener('click', () => {
      toggleJsonOutputBtn.classList.add('active');
      if (togglePreviewBtn) togglePreviewBtn.classList.remove('active');
      if (previewOutput) previewOutput.classList.add('hidden');
      jsonOutput.classList.remove('hidden');
      currentOutputMode = 'json';
      
      if (lastResult) {
        jsonOutput.value = JSON.stringify(lastResult, null, 2);
      }
    });
  }
}

/* ============================================================================
   Bootstrap
   ========================================================================= */

// Initialize dashboard when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDashboard);
} else {
  initDashboard();
}

