// Global state
let currentCategory = 'funeral';
let currentPhrases = [];

// Switch between category tabs
function switchCategory(category) {
    currentCategory = category;

    // Update tabs
    document.querySelectorAll('.category-tab').forEach(tab => {
        tab.classList.remove('border-indigo-500', 'text-indigo-600');
        tab.classList.add('border-transparent', 'text-gray-500');
    });
    document.getElementById(`tab-${category}`).classList.remove('border-transparent', 'text-gray-500');
    document.getElementById(`tab-${category}`).classList.add('border-indigo-500', 'text-indigo-600');

    // Update content
    document.querySelectorAll('.category-content').forEach(content => {
        content.classList.add('hidden');
    });
    document.getElementById(`category-${category}`).classList.remove('hidden');
}

// Toggle accordion sections
function toggleAccordion(id) {
    const content = document.getElementById(`content-${id}`);
    const icon = document.getElementById(`icon-${id}`);

    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        icon.style.transform = 'rotate(180deg)';
    } else {
        content.classList.add('hidden');
        icon.style.transform = 'rotate(0deg)';
    }
}

// Gather all settings from all forms and accordions for a category
function getAllSettings(category) {
    const formData = new FormData();
    const categoryContent = document.getElementById(`category-${category}`);

    // Get all inputs, selects, and textareas from the entire category content
    categoryContent.querySelectorAll('input, select, textarea').forEach(input => {
        if (input.name) {
            if (input.type === 'checkbox') {
                formData.set(input.name, input.checked ? 'true' : 'false');
            } else if (input.type === 'file') {
                // Skip file inputs
                return;
            } else {
                formData.set(input.name, input.value);
            }
        }
    });

    return formData;
}

// Save settings
async function saveSettings(event, category) {
    if (event) {
        event.preventDefault();
    }

    // Gather all settings from the entire category (form + accordion sections)
    const formData = getAllSettings(category);

    try {
        const response = await fetch(`/api/settings/${category}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            showToast('Settings saved successfully!', 'success');
            // Refresh preview with a slight delay to ensure DB is updated
            setTimeout(() => refreshPreview(category), 100);
        } else {
            showToast('Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showToast('Error saving settings', 'error');
    }
}

// Auto-save for any input change
async function autoSaveSettings(category) {
    const formData = getAllSettings(category);

    try {
        const response = await fetch(`/api/settings/${category}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            // Refresh preview with a slight delay to ensure DB is updated
            setTimeout(() => refreshPreview(category), 100);
        }
    } catch (error) {
        console.error('Error auto-saving settings:', error);
    }
}

// Toggle visibility
async function toggleVisibility(category) {
    const btn = document.getElementById(`visibility-btn-${category}`);
    const text = document.getElementById(`visibility-text-${category}`);
    const isVisible = btn.classList.contains('bg-green-500');

    try {
        const response = await fetch(`/api/visibility/${category}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ visible: !isVisible })
        });

        const data = await response.json();

        if (data.success) {
            if (data.visible) {
                btn.classList.remove('bg-red-500', 'hover:bg-red-600');
                btn.classList.add('bg-green-500', 'hover:bg-green-600');
                text.textContent = 'Visible';
                btn.querySelector('i').classList.remove('fa-eye-slash');
                btn.querySelector('i').classList.add('fa-eye');
            } else {
                btn.classList.remove('bg-green-500', 'hover:bg-green-600');
                btn.classList.add('bg-red-500', 'hover:bg-red-600');
                text.textContent = 'Hidden';
                btn.querySelector('i').classList.remove('fa-eye');
                btn.querySelector('i').classList.add('fa-eye-slash');
            }
            setTimeout(() => refreshPreview(category), 100);
            showToast(`Overlay ${data.visible ? 'shown' : 'hidden'}`, 'success');
        }
    } catch (error) {
        console.error('Error toggling visibility:', error);
        showToast('Error toggling visibility', 'error');
    }
}

// Reset settings
async function resetSettings(category) {
    if (!confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/settings/${category}/reset`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showToast('Settings reset to defaults', 'success');
            // Update all form fields with new values
            updateFormFields(category, data.settings);
            setTimeout(() => refreshPreview(category), 100);
        } else {
            showToast('Failed to reset settings', 'error');
        }
    } catch (error) {
        console.error('Error resetting settings:', error);
        showToast('Error resetting settings', 'error');
    }
}

// Update form fields with new settings
function updateFormFields(category, settings) {
    const categoryContent = document.getElementById(`category-${category}`);
    if (!categoryContent) return;

    // Update all inputs in the entire category content
    categoryContent.querySelectorAll('input, select, textarea').forEach(input => {
        const name = input.name;
        if (settings.hasOwnProperty(name)) {
            if (input.type === 'checkbox') {
                input.checked = settings[name];
            } else if (input.type === 'range') {
                input.value = settings[name];
                // Update the display value next to range inputs
                const displaySpan = input.nextElementSibling;
                if (displaySpan && displaySpan.tagName === 'SPAN') {
                    if (name.includes('opacity') || name.includes('duration') || name.includes('delay') || name.includes('speed')) {
                        displaySpan.textContent = settings[name];
                    } else {
                        displaySpan.textContent = settings[name] + 'px';
                    }
                }
            } else if (input.type !== 'file') {
                input.value = settings[name] || '';
            }
        }
    });
}

// Refresh preview - Force reload with timestamp to bypass cache
function refreshPreview(category) {
    const iframe = document.getElementById(`preview-${category}`);
    if (iframe) {
        const currentSrc = iframe.src.split('?')[0]; // Remove any existing query params
        const timestamp = new Date().getTime();

        // Use contentWindow.location for a harder reload
        try {
            iframe.contentWindow.location.href = `${currentSrc}?t=${timestamp}`;
        } catch (e) {
            // Fallback if cross-origin or other issue
            iframe.src = `${currentSrc}?t=${timestamp}`;
        }
    }
}

// Upload file
async function uploadFile(event, category, fileType) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    // Show loading toast
    showToast(`Uploading ${fileType}...`, 'info');

    try {
        const response = await fetch(`/api/upload/${category}/${fileType}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            showToast(`${fileType === 'logo' ? 'Logo' : 'Image'} uploaded successfully!`, 'success');
            // Update the image preview without reloading
            updateImagePreview(category, fileType, data.filename);
            setTimeout(() => refreshPreview(category), 100);
        } else {
            showToast('Failed to upload file', 'error');
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        showToast('Error uploading file', 'error');
    }
}

// Update image preview in the UI
function updateImagePreview(category, fileType, filename) {
    const categoryContent = document.getElementById(`category-${category}`);
    if (!categoryContent) return;

    const staticPath = `/static/${filename}`;

    if (fileType === 'logo') {
        // Find or create logo preview
        const logoSection = categoryContent.querySelector('[name="show_company_logo"]')?.closest('div')?.parentElement;
        if (logoSection) {
            let imageContainer = logoSection.querySelector('.relative');
            if (!imageContainer) {
                // Create new image container
                const uploadLabel = logoSection.querySelector('label');
                imageContainer = document.createElement('div');
                imageContainer.className = 'relative';
                imageContainer.innerHTML = `
                    <img src="${staticPath}" alt="Company Logo" 
                         class="h-20 w-20 object-contain border border-gray-300 rounded">
                    <button type="button" onclick="removeLogo('${category}')"
                            class="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600">
                        <i class="fas fa-times text-xs"></i>
                    </button>
                `;
                if (uploadLabel) {
                    uploadLabel.parentElement.insertBefore(imageContainer, uploadLabel);
                }
            } else {
                // Update existing image
                const img = imageContainer.querySelector('img');
                if (img) {
                    img.src = staticPath;
                }
                imageContainer.style.display = 'block';
            }
        }
    } else if (fileType === 'image') {
        // Find or create category image preview
        const imageSection = categoryContent.querySelector('[name="show_category_image"]')?.closest('div')?.parentElement;
        if (imageSection) {
            let imageContainer = imageSection.querySelector('.relative');
            if (!imageContainer) {
                // Create new image container
                const uploadLabel = imageSection.querySelector('label');
                imageContainer = document.createElement('div');
                imageContainer.className = 'relative';
                imageContainer.innerHTML = `
                    <img src="${staticPath}" alt="Category Image" 
                         class="h-20 w-32 object-cover border border-gray-300 rounded">
                    <button type="button" onclick="removeImage('${category}')"
                            class="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600">
                        <i class="fas fa-times text-xs"></i>
                    </button>
                `;
                if (uploadLabel) {
                    uploadLabel.parentElement.insertBefore(imageContainer, uploadLabel);
                }
            } else {
                // Update existing image
                const img = imageContainer.querySelector('img');
                if (img) {
                    img.src = staticPath;
                }
                imageContainer.style.display = 'block';
            }
        }
    }
}

// Remove logo
async function removeLogo(category) {
    if (!confirm('Are you sure you want to remove the logo?')) {
        return;
    }

    try {
        const response = await fetch(`/api/remove-logo/${category}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showToast('Logo removed', 'success');
            // Remove the logo preview from DOM
            const categoryContent = document.getElementById(`category-${category}`);
            if (categoryContent) {
                const containers = categoryContent.querySelectorAll('.relative');
                containers.forEach(container => {
                    const img = container.querySelector('img');
                    if (img && img.alt === 'Company Logo') {
                        container.style.display = 'none';
                    }
                });
                // Uncheck the "show logo" checkbox
                const showLogoCheckbox = categoryContent.querySelector('[name="show_company_logo"]');
                if (showLogoCheckbox) {
                    showLogoCheckbox.checked = false;
                }
            }
            setTimeout(() => refreshPreview(category), 100);
        } else {
            showToast('Failed to remove logo', 'error');
        }
    } catch (error) {
        console.error('Error removing logo:', error);
        showToast('Error removing logo', 'error');
    }
}

// Remove image
async function removeImage(category) {
    if (!confirm('Are you sure you want to remove the background image?')) {
        return;
    }

    try {
        const response = await fetch(`/api/remove-image/${category}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showToast('Image removed', 'success');
            // Remove the image preview from DOM
            const categoryContent = document.getElementById(`category-${category}`);
            if (categoryContent) {
                const containers = categoryContent.querySelectorAll('.relative');
                containers.forEach(container => {
                    const img = container.querySelector('img');
                    if (img && img.alt === 'Category Image') {
                        container.style.display = 'none';
                    }
                });
                // Uncheck the "show image" checkbox
                const showImageCheckbox = categoryContent.querySelector('[name="show_category_image"]');
                if (showImageCheckbox) {
                    showImageCheckbox.checked = false;
                }
            }
            setTimeout(() => refreshPreview(category), 100);
        } else {
            showToast(data.error || 'Failed to remove image', 'error');
        }
    } catch (error) {
        console.error('Error removing image:', error);
        showToast('Error removing image', 'error');
    }
}

// Phrases Modal Management
async function openPhrasesModal(category) {
    currentCategory = category;

    try {
        const response = await fetch(`/api/secondary-phrases/${category}`);
        const data = await response.json();
        currentPhrases = data.phrases || [];

        renderPhrasesList();
        document.getElementById('phrasesModal').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading phrases:', error);
        showToast('Error loading phrases', 'error');
    }
}

function closePhrasesModal() {
    document.getElementById('phrasesModal').classList.add('hidden');
}

function renderPhrasesList() {
    const container = document.getElementById('phrasesList');
    container.innerHTML = '';

    currentPhrases.forEach((phrase, index) => {
        const div = document.createElement('div');
        div.className = 'flex gap-2';
        div.innerHTML = `
            <input type="text" 
                   value="${phrase}" 
                   onchange="updatePhrase(${index}, this.value)"
                   class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                   placeholder="Enter phrase...">
            <button type="button" 
                    onclick="removePhrase(${index})"
                    class="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors">
                <i class="fas fa-trash"></i>
            </button>
        `;
        container.appendChild(div);
    });
}

function addPhraseInput() {
    currentPhrases.push('');
    renderPhrasesList();
}

function updatePhrase(index, value) {
    currentPhrases[index] = value;
}

function removePhrase(index) {
    currentPhrases.splice(index, 1);
    renderPhrasesList();
}

async function savePhrases() {
    // Filter out empty phrases
    const filteredPhrases = currentPhrases.filter(p => p.trim() !== '');

    try {
        const response = await fetch(`/api/secondary-phrases/${currentCategory}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ phrases: filteredPhrases })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Phrases saved successfully!', 'success');
            closePhrasesModal();
            setTimeout(() => refreshPreview(currentCategory), 100);
        } else {
            showToast('Failed to save phrases', 'error');
        }
    } catch (error) {
        console.error('Error saving phrases:', error);
        showToast('Error saving phrases', 'error');
    }
}

// Toast notification
function showToast(message, type = 'info') {
    const container = document.getElementById('flash-container');

    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500'
    };

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle',
        warning: 'fa-exclamation-triangle'
    };

    const toast = document.createElement('div');
    toast.className = `toast px-6 py-4 rounded-lg shadow-lg max-w-md ${colors[type]} text-white`;
    toast.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex items-center">
                <i class="fas ${icons[type]} mr-3"></i>
                <span>${message}</span>
            </div>
            <button onclick="this.parentElement.parentElement.classList.add('fade-out')" 
                    class="ml-4 text-white hover:text-gray-200">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Debounce function to prevent too many rapid saves
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Auto-save on input changes with debouncing
document.addEventListener('DOMContentLoaded', function() {
    // Add change listeners to all inputs for auto-save
    document.querySelectorAll('.category-content').forEach(content => {
        const category = content.id.replace('category-', '');
        const inputs = content.querySelectorAll('input:not([type="file"]), select, textarea');

        // Create debounced auto-save function for this category
        const debouncedAutoSave = debounce(() => autoSaveSettings(category), 500);

        inputs.forEach(input => {
            // For color inputs, range inputs, and checkboxes - auto-save immediately
            if (input.type === 'color' || input.type === 'checkbox' || input.type === 'range') {
                input.addEventListener('change', function() {
                    autoSaveSettings(category);
                });
            }
            // For text inputs and selects - debounce the auto-save
            else if (input.type === 'text' || input.tagName === 'SELECT' || input.tagName === 'TEXTAREA') {
                input.addEventListener('input', debouncedAutoSave);
                input.addEventListener('change', () => autoSaveSettings(category));
            }
        });
    });
});

// Close modal on escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closePhrasesModal();
    }
});

// Close modal on background click
document.getElementById('phrasesModal')?.addEventListener('click', function(event) {
    if (event.target === this) {
        closePhrasesModal();
    }
});