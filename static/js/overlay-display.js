/**
 * Unified Overlay Display Controller
 * Handles animations, polling, and live updates for all overlay categories
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
        if (this.settings.text_animation === 'typewriter') {
            this.typewriterEffect([
                { element: this.mainTextEl, text: this.settings.main_text },
                { element: this.companyNameEl, text: this.settings.company_name }
            ]);
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

    // Secondary Text Rotation
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
                entering: { opacity: '1' },
                exiting: { opacity: '0' }
            },
            'slide-left': {
                entering: { transform: 'translateX(0)', opacity: '1' },
                exiting: { transform: 'translateX(-100%)', opacity: '0' }
            },
            'slide-right': {
                entering: { transform: 'translateX(0)', opacity: '1' },
                exiting: { transform: 'translateX(100%)', opacity: '0' }
            },
            'slide-up': {
                entering: { transform: 'translateY(0)', opacity: '1' },
                exiting: { transform: 'translateY(-50%)', opacity: '0' }
            },
            'slide-down': {
                entering: { transform: 'translateY(0)', opacity: '1' },
                exiting: { transform: 'translateY(50%)', opacity: '0' }
            },
            'zoom': {
                entering: { transform: 'scale(1)', opacity: '1' },
                exiting: { transform: 'scale(0.8)', opacity: '0' }
            }
        };

        const typeStyles = styles[type] || styles['fade'];
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
            div.style.position = 'relative';
            div.textContent = phrase;
            this.secondaryContainer.appendChild(div);
            return;
        }

        this.currentPhraseIndex = 0;
        this.settings.secondary_phrases.forEach((phrase, index) => {
            const div = document.createElement('div');
            div.className = 'secondary-phrase';
            div.textContent = phrase;
            if (index === 0) {
                div.classList.add('active');
                const enterStyles = this.getTransitionStyles(this.settings.secondary_transition_type, true);
                Object.assign(div.style, enterStyles);
            }
            this.applyTransition(div, this.settings.secondary_transition_type, this.settings.secondary_transition_duration);
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

        const exitStyles = this.getTransitionStyles(this.settings.secondary_transition_type, false);
        Object.assign(currentPhrase.style, exitStyles);

        const enteringInitialStyles = {
            'slide-left': { transform: 'translateX(100%)', opacity: '0' },
            'slide-right': { transform: 'translateX(-100%)', opacity: '0' },
            'slide-up': { transform: 'translateY(50%)', opacity: '0' },
            'slide-down': { transform: 'translateY(-50%)', opacity: '0' },
            'zoom': { transform: 'scale(0.8)', opacity: '0' },
            'fade': { opacity: '0' }
        };

        const initialStyles = enteringInitialStyles[this.settings.secondary_transition_type] || { opacity: '0' };
        Object.assign(nextPhrase.style, initialStyles);
        nextPhrase.classList.add('active');

        void nextPhrase.offsetWidth;

        const timeout = setTimeout(() => {
            const enterStyles = this.getTransitionStyles(this.settings.secondary_transition_type, true);
            Object.assign(nextPhrase.style, enterStyles);

            const cleanupTimeout = setTimeout(() => {
                currentPhrase.classList.remove('active');
            }, this.settings.secondary_transition_duration * 1000);

            this.rotationTimeouts.push(cleanupTimeout);
        }, 50);

        this.rotationTimeouts.push(timeout);
        this.currentPhraseIndex = nextIndex;
    }

    // Initialize all animations
    initializeAnimations() {
        this.applyEntranceAnimation();
        this.applyTextAnimation();
        this.initializeSecondaryText();
        this.applyImageAnimation();
        this.applyLogoAnimation();
        this.applyTickerAnimation();
        this.updateTickerSpeed(this.settings.ticker_speed);
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

    // Live Settings Updates
    updateLiveSettings(s) {
        let settingsChanged = false;

        // Update colors immediately
        if (s.bg_color !== undefined && s.bg_color !== this.settings.bg_color) {
            this.settings.bg_color = s.bg_color;
            this.lowerThirdBg.style.background = `linear-gradient(135deg, ${s.bg_color}f5 0%, ${s.bg_color}e0 100%)`;
            if (this.tickerContainer) {
                this.tickerContainer.style.background = `linear-gradient(90deg, ${s.bg_color}dd 0%, ${s.bg_color} 50%, ${s.bg_color}dd 100%)`;
            }
            settingsChanged = true;
        }

        if (s.accent_color !== undefined && s.accent_color !== this.settings.accent_color) {
            this.settings.accent_color = s.accent_color;
            document.documentElement.style.setProperty('--accent-color', s.accent_color);
            // Update all elements with accent color
            document.querySelectorAll('.corner-decoration, .accent-corner::before, .accent-accent::after, .accent-stripe, .heart-accent::before, .heart-accent::after').forEach(el => {
                el.style.borderColor = s.accent_color;
                el.style.background = s.accent_color;
            });
            if (this.categoryImage) {
                this.categoryImage.style.borderColor = s.accent_color;
            }
            settingsChanged = true;
        }

        if (s.text_color !== undefined && s.text_color !== this.settings.text_color) {
            this.settings.text_color = s.text_color;
            this.mainTextEl.style.color = s.text_color;
            this.companyNameEl.style.color = s.text_color;
            this.tickerText.style.color = s.text_color;
            settingsChanged = true;
        }

        // Update opacity immediately
        if (s.opacity !== undefined && s.opacity !== this.settings.opacity) {
            this.settings.opacity = s.opacity;
            this.lowerThirdBg.style.opacity = s.opacity;
            if (this.tickerContainer) {
                this.tickerContainer.style.opacity = s.opacity;
            }
            settingsChanged = true;
        }

        // Update font sizes immediately
        if (s.main_font_size !== undefined && s.main_font_size !== this.settings.main_font_size) {
            this.settings.main_font_size = s.main_font_size;
            this.mainTextEl.style.fontSize = `${s.main_font_size}px`;
            this.companyNameEl.style.fontSize = `${s.main_font_size * 0.6}px`;
            settingsChanged = true;
        }

        if (s.secondary_font_size !== undefined && s.secondary_font_size !== this.settings.secondary_font_size) {
            this.settings.secondary_font_size = s.secondary_font_size;
            document.querySelectorAll('.secondary-phrase').forEach(el => {
                el.style.fontSize = `${s.secondary_font_size}px`;
            });
            this.secondaryContainer.style.height = `${s.secondary_font_size * 1.2}px`;
            settingsChanged = true;
        }

        if (s.ticker_font_size !== undefined && s.ticker_font_size !== this.settings.ticker_font_size) {
            this.settings.ticker_font_size = s.ticker_font_size;
            this.tickerText.style.fontSize = `${s.ticker_font_size}px`;
            settingsChanged = true;
        }

        // Update border radius immediately
        if (s.border_radius !== undefined && s.border_radius !== this.settings.border_radius) {
            this.settings.border_radius = s.border_radius;
            this.lowerThirdBg.style.borderRadius = `${s.border_radius}px`;
            if (this.categoryImage) {
                this.categoryImage.style.borderRadius = s.border_radius > 25 ? '50%' : `${s.border_radius}px`;
            }
            settingsChanged = true;
        }

        // Update font family immediately
        if (s.font_family !== undefined && s.font_family !== this.settings.font_family) {
            this.settings.font_family = s.font_family;
            document.body.style.fontFamily = s.font_family;
            settingsChanged = true;
        }

        // Update logo size immediately
        if (s.logo_size !== undefined && s.logo_size !== this.settings.logo_size) {
            this.settings.logo_size = s.logo_size;
            if (this.companyLogo) {
                this.companyLogo.style.width = `${s.logo_size}px`;
                this.companyLogo.style.height = `${s.logo_size}px`;
            }
            settingsChanged = true;
        }

        // Update ticker speed immediately
        if (s.ticker_speed !== undefined && s.ticker_speed !== this.settings.ticker_speed) {
            this.settings.ticker_speed = s.ticker_speed;
            this.updateTickerSpeed(s.ticker_speed);
            settingsChanged = true;
        }

        // Update decorative elements visibility immediately
        if (s.show_decorative_elements !== undefined && s.show_decorative_elements !== this.settings.show_decorative_elements) {
            this.settings.show_decorative_elements = s.show_decorative_elements;
            document.querySelectorAll('.corner-decoration, .corner-accent, .accent-stripe, .heart-accent, .divider-line').forEach(el => {
                el.style.display = s.show_decorative_elements ? 'block' : 'none';
            });
            settingsChanged = true;
        }

        return settingsChanged;
    }

    // Handle settings updates from polling
    handleSettingsUpdate(s) {
        // First, apply all live settings that don't require reload
        const liveSettingsChanged = this.updateLiveSettings(s);

        // Check if images/visibility changed (requires reload)
        const needsReload =
            (s.company_logo !== undefined && s.company_logo !== this.settings.company_logo) ||
            (s.category_image !== undefined && s.category_image !== this.settings.category_image) ||
            (s.show_category_image !== undefined && s.show_category_image !== this.settings.show_category_image) ||
            (s.show_company_logo !== undefined && s.show_company_logo !== this.settings.show_company_logo);

        if (needsReload) {
            setTimeout(() => location.reload(), 500);
            return;
        }

        // Handle secondary text changes
        const phrasesChanged = s.secondary_phrases && JSON.stringify(s.secondary_phrases) !== JSON.stringify(this.settings.secondary_phrases);
        const rotationChanged = s.secondary_rotation_enabled !== undefined && s.secondary_rotation_enabled !== this.settings.secondary_rotation_enabled;
        const rotationSettingsChanged =
            (s.secondary_display_duration !== undefined && s.secondary_display_duration !== this.settings.secondary_display_duration) ||
            (s.secondary_transition_type !== undefined && s.secondary_transition_type !== this.settings.secondary_transition_type) ||
            (s.secondary_transition_duration !== undefined && s.secondary_transition_duration !== this.settings.secondary_transition_duration);

        if (phrasesChanged || rotationChanged || rotationSettingsChanged) {
            if (s.secondary_phrases) this.settings.secondary_phrases = s.secondary_phrases;
            if (s.secondary_rotation_enabled !== undefined) this.settings.secondary_rotation_enabled = s.secondary_rotation_enabled;
            if (s.secondary_display_duration !== undefined) this.settings.secondary_display_duration = s.secondary_display_duration;
            if (s.secondary_transition_type !== undefined) this.settings.secondary_transition_type = s.secondary_transition_type;
            if (s.secondary_transition_duration !== undefined) this.settings.secondary_transition_duration = s.secondary_transition_duration;
            this.initializeSecondaryText();
        }

        // Handle text content changes
        if (s.main_text !== undefined && this.decodeHTML(s.main_text) !== this.settings.main_text) {
            this.settings.main_text = this.decodeHTML(s.main_text);
            this.applyTextAnimation();
        }

        if (s.company_name !== undefined && this.decodeHTML(s.company_name) !== this.settings.company_name) {
            this.settings.company_name = this.decodeHTML(s.company_name);
            if (this.companyNameEl) {
                this.companyNameEl.textContent = this.settings.company_name;
            }
        }

        if (s.ticker_text !== undefined && this.decodeHTML(s.ticker_text) !== this.tickerText.textContent) {
            this.tickerText.textContent = this.decodeHTML(s.ticker_text);
            this.updateTickerSpeed(this.settings.ticker_speed);
        }

        // Handle animation changes (requires replay)
        const animationChanged =
            (s.entrance_animation !== undefined && s.entrance_animation !== this.settings.entrance_animation) ||
            (s.entrance_duration !== undefined && s.entrance_duration !== this.settings.entrance_duration) ||
            (s.entrance_delay !== undefined && s.entrance_delay !== this.settings.entrance_delay) ||
            (s.text_animation !== undefined && s.text_animation !== this.settings.text_animation) ||
            (s.image_animation !== undefined && s.image_animation !== this.settings.image_animation) ||
            (s.logo_animation !== undefined && s.logo_animation !== this.settings.logo_animation) ||
            (s.ticker_entrance !== undefined && s.ticker_entrance !== this.settings.ticker_entrance);

        if (animationChanged) {
            if (s.entrance_animation !== undefined) this.settings.entrance_animation = s.entrance_animation;
            if (s.entrance_duration !== undefined) this.settings.entrance_duration = s.entrance_duration;
            if (s.entrance_delay !== undefined) this.settings.entrance_delay = s.entrance_delay;
            if (s.text_animation !== undefined) this.settings.text_animation = s.text_animation;
            if (s.text_animation_speed !== undefined) this.settings.text_animation_speed = s.text_animation_speed;
            if (s.image_animation !== undefined) this.settings.image_animation = s.image_animation;
            if (s.image_animation_delay !== undefined) this.settings.image_animation_delay = s.image_animation_delay;
            if (s.logo_animation !== undefined) this.settings.logo_animation = s.logo_animation;
            if (s.logo_animation_delay !== undefined) this.settings.logo_animation_delay = s.logo_animation_delay;
            if (s.ticker_entrance !== undefined) this.settings.ticker_entrance = s.ticker_entrance;
            if (s.ticker_entrance_delay !== undefined) this.settings.ticker_entrance_delay = s.ticker_entrance_delay;

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
        setTimeout(() => this.initializeAnimations(), 100);
        this.pollInterval = setInterval(() => this.pollForUpdates(), 3000);
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
        });
    }
}

// Initialize overlay when DOM is ready
function initOverlay(category, settings) {
    const controller = new OverlayController(category, settings);
    controller.start();
    return controller;
}