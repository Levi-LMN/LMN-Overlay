/**
 * Universal Overlay Display Controller - COMPLETE VERSION
 * Shared by funeral, wedding, and ceremony templates
 * Includes position, size, and all animation controls
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

    // ========================================================================
    // UTILITY FUNCTIONS
    // ========================================================================
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

    updateAccentColor(color) {
        document.documentElement.style.setProperty('--accent-color', color);
    }

    // ========================================================================
    // POSITION & SIZE APPLICATION - NEW
    // ========================================================================
    applyPositionAndSize() {
        if (!this.lowerThird) return;

        // Reset all positioning
        this.lowerThird.style.position = 'relative';
        this.lowerThird.style.top = 'auto';
        this.lowerThird.style.bottom = 'auto';
        this.lowerThird.style.left = 'auto';
        this.lowerThird.style.right = 'auto';
        this.lowerThird.style.transform = 'none';

        // Apply vertical position
        if (this.settings.vertical_position === 'top') {
            this.container.style.justifyContent = 'flex-start';
            this.container.style.paddingTop = '20px';
            this.container.style.paddingBottom = '0';
        } else if (this.settings.vertical_position === 'center') {
            this.container.style.justifyContent = 'center';
            this.container.style.paddingTop = '0';
            this.container.style.paddingBottom = '0';
        } else if (this.settings.vertical_position === 'bottom') {
            this.container.style.justifyContent = 'flex-end';
            this.container.style.paddingTop = '0';
            this.container.style.paddingBottom = '10px';
        } else if (this.settings.vertical_position === 'custom') {
            this.container.style.justifyContent = 'flex-start';
            this.lowerThird.style.position = 'fixed';
            if (this.settings.custom_top > 0) {
                this.lowerThird.style.top = `${this.settings.custom_top}px`;
            }
            if (this.settings.custom_bottom > 0) {
                this.lowerThird.style.bottom = `${this.settings.custom_bottom}px`;
            }
        }

        // Apply horizontal position
        if (this.settings.horizontal_position === 'left') {
            this.container.style.alignItems = 'flex-start';
            this.lowerThird.style.marginLeft = '0';
            this.lowerThird.style.marginRight = 'auto';
        } else if (this.settings.horizontal_position === 'center') {
            this.container.style.alignItems = 'center';
            this.lowerThird.style.marginLeft = 'auto';
            this.lowerThird.style.marginRight = 'auto';
        } else if (this.settings.horizontal_position === 'right') {
            this.container.style.alignItems = 'flex-end';
            this.lowerThird.style.marginLeft = 'auto';
            this.lowerThird.style.marginRight = '0';
        } else if (this.settings.horizontal_position === 'custom') {
            if (this.settings.custom_left > 0) {
                this.lowerThird.style.left = `${this.settings.custom_left}px`;
            }
            if (this.settings.custom_right > 0) {
                this.lowerThird.style.right = `${this.settings.custom_right}px`;
            }
        }

        // Apply container width
        if (this.settings.container_width === 'full') {
            this.lowerThird.style.width = '100%';
            this.lowerThird.style.maxWidth = 'none';
            this.lowerThird.style.minWidth = 'auto';
        } else if (this.settings.container_width === 'custom') {
            this.lowerThird.style.width = `${this.settings.custom_width}px`;
            this.lowerThird.style.maxWidth = `${this.settings.container_max_width}px`;
            this.lowerThird.style.minWidth = `${this.settings.container_min_width}px`;
        } else {
            // Auto width
            this.lowerThird.style.width = 'auto';
            this.lowerThird.style.maxWidth = `${this.settings.container_max_width}px`;
            this.lowerThird.style.minWidth = `${this.settings.container_min_width}px`;
        }

        // Apply container height
        if (this.settings.container_height === 'custom') {
            this.lowerThird.style.height = `${this.settings.custom_height}px`;
        } else {
            this.lowerThird.style.height = 'auto';
        }

        // Apply container padding
        const contentSection = this.lowerThird.querySelector('.content-section');
        if (contentSection) {
            contentSection.style.padding = `${this.settings.container_padding}px`;
        }
    }

    // ========================================================================
    // TEXT SCALING APPLICATION - NEW
    // ========================================================================
    applyTextScaling() {
        if (!this.mainTextEl) return;

        // Apply line height
        this.mainTextEl.style.lineHeight = this.settings.text_line_height;
        if (this.secondaryContainer) {
            this.secondaryContainer.style.lineHeight = this.settings.text_line_height;
        }
        if (this.companyNameEl) {
            this.companyNameEl.style.lineHeight = this.settings.text_line_height;
        }

        // Apply text truncation
        if (this.settings.enable_text_truncation) {
            this.mainTextEl.style.overflow = 'hidden';
            this.mainTextEl.style.textOverflow = 'ellipsis';
            this.mainTextEl.style.whiteSpace = 'nowrap';
        } else {
            this.mainTextEl.style.overflow = 'visible';
            this.mainTextEl.style.textOverflow = 'clip';
            this.mainTextEl.style.whiteSpace = 'normal';
        }

        // Apply max lines (webkit only, but works in most browsers)
        if (this.settings.text_max_lines > 1 && !this.settings.enable_text_truncation) {
            this.mainTextEl.style.display = '-webkit-box';
            this.mainTextEl.style.webkitLineClamp = this.settings.text_max_lines;
            this.mainTextEl.style.webkitBoxOrient = 'vertical';
            this.mainTextEl.style.overflow = 'hidden';
            this.mainTextEl.style.whiteSpace = 'normal';
        }

        // Apply scale mode
        if (this.settings.text_scale_mode === 'fit') {
            // Make text fit container by adjusting font size dynamically
            this.fitTextToContainer();
        } else if (this.settings.text_scale_mode === 'responsive') {
            // Use vw units for responsive scaling
            const baseSize = this.settings.main_font_size;
            const vwSize = (baseSize / 1920) * 100; // Convert px to vw
            this.mainTextEl.style.fontSize = `${vwSize}vw`;
        } else {
            // Fixed size
            this.mainTextEl.style.fontSize = `${this.settings.main_font_size}px`;
        }
    }

    fitTextToContainer() {
        if (!this.lowerThird || !this.mainTextEl) return;

        const containerWidth = this.lowerThird.offsetWidth;
        const textWidth = this.mainTextEl.scrollWidth;

        if (textWidth > containerWidth) {
            const scale = containerWidth / textWidth * 0.95; // 95% to leave some margin
            const newSize = Math.floor(this.settings.main_font_size * scale);
            this.mainTextEl.style.fontSize = `${newSize}px`;
        }
    }

    // ========================================================================
    // ANIMATION FUNCTIONS
    // ========================================================================
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

    // ========================================================================
    // SECONDARY TEXT ROTATION
    // ========================================================================
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

            this.applyTransition(div, this.settings.secondary_transition_type, this.settings.secondary_transition_duration);

            if (index === 0) {
                div.classList.add('active');
                div.style.position = 'relative';

                const initialStyles = this.getTransitionStyles(this.settings.secondary_transition_type, 'initial');
                Object.assign(div.style, initialStyles);

                void div.offsetWidth;

                const enteringStyles = this.getTransitionStyles(this.settings.secondary_transition_type, true);
                Object.assign(div.style, enteringStyles);
            } else {
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

        this.applyTransition(currentPhrase, this.settings.secondary_transition_type, this.settings.secondary_transition_duration);
        this.applyTransition(nextPhrase, this.settings.secondary_transition_type, this.settings.secondary_transition_duration);

        const exitingStyles = this.getTransitionStyles(this.settings.secondary_transition_type, false);
        Object.assign(currentPhrase.style, exitingStyles);

        setTimeout(() => {
            currentPhrase.classList.remove('active');
            currentPhrase.style.position = 'absolute';
            currentPhrase.style.top = '0';
            currentPhrase.style.left = '0';
            currentPhrase.style.width = '100%';

            nextPhrase.style.position = 'relative';
            nextPhrase.style.top = 'auto';
            nextPhrase.style.left = 'auto';
            nextPhrase.style.width = 'auto';
            nextPhrase.classList.add('active');

            const initialStyles = this.getTransitionStyles(this.settings.secondary_transition_type, 'initial');
            Object.assign(nextPhrase.style, initialStyles);

            void nextPhrase.offsetWidth;

            const enteringStyles = this.getTransitionStyles(this.settings.secondary_transition_type, true);
            Object.assign(nextPhrase.style, enteringStyles);

            this.currentPhraseIndex = nextIndex;
        }, this.settings.secondary_transition_duration * 1000);
    }

    // ========================================================================
    // APPLY ALL VISUAL STYLES
    // ========================================================================
    applyAllStyles() {
        this.updateAccentColor(this.settings.accent_color);

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

        if (this.secondaryContainer) {
            this.secondaryContainer.style.minHeight = `${this.settings.secondary_font_size * 1.3}px`;
        }

        document.querySelectorAll('.secondary-phrase').forEach(el => {
            el.style.fontSize = `${this.settings.secondary_font_size}px`;
            el.style.lineHeight = '1.3';
        });

        // Logo size
        if (this.companyLogo) {
            this.companyLogo.style.width = `${this.settings.logo_size}px`;
            this.companyLogo.style.height = `${this.settings.logo_size}px`;
        }

        // Font family
        document.body.style.fontFamily = this.settings.font_family;

        // Decorative elements
        const decorativeElements = document.querySelectorAll('.corner-decoration, .corner-accent, .accent-stripe, .heart-accent, .divider-line, .corner-flourish');
        decorativeElements.forEach(el => {
            el.style.display = this.settings.show_decorative_elements ? 'block' : 'none';
        });

        // Ticker speed
        this.updateTickerSpeed(this.settings.ticker_speed);

        // Apply position and size - NEW
        this.applyPositionAndSize();

        // Apply text scaling - NEW
        this.applyTextScaling();
    }

    // ========================================================================
    // INITIALIZE ALL ANIMATIONS
    // ========================================================================
    initializeAnimations() {
        this.applyAllStyles();
        this.applyEntranceAnimation();
        this.applyTextAnimation();

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

    // ========================================================================
    // REPLAY ANIMATIONS
    // ========================================================================
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

    // ========================================================================
    // HANDLE SETTINGS UPDATES
    // ========================================================================
    handleSettingsUpdate(newSettings) {
        console.log('Received settings update:', newSettings);

        let needsReload = false;
        let needsAnimationReplay = false;
        let stylesChanged = false;

        // Handle visibility changes FIRST
        if (newSettings.is_visible !== undefined && newSettings.is_visible !== this.settings.is_visible) {
            console.log('Visibility changed:', newSettings.is_visible);
            this.settings.is_visible = newSettings.is_visible;

            if (newSettings.is_visible) {
                this.container.classList.remove('hidden');
                this.container.style.opacity = '1';
                setTimeout(() => this.replayAnimations(), 100);
            } else {
                this.container.style.opacity = '0';
                setTimeout(() => {
                    this.container.classList.add('hidden');
                }, 500);
            }
            return;
        }

        // Check for image changes (requires reload)
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
            'show_decorative_elements',
            // Position and size fields - NEW
            'vertical_position', 'horizontal_position', 'custom_top', 'custom_bottom',
            'custom_left', 'custom_right', 'container_width', 'custom_width',
            'container_max_width', 'container_min_width', 'container_height',
            'custom_height', 'container_padding',
            // Text scaling fields - NEW
            'text_scale_mode', 'text_line_height', 'text_max_lines', 'enable_text_truncation'
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

        // Check for secondary phrases changes
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

    // ========================================================================
    // POLLING
    // ========================================================================
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

    // ========================================================================
    // START THE OVERLAY
    // ========================================================================
    start() {
        console.log('Starting overlay controller...');

        if (!this.settings.is_visible) {
            this.container.classList.add('hidden');
            this.container.style.opacity = '0';
            console.log('Overlay starting in hidden state');
        } else {
            setTimeout(() => {
                this.initializeAnimations();
            }, 100);
        }

        this.pollInterval = setInterval(() => this.pollForUpdates(), 2000);
        setTimeout(() => this.pollForUpdates(), 1000);

        if (this.tickerText) {
            this.tickerText.addEventListener('animationiteration', () => {
                this.updateTickerSpeed(this.settings.ticker_speed);
            });
        }

        window.addEventListener('beforeunload', () => {
            if (this.pollInterval) clearInterval(this.pollInterval);
            this.clearRotationTimers();
            this.clearTypewriterTimeouts();
        });
    }
}

// ============================================================================
// INITIALIZE OVERLAY FUNCTION (Called by templates)
// ============================================================================
function initOverlay(category, settings) {
    console.log('Initializing overlay with category:', category);
    const controller = new OverlayController(category, settings);
    controller.start();
    return controller;
}