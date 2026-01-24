/**
 * OBS Overlay Control Panel JavaScript - COMPLETE VERSION
 * Includes Position & Size Controls + All Original Functionality
 */

// ============================================================================
// GLOBAL STATE
// ============================================================================
let currentPhrasesCategory = null;
let currentPhrases = [];

// ============================================================================
// FLASH MESSAGE AUTO-HIDE
// ============================================================================
setTimeout(() => {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        msg.style.transition = 'opacity 0.5s';
        msg.style.opacity = '0';
        setTimeout(() => msg.remove(), 500);
    });
}, 5000);

// ============================================================================
// UPLOAD PROGRESS FUNCTIONS
// ============================================================================
function showUploadProgress() {
    document.getElementById('uploadModal').classList.remove('hidden');
    document.getElementById('uploadProgress').style.width = '0%';
    document.getElementById('uploadStatus').textContent = 'Preparing upload...';
}

function updateUploadProgress(percent, status) {
    document.getElementById('uploadProgress').style.width = percent + '%';
    document.getElementById('uploadStatus').textContent = status;
}

function hideUploadProgress() {
    setTimeout(() => {
        document.getElementById('uploadModal').classList.add('hidden');
    }, 500);
}

// ============================================================================
// CATEGORY TAB SWITCHING
// ============================================================================
function switchCategory(category) {
    // Hide all category content
    document.querySelectorAll('.category-content').forEach(el => el.classList.add('hidden'));

    // Remove active state from all tabs
    document.querySelectorAll('.category-tab').forEach(el => {
        el.classList.remove('border-blue-500', 'text-blue-600');
        el.classList.add('border-transparent', 'text-gray-500');
    });

    // Show selected category content
    document.getElementById(`content-${category}`).classList.remove('hidden');

    // Add active state to selected tab
    const activeTab = document.getElementById(`tab-${category}`);
    activeTab.classList.remove('border-transparent', 'text-gray-500');
    activeTab.classList.add('border-blue-500', 'text-blue-600');

    // Save to localStorage
    localStorage.setItem('activeCategory', category);
}

// ============================================================================
// SETTINGS UPDATE FUNCTION
// ============================================================================
function updateSetting(category, field, value) {
    const formData = new FormData();
    formData.append(field, value);

    fetch(`/api/settings/${category}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Setting updated:', field, value);

            // Update color preview text boxes
            if (field.includes('color')) {
                const colorInput = document.getElementById(`${field}-${category}`);
                const textInput = colorInput.nextElementSibling;
                if (textInput && textInput.tagName === 'INPUT') {
                    textInput.value = value;
                }
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

// ============================================================================
// IMAGE UPLOAD FUNCTION
// ============================================================================
function uploadImage(category, type, input) {
    const file = input.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Please select a valid image file');
        input.value = '';
        return;
    }

    // Validate file size (16MB max)
    if (file.size > 16 * 1024 * 1024) {
        alert('File size must be less than 16MB');
        input.value = '';
        return;
    }

    showUploadProgress();
    updateUploadProgress(10, 'Validating file...');

    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();

    // Track upload progress
    xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 80) + 10; // 10-90%
            updateUploadProgress(percentComplete, `Uploading ${file.name}...`);
        }
    });

    xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
            updateUploadProgress(95, 'Processing...');
            const data = JSON.parse(xhr.responseText);

            if (data.success) {
                updateUploadProgress(100, 'Upload complete!');
                setTimeout(() => {
                    hideUploadProgress();
                    localStorage.setItem('activeCategory', category);
                    location.reload();
                }, 500);
            } else {
                hideUploadProgress();
                alert('Upload failed: ' + (data.error || 'Unknown error'));
                input.value = '';
            }
        } else {
            hideUploadProgress();
            alert('Upload failed. Please try again.');
            input.value = '';
        }
    });

    xhr.addEventListener('error', () => {
        hideUploadProgress();
        alert('Network error. Please check your connection and try again.');
        input.value = '';
    });

    xhr.open('POST', `/api/upload/${category}/${type}`);
    xhr.send(formData);
}

// ============================================================================
// LOGO REMOVAL FUNCTION
// ============================================================================
function removeLogo(category) {
    if (!confirm('Are you sure you want to remove the logo? This will delete the logo file path from the system.')) {
        return;
    }

    fetch(`/api/remove-logo/${category}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            localStorage.setItem('activeCategory', category);
            location.reload();
        } else {
            alert('Error removing logo. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error removing logo. Please try again.');
    });
}

// ============================================================================
// VISIBILITY TOGGLE
// ============================================================================
function toggleVisibility(category) {
    const button = document.getElementById(`visibility-${category}`);
    const isVisible = button.classList.contains('bg-green-500');

    fetch(`/api/visibility/${category}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({visible: !isVisible})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const span = button.querySelector('span');
            if (data.visible) {
                button.classList.remove('bg-gray-300');
                button.classList.add('bg-green-500');
                span.classList.remove('translate-x-1');
                span.classList.add('translate-x-6');
            } else {
                button.classList.remove('bg-green-500');
                button.classList.add('bg-gray-300');
                span.classList.remove('translate-x-6');
                span.classList.add('translate-x-1');
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

// ============================================================================
// PHRASES EDITOR FUNCTIONS
// ============================================================================
function openPhrasesEditor(category) {
    currentPhrasesCategory = category;

    fetch(`/api/secondary-phrases/${category}`)
        .then(response => response.json())
        .then(data => {
            currentPhrases = data.phrases || [];
            if (currentPhrases.length === 0) {
                currentPhrases = ['New phrase...'];
            }
            renderPhrasesList();
            document.getElementById('phrasesModal').classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error loading phrases:', error);
            currentPhrases = ['New phrase...'];
            renderPhrasesList();
            document.getElementById('phrasesModal').classList.remove('hidden');
        });
}

function closePhrasesModal() {
    document.getElementById('phrasesModal').classList.add('hidden');
    currentPhrasesCategory = null;
    currentPhrases = [];
}

function renderPhrasesList() {
    const container = document.getElementById('phrasesList');
    container.innerHTML = '';

    if (currentPhrases.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-center py-4">No phrases yet. Click "Add New Phrase" to start.</p>';
        return;
    }

    currentPhrases.forEach((phrase, index) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-2 mb-2';
        div.innerHTML = `
            <span class="text-gray-600 font-mono text-sm w-8">${index + 1}.</span>
            <input type="text" value="${escapeHtml(phrase)}"
                   onchange="updatePhraseText(${index}, this.value)"
                   class="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                   placeholder="Enter phrase text...">
            <button onclick="movePhraseUp(${index})" ${index === 0 ? 'disabled' : ''}
                    class="p-2 text-gray-600 hover:text-blue-600 disabled:opacity-30 disabled:cursor-not-allowed" title="Move up">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
                </svg>
            </button>
            <button onclick="movePhraseDown(${index})" ${index === currentPhrases.length - 1 ? 'disabled' : ''}
                    class="p-2 text-gray-600 hover:text-blue-600 disabled:opacity-30 disabled:cursor-not-allowed" title="Move down">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                </svg>
            </button>
            <button onclick="deletePhrase(${index})" class="p-2 text-red-600 hover:text-red-800" title="Delete">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
            </button>
        `;
        container.appendChild(div);
    });
}

function addNewPhrase() {
    currentPhrases.push('New phrase...');
    renderPhrasesList();
}

function updatePhraseText(index, newText) {
    currentPhrases[index] = newText;
}

function movePhraseUp(index) {
    if (index > 0) {
        [currentPhrases[index], currentPhrases[index - 1]] = [currentPhrases[index - 1], currentPhrases[index]];
        renderPhrasesList();
    }
}

function movePhraseDown(index) {
    if (index < currentPhrases.length - 1) {
        [currentPhrases[index], currentPhrases[index + 1]] = [currentPhrases[index + 1], currentPhrases[index]];
        renderPhrasesList();
    }
}

function deletePhrase(index) {
    if (currentPhrases.length === 1) {
        alert('You must have at least one phrase. Edit this phrase instead of deleting it.');
        return;
    }

    if (confirm('Delete this phrase?')) {
        currentPhrases.splice(index, 1);
        renderPhrasesList();
    }
}

function savePhrases() {
    const filteredPhrases = currentPhrases.filter(p => p.trim() !== '');

    if (filteredPhrases.length === 0) {
        alert('Please add at least one phrase with text.');
        return;
    }

    fetch(`/api/secondary-phrases/${currentPhrasesCategory}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({phrases: filteredPhrases})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById(`phrase-preview-${currentPhrasesCategory}`).textContent =
                `${filteredPhrases.length} phrase${filteredPhrases.length !== 1 ? 's' : ''} configured`;
            closePhrasesModal();
        } else {
            alert('Error saving phrases. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error saving phrases. Please try again.');
    });
}

// ============================================================================
// POSITION & SIZE CONTROL HELPERS - NEW FUNCTIONS
// ============================================================================
function setupPositionSizeControls() {
    // Vertical position dropdowns
    document.querySelectorAll('[id^="vertical_position-"]').forEach(select => {
        select.addEventListener('change', function() {
            const cat = this.id.split('-')[1];
            const customDiv = document.getElementById(`custom-vertical-${cat}`);
            if (customDiv) {
                customDiv.classList.toggle('hidden', this.value !== 'custom');
            }
        });
    });

    // Horizontal position dropdowns
    document.querySelectorAll('[id^="horizontal_position-"]').forEach(select => {
        select.addEventListener('change', function() {
            const cat = this.id.split('-')[1];
            const customDiv = document.getElementById(`custom-horizontal-${cat}`);
            if (customDiv) {
                customDiv.classList.toggle('hidden', this.value !== 'custom');
            }
        });
    });

    // Container width dropdowns
    document.querySelectorAll('[id^="container_width-"]').forEach(select => {
        select.addEventListener('change', function() {
            const cat = this.id.split('-')[1];
            const customDiv = document.getElementById(`custom-width-${cat}`);
            if (customDiv) {
                customDiv.classList.toggle('hidden', this.value !== 'custom');
            }
        });
    });

    // Container height dropdowns
    document.querySelectorAll('[id^="container_height-"]').forEach(select => {
        select.addEventListener('change', function() {
            const cat = this.id.split('-')[1];
            const customDiv = document.getElementById(`custom-height-${cat}`);
            if (customDiv) {
                customDiv.classList.toggle('hidden', this.value !== 'custom');
            }
        });
    });
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
    // Restore active category from localStorage
    const savedCategory = localStorage.getItem('activeCategory');
    if (savedCategory) {
        switchCategory(savedCategory);
    }

    // Setup position and size control listeners
    setupPositionSizeControls();

    // Close modal on outside click
    const phrasesModal = document.getElementById('phrasesModal');
    if (phrasesModal) {
        phrasesModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closePhrasesModal();
            }
        });
    }

    // Initialize color picker listeners to update text boxes
    document.querySelectorAll('input[type="color"]').forEach(colorInput => {
        colorInput.addEventListener('change', function() {
            const textInput = this.nextElementSibling;
            if (textInput && textInput.tagName === 'INPUT') {
                textInput.value = this.value;
            }
        });
    });

    console.log('Control panel initialized with position & size controls');
});