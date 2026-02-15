// OBS Lower-Third Overlay Control Script
// Real-time updates from Control Panel

class OverlayController {
    constructor(category) {
        this.category = category;
        this.settings = null;
        this.pollInterval = null;
        this.secondaryPhraseIndex = 0;
        this.secondaryInterval = null;
        this.lastUpdateTime = null;

        this.init();
    }

    async init() {
        await this.loadSettings();
        this.applySettings();
        this.applyVisibility(); // Force visibility check immediately
        this.startPolling();
        this.initializeAnimations();
    }

    async loadSettings() {
        try {
            const response = await fetch(`/api/poll/${this.category}`);
            const data = await response.json();

            if (data.settings) {
                this.settings = data.settings;
                this.lastUpdateTime = data.timestamp;
            }
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    startPolling() {
        // Poll for updates every 500ms for instant updates
        this.pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/poll/${this.category}`);
                const data = await response.json();

                if (data.timestamp !== this.lastUpdateTime) {
                    this.settings = data.settings;
                    this.lastUpdateTime = data.timestamp;
                    this.applySettings();
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 500);
    }

    applySettings() {
        if (!this.settings) return;

        this.applyVisibility();
        this.applyContent();
        this.applyColors();
        this.applyTypography();
        this.applyLayout();
        this.applyMedia();
        this.applyAnimations();
        this.applyTicker();
        this.initializeSecondaryRotation();
    }

    applyVisibility() {
        const container = document.querySelector('.overlay-container');
        if (container) {
            if (this.settings.is_visible) {
                container.style.display = 'flex';
                container.style.opacity = '1';
            } else {
                container.style.display = 'none';
                container.style.opacity = '0';
            }
        }
    }

    applyContent() {
        // Main Text
        const mainText = document.querySelector('.main-text');
        if (mainText && this.settings.main_text) {
            mainText.textContent = this.settings.main_text;
        }

        // Secondary Text
        const secondaryText = document.querySelector('.secondary-text');
        if (secondaryText && this.settings.secondary_text) {
            secondaryText.textContent = this.settings.secondary_text;
        }

        // Company Name
        const companyName = document.querySelector('.company-name');
        if (companyName && this.settings.company_name) {
            companyName.textContent = this.settings.company_name;
        }
    }

    applyColors() {
        const container = document.querySelector('.overlay-container');
        if (!container) return;

        // Overlay Background
        if (this.settings.overlay_bg_color) {
            const opacity = this.settings.overlay_bg_opacity || 1;
            const rgb = this.hexToRgb(this.settings.overlay_bg_color);
            container.style.background = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${opacity})`;
        }

        // Main Text
        const mainText = document.querySelector('.main-text');
        if (mainText) {
            mainText.style.color = this.settings.main_text_color || '#ffffff';
            if (this.settings.main_text_bg_color) {
                const opacity = this.settings.main_text_bg_opacity || 1;
                const rgb = this.hexToRgb(this.settings.main_text_bg_color);
                mainText.style.background = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${opacity})`;
            }
        }

        // Secondary Text
        const secondaryText = document.querySelector('.secondary-text');
        if (secondaryText) {
            secondaryText.style.color = this.settings.secondary_text_color || '#ffffff';
            if (this.settings.secondary_text_bg_color) {
                const opacity = this.settings.secondary_text_bg_opacity || 1;
                const rgb = this.hexToRgb(this.settings.secondary_text_bg_color);
                secondaryText.style.background = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${opacity})`;
            }
        }

        // Company Name
        const companyName = document.querySelector('.company-name');
        if (companyName) {
            companyName.style.color = this.settings.company_name_color || '#ffffff';
            if (this.settings.company_name_bg_color) {
                const opacity = this.settings.company_name_bg_opacity || 1;
                const rgb = this.hexToRgb(this.settings.company_name_bg_color);
                companyName.style.background = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${opacity})`;
            }
        }

        // Border
        if (this.settings.border_width > 0) {
            container.style.border = `${this.settings.border_width}px solid ${this.settings.border_color}`;
        } else {
            container.style.border = 'none';
        }

        container.style.borderRadius = `${this.settings.border_radius}px`;

        // Accent Color (for decorative elements)
        const decorativeElements = document.querySelectorAll('.decorative-line, .decorative-corner');
        decorativeElements.forEach(el => {
            el.style.color = this.settings.accent_color || '#ffffff';
        });
    }

    applyTypography() {
        const fontFamily = this.settings.font_family || 'Arial, sans-serif';
        document.body.style.fontFamily = fontFamily;

        // Font Sizes
        const mainText = document.querySelector('.main-text');
        if (mainText) {
            mainText.style.fontSize = `${this.settings.main_font_size}px`;
            mainText.style.lineHeight = this.settings.text_line_height || 1.2;
        }

        const secondaryText = document.querySelector('.secondary-text');
        if (secondaryText) {
            secondaryText.style.fontSize = `${this.settings.secondary_font_size}px`;
            secondaryText.style.lineHeight = this.settings.text_line_height || 1.2;
        }

        const companyName = document.querySelector('.company-name');
        if (companyName) {
            companyName.style.fontSize = `${this.settings.company_name_font_size}px`;
        }

        // Text Truncation
        const container = document.querySelector('.overlay-container');
        if (this.settings.enable_text_truncation) {
            mainText?.classList.add('text-truncate');
            secondaryText?.classList.add('text-truncate');
            if (mainText) mainText.style.webkitLineClamp = this.settings.text_max_lines;
            if (secondaryText) secondaryText.style.webkitLineClamp = this.settings.text_max_lines;
        } else {
            mainText?.classList.remove('text-truncate');
            secondaryText?.classList.remove('text-truncate');
        }

        // Text Scale Mode
        if (this.settings.text_scale_mode === 'responsive') {
            container?.classList.add('text-responsive');
        } else {
            container?.classList.remove('text-responsive');
        }
    }

    applyLayout() {
        const container = document.querySelector('.overlay-container');
        if (!container) return;

        // Remove all position classes but preserve visibility
        const currentDisplay = container.style.display;
        container.className = 'overlay-container';
        container.style.display = currentDisplay; // Restore visibility

        // Vertical Position
        const vPos = this.settings.vertical_position || 'bottom';
        if (vPos === 'custom') {
            container.style.top = this.settings.custom_top ? `${this.settings.custom_top}px` : 'auto';
            container.style.bottom = this.settings.custom_bottom ? `${this.settings.custom_bottom}px` : 'auto';
        } else {
            container.classList.add(`position-${vPos}`);
            container.style.top = '';
            container.style.bottom = '';
        }

        // Horizontal Position
        const hPos = this.settings.horizontal_position || 'left';
        if (hPos === 'custom') {
            container.style.left = this.settings.custom_left ? `${this.settings.custom_left}px` : 'auto';
            container.style.right = this.settings.custom_right ? `${this.settings.custom_right}px` : 'auto';
        } else {
            container.classList.add(`position-${hPos}`);
            container.style.left = '';
            container.style.right = '';
        }

        // Container Dimensions
        if (this.settings.container_width === 'full') {
            container.style.width = '100%';
        } else if (this.settings.container_width === 'custom' && this.settings.custom_width) {
            container.style.width = `${this.settings.custom_width}px`;
        } else {
            container.style.width = 'auto';
        }

        if (this.settings.container_max_width) {
            container.style.maxWidth = `${this.settings.container_max_width}px`;
        }
        if (this.settings.container_min_width) {
            container.style.minWidth = `${this.settings.container_min_width}px`;
        }

        if (this.settings.container_height === 'custom' && this.settings.custom_height) {
            container.style.height = `${this.settings.custom_height}px`;
        } else {
            container.style.height = 'auto';
        }

        container.style.padding = `${this.settings.container_padding || 20}px`;

        // Layout Style
        const layoutStyle = this.settings.layout_style || 'default';
        container.classList.add(`layout-${layoutStyle}`);

        // Decorative Elements
        const decorativeElements = document.querySelectorAll('.decorative-line, .decorative-corner');
        decorativeElements.forEach(el => {
            el.style.display = this.settings.show_decorative_elements ? 'block' : 'none';
        });

        // Overall Opacity
        if (currentDisplay !== 'none') {
            container.style.opacity = this.settings.opacity || 1;
        }
    }

    applyMedia() {
        // Logo
        const logoContainer = document.querySelector('.logo-container');
        const logoImg = document.querySelector('.logo-container img');

        if (logoContainer && logoImg) {
            if (this.settings.show_company_logo && this.settings.company_logo) {
                logoContainer.style.display = 'flex';
                logoImg.src = `/static/${this.settings.company_logo}`;
                logoImg.style.width = `${this.settings.logo_size}px`;
                logoImg.style.height = `${this.settings.logo_size}px`;
                logoImg.style.opacity = this.settings.logo_opacity || 1;
                logoImg.style.borderRadius = `${this.settings.logo_border_radius}px`;

                if (this.settings.logo_shadow) {
                    logoImg.classList.add('shadow-logo');
                } else {
                    logoImg.classList.remove('shadow-logo');
                }
            } else {
                logoContainer.style.display = 'none';
            }
        }

        // Category Background Image
        const categoryImage = document.querySelector('.category-image');
        if (categoryImage) {
            if (this.settings.show_category_image && this.settings.category_image) {
                categoryImage.style.display = 'block';
                categoryImage.src = `/static/${this.settings.category_image}`;
            } else {
                categoryImage.style.display = 'none';
            }
        }
    }

    applyAnimations() {
        const container = document.querySelector('.overlay-container');
        if (!container) return;

        // Entrance Animation
        const entranceAnim = this.settings.entrance_animation || 'fadeIn';
        const entranceDuration = this.settings.entrance_duration || 1;
        const entranceDelay = this.settings.entrance_delay || 0;

        container.style.animation = `${entranceAnim} ${entranceDuration}s ease-out ${entranceDelay}s both`;

        // Text Animation
        const textElements = document.querySelectorAll('.main-text, .secondary-text, .company-name');
        const textAnim = this.settings.text_animation;
        const textSpeed = this.settings.text_animation_speed || 2;

        textElements.forEach(el => {
            if (textAnim && textAnim !== 'none') {
                el.style.animation = `${textAnim} ${textSpeed}s ease-in-out infinite`;
            } else {
                el.style.animation = '';
            }
        });

        // Logo Animation
        const logoImg = document.querySelector('.logo-container img');
        if (logoImg) {
            const logoAnim = this.settings.logo_animation;
            const logoDelay = this.settings.logo_animation_delay || 0;

            if (logoAnim && logoAnim !== 'none') {
                logoImg.style.animation = `${logoAnim} 1s ease-out ${logoDelay}s both`;
            }

            // Logo Display Animation (repeating)
            if (this.settings.logo_display_animation_enabled && this.settings.logo_display_animation) {
                const displayAnim = this.settings.logo_display_animation;
                const displayDuration = this.settings.logo_display_animation_duration || 1;
                const displayFrequency = this.settings.logo_display_animation_frequency || 5;

                setInterval(() => {
                    logoImg.style.animation = `${displayAnim} ${displayDuration}s ease-in-out`;
                    setTimeout(() => {
                        logoImg.style.animation = '';
                    }, displayDuration * 1000);
                }, displayFrequency * 1000);
            }
        }

        // Image Animation
        const categoryImage = document.querySelector('.category-image');
        if (categoryImage) {
            const imageAnim = this.settings.image_animation;
            const imageDelay = this.settings.image_animation_delay || 0;

            if (imageAnim && imageAnim !== 'none') {
                categoryImage.style.animation = `${imageAnim} 1s ease-out ${imageDelay}s both`;
            }

            // Image Display Animation (repeating)
            if (this.settings.image_display_animation_enabled && this.settings.image_display_animation) {
                const displayAnim = this.settings.image_display_animation;
                const displayDuration = this.settings.image_display_animation_duration || 1;
                const displayFrequency = this.settings.image_display_animation_frequency || 5;

                setInterval(() => {
                    categoryImage.style.animation = `${displayAnim} ${displayDuration}s ease-in-out`;
                    setTimeout(() => {
                        categoryImage.style.animation = '';
                    }, displayDuration * 1000);
                }, displayFrequency * 1000);
            }
        }
    }

    applyTicker() {
        const tickerWrapper = document.querySelector('.ticker-wrapper');
        const tickerContent = document.querySelector('.ticker-content');

        if (!tickerWrapper || !tickerContent) return;

        if (this.settings.show_ticker && this.settings.ticker_text) {
            tickerWrapper.style.display = 'block';
            tickerContent.textContent = this.settings.ticker_text;

            // Ticker Styling
            tickerContent.style.fontSize = `${this.settings.ticker_font_size}px`;
            tickerContent.style.color = this.settings.ticker_text_color || '#ffffff';

            if (this.settings.ticker_bg_color) {
                const opacity = this.settings.ticker_bg_opacity || 1;
                const rgb = this.hexToRgb(this.settings.ticker_bg_color);
                tickerWrapper.style.background = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${opacity})`;
            }

            // Ticker Speed
            const speed = this.settings.ticker_speed || 50;
            tickerContent.style.animationDuration = `${speed}s`;

            // Ticker Entrance Animation
            const tickerEntrance = this.settings.ticker_entrance || 'slideInBottom';
            const tickerDelay = this.settings.ticker_entrance_delay || 1;
            tickerWrapper.style.animation = `${tickerEntrance} 1s ease-out ${tickerDelay}s both`;
        } else {
            tickerWrapper.style.display = 'none';
        }
    }

    initializeSecondaryRotation() {
        if (this.secondaryInterval) {
            clearInterval(this.secondaryInterval);
        }

        if (!this.settings.secondary_rotation_enabled || !this.settings.secondary_phrases || this.settings.secondary_phrases.length === 0) {
            return;
        }

        const secondaryText = document.querySelector('.secondary-text');
        if (!secondaryText) return;

        const phrases = this.settings.secondary_phrases;
        const displayDuration = (this.settings.secondary_display_duration || 3) * 1000;
        const transitionType = this.settings.secondary_transition_type || 'fade';
        const transitionDuration = (this.settings.secondary_transition_duration || 0.5) * 1000;

        this.secondaryInterval = setInterval(() => {
            this.secondaryPhraseIndex = (this.secondaryPhraseIndex + 1) % phrases.length;

            // Apply transition animation
            secondaryText.style.animation = `${transitionType}Transition ${transitionDuration / 1000}s ease-in-out`;

            setTimeout(() => {
                secondaryText.textContent = phrases[this.secondaryPhraseIndex];
                secondaryText.style.animation = '';
            }, transitionDuration / 2);
        }, displayDuration + transitionDuration);
    }

    initializeAnimations() {
        // Trigger entrance animations on load
        setTimeout(() => {
            const container = document.querySelector('.overlay-container');
            if (container) {
                container.style.opacity = '1';
            }
        }, 100);
    }

    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : { r: 0, g: 0, b: 0 };
    }

    destroy() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        if (this.secondaryInterval) {
            clearInterval(this.secondaryInterval);
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const categoryMeta = document.querySelector('meta[name="category"]');
    if (categoryMeta) {
        const category = categoryMeta.content;
        window.overlayController = new OverlayController(category);
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.overlayController) {
        window.overlayController.destroy();
    }
});