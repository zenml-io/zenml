// Document Analysis Service - Frontend JavaScript

console.log('JavaScript file loaded successfully');

const form = document.getElementById('analysisForm');
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const contentTextarea = document.getElementById('content');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileType = document.getElementById('fileType');
const fileSize = document.getElementById('fileSize');
const results = document.getElementById('results');
const loadingState = document.getElementById('loadingState');
const analysisResults = document.getElementById('analysisResults');
const analyzeBtn = document.getElementById('analyzeBtn');

let currentFileData = null;

// Click to upload
uploadArea.addEventListener('click', () => {
  console.log('Upload area clicked');
  fileInput.click();
});

// File input change
fileInput.addEventListener('change', handleFileSelect);

function handleFileSelect(e) {
  const files = e.target.files;
  if (files.length > 0) {
    processFile(files[0]);
  }
}

// Drag and drop functionality
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
  uploadArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
  uploadArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
  uploadArea.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
  uploadArea.classList.add('dragover');
}

function unhighlight(e) {
  uploadArea.classList.remove('dragover');
}

uploadArea.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;
  
  if (files.length > 0) {
    processFile(files[0]);
  }
}

async function processFile(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    showMessage('📤 Uploading file...', 'info');
    
    const response = await fetch('/upload', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // Update UI with file info
    fileName.textContent = data.filename;
    fileType.textContent = data.document_type.charAt(0).toUpperCase() + data.document_type.slice(1);
    fileSize.textContent = formatFileSize(data.size);
    fileInfo.style.display = 'block';
    
    // Set content
    contentTextarea.value = data.content;
    
    // Store file data for analysis
    currentFileData = {
      filename: data.filename,
      document_type: data.document_type,
      content: data.content
    };
    
    showMessage('✅ File uploaded successfully!', 'success');
    
  } catch (error) {
    showError('Upload failed: ' + error.message);
  }
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showMessage(text, type) {
  const div = document.createElement('div');
  div.className = type === 'success' ? 'success' : type === 'info' ? 'info' : 'error';
  div.textContent = text;
  div.style.cssText = `
    padding: 12px; 
    border-radius: 6px; 
    margin: 12px 0;
    ${type === 'success' ? 'background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534;' : 
      type === 'info' ? 'background: #eff6ff; border: 1px solid #dbeafe; color: #1e40af;' : 
      'background: #fef2f2; border: 1px solid #fecaca; color: #dc2626;'}
  `;
  uploadArea.parentNode.insertBefore(div, uploadArea.nextSibling);
  setTimeout(() => div.remove(), 3000);
}

form.addEventListener('submit', async function(e) {
  e.preventDefault();
  console.log('Form submitted');
  
  const content = contentTextarea.value.trim();
  if (!content) {
    showError('Please provide document content');
    return;
  }
  
  const data = {
    content: content,
    filename: currentFileData?.filename,
    document_type: currentFileData?.document_type,
    analysis_type: 'full'
  };
  
  analyzeBtn.disabled = true;
  results.classList.add('show');
  loadingState.style.display = 'block';
  analysisResults.style.display = 'none';
  
  try {
    const response = await fetch('/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.error) {
      showError(result.error);
      return;
    }
    
    // Now we have a run_id, poll for results
    if (result.run_id) {
      pollForResults(result.run_id);
    } else {
      showError('No run ID received from server');
    }
  } catch (error) {
    showError('Network error: ' + error.message);
    analyzeBtn.disabled = false;
    loadingState.style.display = 'none';
  }
});

async function pollForResults(runId) {
  const maxPolls = 60; // Poll for up to 2 minutes
  let polls = 0;
  
  const poll = async () => {
    try {
      const response = await fetch(`/result/${runId}`);
      const result = await response.json();
      
      if (response.status === 202) {
        // Still running, continue polling
        polls++;
        if (polls < maxPolls) {
          setTimeout(poll, 2000); // Poll every 2 seconds
        } else {
          showError('Analysis timed out');
          analyzeBtn.disabled = false;
          loadingState.style.display = 'none';
        }
      } else if (response.status === 200) {
        // Completed successfully
        showResults(result);
        analyzeBtn.disabled = false;
        loadingState.style.display = 'none';
      } else {
        // Error occurred
        showError(result.error || 'Analysis failed');
        analyzeBtn.disabled = false;
        loadingState.style.display = 'none';
      }
    } catch (error) {
      showError('Error checking results: ' + error.message);
      analyzeBtn.disabled = false;
      loadingState.style.display = 'none';
    }
  };
  
  // Start polling
  poll();
}

function showResults(data) {
  // Safely set text content with fallbacks
  document.getElementById('summaryText').textContent = data.summary || 'No summary available';
  document.getElementById('wordCount').textContent = data.word_count || '0';
  
  // Handle sentiment with safety checks
  const sentiment = data.sentiment || 'unknown';
  document.getElementById('sentiment').textContent = sentiment.charAt(0).toUpperCase() + sentiment.slice(1);
  
  // Handle readability score
  const readabilityScore = data.readability_score || 0;
  document.getElementById('readability').textContent = readabilityScore.toFixed(2);
  
  // Handle keywords array
  const keywords = data.keywords || [];
  document.getElementById('keywords').textContent = keywords.join(', ') || 'No keywords available';
  
  analysisResults.style.display = 'block';
}

function showError(message) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'error';
  errorDiv.textContent = 'Error: ' + message;
  results.appendChild(errorDiv);
  setTimeout(() => errorDiv.remove(), 5000);
}