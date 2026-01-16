/**
 * Fixed Overlay Display Controller
 * Complete rewrite with immediate updates and proper state management
 * FIXED: Secondary phrases now use their own transition animations
 */

class OverlayController {
    constructor(category, settings) {
        this.category = category;
        this.settings = settings;
        this.lastTimestamp = null;
        this.pollInterval = null;
        this.rotationInterval = null;
        this.rotationTimeouts = [];
        this.typewriterTimeouts = [];
        this.currentPhraseIndex = 0;
        this.animationInitialized = false;

        // DOM element references
        this.container = document.getElementById('overlay-container');
        this.tickerText = document.getElementById('ticker-text');
        this.lowerThird = document.querySelector('.lower-third');
        this.categoryImage = document.getElementById('category-image');
        this.companyLogo = document.getElementById('company-logo');
        this.tickerContainer = document.querySelector('.ticker-container');
        this.mainTextEl = document.getElementById('main-text');
        this.secondaryContainer = document.getElementById('secondary-text-container');
        this.companyNameEl = document.getElementById('company-name');
        this.lowerThirdBg = document.querySelector('.lower-third-bg');
    }

    // Utility Functions
    decodeHTML(html) {
        const txt = document.createElement('textarea');
        txt.innerHTML = html;
        return txt.value;
    }

    clearTypewriterTimeouts() {
        this.typewriterTimeouts.forEach(timeout => clearTimeout(timeout));
        this.typewriterTimeouts = [];
    }

    clearRotationTimers() {
        if (this.rotationInterval) {
            clearInterval(this.rotationInterval);
            this.rotationInterval = null;
        }
        this.rotationTimeouts.forEach(timeout => clearTimeout(timeout));
        this.rotationTimeouts = [];
    }

    // Animation Functions
    applyEntranceAnimation() {
        if (this.settings.entrance_animation !== 'none') {
            this.lowerThird.style.animation = `${this.settings.entrance_animation} ${this.settings.entrance_duration}s ease-out ${this.settings.entrance_delay}s both`;
        }
    }

    typewriterEffect(elements) {
        this.clearTypewriterTimeouts();

        const baseDelay = (this.settings.entrance_delay + this.settings.entrance_duration) * 1000;
        let currentDelay = baseDelay;

        elements.forEach((item, index) => {
            const { element, text } = item;
            element.innerHTML = '';

            if (index === 0) {
                const cursor = document.createElement('span');
                cursor.className = 'typewriter-cursor';
                cursor.id = 'cursor-0';
                element.appendChild(cursor);
            }

            const chars = text.split('');
            chars.forEach((char, i) => {
                const timeout = setTimeout(() => {
                    const span = document.createElement('span');
                    span.textContent = char;

                    const cursor = document.getElementById(`cursor-${index}`);
                    if (cursor) {
                        element.insertBefore(span, cursor);
                    } else {
                        element.appendChild(span);
                    }

                    if (i === chars.length - 1) {
                        const oldCursor = document.getElementById(`cursor-${index}`);
                        if (oldCursor) oldCursor.remove();

                        if (index < elements.length - 1) {
                            setTimeout(() => {
                                const nextElement = elements[index + 1].element;
                                const newCursor = document.createElement('span');
                                newCursor.className = 'typewriter-cursor';
                                newCursor.id = `cursor-${index + 1}`;
                                nextElement.appendChild(newCursor);
                            }, 200);
                        }
                    }
                }, currentDelay + (i * this.settings.text_animation_speed * 1000));

                this.typewriterTimeouts.push(timeout);
            });

            currentDelay += chars.length * this.settings.text_animation_speed * 1000 + 300;
        });
    }

    fadeInWords(element, text) {
        element.innerHTML = '';
        const words = text.split(' ');
        words.forEach((word, i) => {
            const span = document.createElement('span');
            span.textContent = word + (i < words.length - 1 ? ' ' : '');
            span.style.opacity = '0';
            span.style.animation = 'fade-in 0.5s ease forwards';
            span.style.animationDelay = `${i * this.settings.text_animation_speed + this.settings.entrance_delay + this.settings.entrance_duration}s`;
            element.appendChild(span);
        });
    }

    slideInChars(element, text) {
        element.innerHTML = '';
        const chars = text.split('');
        chars.forEach((char, i) => {
            const span = document.createElement('span');
            span.textContent = char;
            span.style.display = 'inline-block';
            span.style.opacity = '0';
            span.style.animation = 'fade-in 0.3s ease forwards';
            span.style.animationDelay = `${i * this.settings.text_animation_speed + this.settings.entrance_delay + this.settings.entrance_duration}s`;
            element.appendChild(span);
        });
    }

    applyTextAnimation() {
        // Only apply text animations to main text and company name
        // Secondary phrases will use their own transition system
        if (this.settings.text_animation === 'typewriter') {
            const elements = [
                { element: this.mainTextEl, text: this.settings.main_text },
                { element: this.companyNameEl, text: this.settings.company_name }
            ];
            this.typewriterEffect(elements);
        } else if (this.settings.text_animation === 'fade-in-words') {
            this.fadeInWords(this.mainTextEl, this.settings.main_text);
            this.fadeInWords(this.companyNameEl, this.settings.company_name);
        } else if (this.settings.text_animation === 'slide-in-chars') {
            this.slideInChars(this.mainTextEl, this.settings.main_text);
            this.slideInChars(this.companyNameEl, this.settings.company_name);
        } else {
            this.mainTextEl.textContent = this.settings.main_text;
            this.companyNameEl.textContent = this.settings.company_name;
        }

        // Secondary phrases are handled separately in initializeSecondaryText
    }

    applyImageAnimation() {
        if (this.categoryImage && this.settings.image_animation !== 'none') {
            this.categoryImage.style.animation = `${this.settings.image_animation} 0.8s ease-out ${this.settings.entrance_delay + this.settings.entrance_duration + this.settings.image_animation_delay}s both`;
        }
    }

    applyLogoAnimation() {
        if (this.companyLogo && this.settings.logo_animation !== 'none') {
            this.companyLogo.style.animation = `${this.settings.logo_animation} 0.8s ease-out ${this.settings.entrance_delay + this.settings.entrance_duration + this.settings.logo_animation_delay}s both`;
        }
    }

    applyTickerAnimation() {
        if (this.settings.ticker_entrance !== 'none') {
            this.tickerContainer.style.animation = `${this.settings.ticker_entrance} 0.6s ease-out ${this.settings.entrance_delay + this.settings.entrance_duration + this.settings.ticker_entrance_delay}s both`;
        }
    }

    updateTickerSpeed(speed) {
        const textWidth = this.tickerText.offsetWidth;
        const duration = textWidth / speed;
        this.tickerText.style.animationDuration = `${duration}s`;
    }

    // Secondary Text Rotation - FIXED TO USE PROPER TRANSITIONS
    applyTransition(element, type, duration) {
        const transitions = {
            'fade': `opacity ${duration}s ease`,
            'slide-left': `transform ${duration}s ease, opacity ${duration}s ease`,
            'slide-right': `transform ${duration}s ease, opacity ${duration}s ease`,
            'slide-up': `transform ${duration}s ease, opacity ${duration}s ease`,
            'slide-down': `transform ${duration}s ease, opacity ${duration}s ease`,
            'zoom': `transform ${duration}s ease, opacity ${duration}s ease`
        };
        element.style.transition = transitions[type] || transitions['fade'];
    }

    getTransitionStyles(type, entering) {
        const styles = {
            'fade': {
                entering: { transform: 'none', opacity: '1' },
                exiting: { transform: 'none', opacity: '0' },
                initial: { transform: 'none', opacity: '0' }
            },
            'slide-left': {
                entering: { transform: 'translateX(0)', opacity: '1' },
                exiting: { transform: 'translateX(-100%)', opacity: '0' },
                initial: { transform: 'translateX(100%)', opacity: '0' }
            },
            'slide-right': {
                entering: { transform: 'translateX(0)', opacity: '1' },
                exiting: { transform: 'translateX(100%)', opacity: '0' },
                initial: { transform: 'translateX(-100%)', opacity: '0' }
            },
            'slide-up': {
                entering: { transform: 'translateY(0)', opacity: '1' },
                exiting: { transform: 'translateY(-50%)', opacity: '0' },
                initial: { transform: 'translateY(50%)', opacity: '0' }
            },
            'slide-down': {
                entering: { transform: 'translateY(0)', opacity: '1' },
                exiting: { transform: 'translateY(50%)', opacity: '0' },
                initial: { transform: 'translateY(-50%)', opacity: '0' }
            },
            'zoom': {
                entering: { transform: 'scale(1)', opacity: '1' },
                exiting: { transform: 'scale(0.8)', opacity: '0' },
                initial: { transform: 'scale(0.8)', opacity: '0' }
            }
        };

        const typeStyles = styles[type] || styles['fade'];
        if (entering === 'initial') {
            return typeStyles.initial;
        }
        return entering ? typeStyles.entering : typeStyles.exiting;
    }

    initializeSecondaryText() {
        this.clearRotationTimers();
        this.secondaryContainer.innerHTML = '';

        if (!this.settings.secondary_rotation_enabled || !this.settings.secondary_phrases || this.settings.secondary_phrases.length === 0) {
            const phrase = this.settings.secondary_phrases && this.settings.secondary_phrases.length > 0
                ? this.settings.secondary_phrases[0]
                : 'Default Secondary Text';
            const div = document.createElement('div');
            div.className = 'secondary-phrase active';
            div.textContent = phrase;
            div.style.position = 'relative';
            div.style.opacity = '1';

            // Apply transition settings even for single phrase
            this.applyTransition(div, this.settings.secondary_transition_type, this.settings.secondary_transition_duration);
            const enteringStyles = this.getTransitionStyles(this.settings.secondary_transition_type, true);
            Object.assign(div.style, enteringStyles);

            this.secondaryContainer.appendChild(div);
            return;
        }

        this.currentPhraseIndex = 0;
        this.settings.secondary_phrases.forEach((phrase, index) => {
            const div = document.createElement('div');
            div.className = 'secondary-phrase';
            div.textContent = phrase;

            // Apply transition to all phrases
            this.applyTransition(div, this.settings.secondary_transition_type, this.settings.secondary_transition_duration);

            if (index === 0) {
                // First phrase - make it visible with entering animation
                div.classList.add('active');
                div.style.position = 'relative';

                // Start with initial state
                const initialStyles = this.getTransitionStyles(this.settings.secondary_transition_type, 'initial');
                Object.assign(div.style, initialStyles);

                // Trigger reflow
                void div.offsetWidth;

                // Animate to entering state
                const enteringStyles = this.getTransitionStyles(this.settings.secondary_transition_type, true);
                Object.assign(div.style, enteringStyles);
            } else {
                // Hidden phrases
                div.style.position = 'absolute';
                div.style.top = '0';
                div.style.left = '0';
                div.style.width = '100%';
                div.style.opacity = '0';
            }

            this.secondaryContainer.appendChild(div);
        });

        this.startPhraseRotation();
    }

    startPhraseRotation() {
        if (!this.settings.secondary_rotation_enabled || this.settings.secondary_phrases.length <= 1) return;

        const totalDuration = (this.settings.secondary_display_duration + this.settings.secondary_transition_duration) * 1000;

        this.rotationInterval = setInterval(() => {
            this.rotatePhrases();
        }, totalDuration);
    }

    rotatePhrases() {
        const phrases = this.secondaryContainer.querySelectorAll('.secondary-phrase');
        if (phrases.length <= 1) return;

        const currentPhrase = phrases[this.currentPhraseIndex];
        const nextIndex = (this.currentPhraseIndex + 1) % phrases.length;
        const nextPhrase = phrases[nextIndex];

        // Apply transition to both phrases
        this.applyTransition(currentPhrase, this.settings.secondary_transition_type, this.settings.secondary_transition_duration);
        this.applyTransition(nextPhrase, this.settings.secondary_transition_type, this.settings.secondary_transition_duration);

        // Animate out current phrase
        const exitingStyles = this.getTransitionStyles(this.settings.secondary_transition_type, false);
        Object.assign(currentPhrase.style, exitingStyles);

        setTimeout(() => {
            // Hide current phrase
            currentPhrase.classList.remove('active');
            currentPhrase.style.position = 'absolute';
            currentPhrase.style.top = '0';
            currentPhrase.style.left = '0';
            currentPhrase.style.width = '100%';

            // Prepare next phrase in initial state
            nextPhrase.style.position = 'relative';
            nextPhrase.style.top = 'auto';
            nextPhrase.style.left = 'auto';
            nextPhrase.style.width = 'auto';
            nextPhrase.classList.add('active');

            const initialStyles = this.getTransitionStyles(this.settings.secondary_transition_type, 'initial');
            Object.assign(nextPhrase.style, initialStyles);

            // Trigger reflow
            void nextPhrase.offsetWidth;

            // Animate in next phrase
            const enteringStyles = this.getTransitionStyles(this.settings.secondary_transition_type, true);
            Object.assign(nextPhrase.style, enteringStyles);

            this.currentPhraseIndex = nextIndex;
        }, this.settings.secondary_transition_duration * 1000);
    }

    // Apply ALL visual styles immediately without reloading
    applyAllStyles() {
        // Background colors
        if (this.lowerThirdBg) {
            this.lowerThirdBg.style.background = `linear-gradient(135deg, ${this.settings.bg_color}f5 0%, ${this.settings.bg_color}e0 100%)`;
            this.lowerThirdBg.style.opacity = this.settings.opacity;
            this.lowerThirdBg.style.borderRadius = `${this.settings.border_radius}px`;
        }

        if (this.tickerContainer) {
            this.tickerContainer.style.background = `linear-gradient(90deg, ${this.settings.bg_color}dd 0%, ${this.settings.bg_color} 50%, ${this.settings.bg_color}dd 100%)`;
            this.tickerContainer.style.opacity = this.settings.opacity;
        }

        // Text colors
        if (this.mainTextEl) {
            this.mainTextEl.style.color = this.settings.text_color;
            this.mainTextEl.style.fontSize = `${this.settings.main_font_size}px`;
        }

        if (this.companyNameEl) {
            this.companyNameEl.style.color = this.settings.text_color;
            this.companyNameEl.style.fontSize = `${this.settings.main_font_size * 0.6}px`;
        }

        if (this.tickerText) {
            this.tickerText.style.color = this.settings.text_color;
            this.tickerText.style.fontSize = `${this.settings.ticker_font_size}px`;
        }

        // Accent color for decorative elements and images
        const accentElements = document.querySelectorAll('.corner-decoration, .accent-corner, .accent-stripe, .heart-accent, .corner-accent');
        accentElements.forEach(el => {
            el.style.borderColor = this.settings.accent_color;
        });

        // Update heart accents (wedding)
        const heartAccents = document.querySelectorAll('.heart-accent::before, .heart-accent::after');
        if (heartAccents.length > 0) {
            const style = document.createElement('style');
            style.textContent = `.heart-accent::before, .heart-accent::after { background: ${this.settings.accent_color}; }`;
            document.head.appendChild(style);
        }

        if (this.categoryImage) {
            this.categoryImage.style.borderColor = this.settings.accent_color;
            this.categoryImage.style.borderRadius = this.settings.border_radius > 25 ? '50%' : `${this.settings.border_radius}px`;
        }

        // Secondary text container
        if (this.secondaryContainer) {
            this.secondaryContainer.style.minHeight = `${this.settings.secondary_font_size * 1.3}px`;
        }

        document.querySelectorAll('.secondary-phrase').forEach(el => {
            el.style.fontSize = `${this.settings.secondary_font_size}px`;
            el.style.color = this.settings.accent_color;
            el.style.lineHeight = '1.3';
        });

        // Logo size
        if (this.companyLogo) {
            this.companyLogo.style.width = `${this.settings.logo_size}px`;
            this.companyLogo.style.height = `${this.settings.logo_size}px`;
        }

        // Font family
        document.body.style.fontFamily = this.settings.font_family;

        // Decorative elements visibility
        const decorativeElements = document.querySelectorAll('.corner-decoration, .corner-accent, .accent-stripe, .heart-accent, .divider-line');
        decorativeElements.forEach(el => {
            el.style.display = this.settings.show_decorative_elements ? 'block' : 'none';
        });

        // Ticker speed
        this.updateTickerSpeed(this.settings.ticker_speed);
    }

    // Initialize all animations
    initializeAnimations() {
        this.applyAllStyles();
        this.applyEntranceAnimation();
        this.applyTextAnimation();

        // Wait for text animations to complete before initializing secondary text rotation
        const textAnimationDelay = this.settings.text_animation !== 'none'
            ? (this.settings.entrance_delay + this.settings.entrance_duration + 2) * 1000
            : 100;

        setTimeout(() => {
            this.initializeSecondaryText();
        }, textAnimationDelay);

        this.applyImageAnimation();
        this.applyLogoAnimation();
        this.applyTickerAnimation();
        this.animationInitialized = true;
    }

    // Replay all animations
    replayAnimations() {
        this.clearTypewriterTimeouts();
        this.clearRotationTimers();
        const elements = [this.lowerThird, this.categoryImage, this.companyLogo, this.tickerContainer];
        elements.forEach(el => {
            if (el) {
                el.style.animation = 'none';
                void el.offsetWidth;
            }
        });

        setTimeout(() => {
            this.initializeAnimations();
        }, 50);
    }

    // Handle settings updates from polling - COMPLETELY REWRITTEN
    handleSettingsUpdate(newSettings) {
        console.log('Received settings update:', newSettings);

        // Track what actually changed
        let needsReload = false;
        let needsAnimationReplay = false;
        let stylesChanged = false;

        // Handle visibility changes FIRST (most important)
        if (newSettings.is_visible !== undefined && newSettings.is_visible !== this.settings.is_visible) {
            console.log('Visibility changed:', newSettings.is_visible);
            this.settings.is_visible = newSettings.is_visible;

            if (newSettings.is_visible) {
                // Turn ON: Remove hidden class and show overlay
                this.container.classList.remove('hidden');
                this.container.style.opacity = '1';
                // Replay animations when turning back on
                setTimeout(() => this.replayAnimations(), 100);
            } else {
                // Turn OFF: Make completely transparent
                this.container.style.opacity = '0';
                // After fade out, add hidden class
                setTimeout(() => {
                    this.container.classList.add('hidden');
                }, 500);
            }

            // Don't process other changes if visibility changed
            // This prevents conflicts during visibility toggle
            return;
        }

        // Check for changes that require page reload (images)
        if (newSettings.company_logo !== undefined && newSettings.company_logo !== this.settings.company_logo) {
            needsReload = true;
        }
        if (newSettings.category_image !== undefined && newSettings.category_image !== this.settings.category_image) {
            needsReload = true;
        }
        if (newSettings.show_category_image !== undefined && newSettings.show_category_image !== this.settings.show_category_image) {
            needsReload = true;
        }
        if (newSettings.show_company_logo !== undefined && newSettings.show_company_logo !== this.settings.show_company_logo) {
            needsReload = true;
        }

        // If reload needed, do it immediately
        if (needsReload) {
            console.log('Image settings changed, reloading page...');
            Object.assign(this.settings, newSettings);
            setTimeout(() => location.reload(), 300);
            return;
        }

        // Check for animation setting changes
        const animationFields = [
            'entrance_animation', 'entrance_duration', 'entrance_delay',
            'text_animation', 'text_animation_speed',
            'image_animation', 'image_animation_delay',
            'logo_animation', 'logo_animation_delay',
            'ticker_entrance', 'ticker_entrance_delay'
        ];

        for (const field of animationFields) {
            if (newSettings[field] !== undefined && newSettings[field] !== this.settings[field]) {
                needsAnimationReplay = true;
                break;
            }
        }

        // Check for style changes
        const styleFields = [
            'bg_color', 'accent_color', 'text_color', 'opacity',
            'main_font_size', 'secondary_font_size', 'ticker_font_size',
            'border_radius', 'font_family', 'logo_size', 'ticker_speed',
            'show_decorative_elements'
        ];

        for (const field of styleFields) {
            if (newSettings[field] !== undefined && newSettings[field] !== this.settings[field]) {
                stylesChanged = true;
                break;
            }
        }

        // Check for text content changes
        const textChanged =
            (newSettings.main_text !== undefined && this.decodeHTML(newSettings.main_text) !== this.settings.main_text) ||
            (newSettings.company_name !== undefined && this.decodeHTML(newSettings.company_name) !== this.settings.company_name) ||
            (newSettings.ticker_text !== undefined && this.decodeHTML(newSettings.ticker_text) !== this.tickerText.textContent);

        // Check for secondary phrases changes - INCLUDING TRANSITION SETTINGS
        const phrasesChanged =
            (newSettings.secondary_phrases && JSON.stringify(newSettings.secondary_phrases) !== JSON.stringify(this.settings.secondary_phrases)) ||
            (newSettings.secondary_rotation_enabled !== undefined && newSettings.secondary_rotation_enabled !== this.settings.secondary_rotation_enabled) ||
            (newSettings.secondary_display_duration !== undefined && newSettings.secondary_display_duration !== this.settings.secondary_display_duration) ||
            (newSettings.secondary_transition_type !== undefined && newSettings.secondary_transition_type !== this.settings.secondary_transition_type) ||
            (newSettings.secondary_transition_duration !== undefined && newSettings.secondary_transition_duration !== this.settings.secondary_transition_duration);

        // Update settings object
        Object.assign(this.settings, newSettings);

        // Decode HTML entities for text fields
        if (newSettings.main_text !== undefined) {
            this.settings.main_text = this.decodeHTML(newSettings.main_text);
        }
        if (newSettings.company_name !== undefined) {
            this.settings.company_name = this.decodeHTML(newSettings.company_name);
        }
        if (newSettings.ticker_text !== undefined) {
            this.settings.ticker_text = this.decodeHTML(newSettings.ticker_text);
            this.tickerText.textContent = this.settings.ticker_text;
        }

        // Apply updates in the correct order
        if (stylesChanged) {
            console.log('Applying style changes immediately...');
            this.applyAllStyles();
        }

        if (phrasesChanged) {
            console.log('Updating secondary text phrases...');
            this.initializeSecondaryText();
        }

        if (textChanged || needsAnimationReplay) {
            console.log('Replaying animations...');
            setTimeout(() => this.replayAnimations(), 100);
        }
    }

    // Polling
    pollForUpdates() {
        fetch(`/api/poll/${this.category}`)
            .then(response => response.json())
            .then(data => {
                if (this.lastTimestamp && data.timestamp === this.lastTimestamp) {
                    return;
                }

                if (this.lastTimestamp === null) {
                    this.lastTimestamp = data.timestamp;
                    return;
                }

                this.lastTimestamp = data.timestamp;
                this.handleSettingsUpdate(data.settings);
            })
            .catch(error => {
                console.error('Polling error:', error);
            });
    }

    // Start the overlay
    start() {
        console.log('Starting overlay controller...');

        // Check initial visibility state
        if (!this.settings.is_visible) {
            this.container.classList.add('hidden');
            this.container.style.opacity = '0';
            console.log('Overlay starting in hidden state');
        } else {
            // Initial animation only if visible
            setTimeout(() => {
                this.initializeAnimations();
            }, 100);
        }

        // Start polling
        this.pollInterval = setInterval(() => this.pollForUpdates(), 2000);

        // Initial poll after short delay
        setTimeout(() => this.pollForUpdates(), 1000);

        // Update ticker speed on animation iteration
        if (this.tickerText) {
            this.tickerText.addEventListener('animationiteration', () => {
                this.updateTickerSpeed(this.settings.ticker_speed);
            });
        }

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (this.pollInterval) clearInterval(this.pollInterval);
            this.clearRotationTimers();
            this.clearTypewriterTimeouts();
        });
    }
}

// Initialize overlay when DOM is ready
function initOverlay(category, settings) {
    console.log('Initializing overlay with category:', category);
    const controller = new OverlayController(category, settings);
    controller.start();
    return controller;
}