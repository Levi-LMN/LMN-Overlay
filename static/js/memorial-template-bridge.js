(function () {
    const category = 'funeral';
    const root = document.querySelector('.lt, .lower-third');
    let current = window.MEMORIAL_SETTINGS || {};
    let lastPayload = '';
    let cycleTimer = null;
    let cycleSignature = '';
    let tickerObserver = null;
    let chromeState = {logo: false, live: false};

    function setVar(name, value) {
        if (value) document.documentElement.style.setProperty(name, value);
    }

    function applyPalette(s) {
        const background = s.overlay_bg_color || '#171A18';
        const dark = s.ticker_bg_color || background;
        const accent = s.accent_color || s.border_color || '#D8B875';
        const accentSoft = s.secondary_text_color || accent;
        const text = s.main_text_color || '#FFFFFF';
        const muted = s.ticker_text_color || text;

        ['--ink', '--forest-a', '--wine-a', '--night-a', '--bar-a'].forEach(v => setVar(v, background));
        ['--forest-b', '--wine-b', '--night-b', '--bar-b'].forEach(v => setVar(v, dark));
        ['--rose', '--sage', '--silver', '--steel', '--bronze'].forEach(v => setVar(v, accent));
        ['--rose-dk', '--sage-dk', '--silver-dk', '--steel-dk', '--bronze-dk'].forEach(v => setVar(v, accentSoft));
        ['--rose-lt', '--silver-lt', '--bronze-lt'].forEach(v => setVar(v, text));
        ['--pearl', '--ivory'].forEach(v => setVar(v, text));
        ['--pearl-dim', '--ivory-dim'].forEach(v => setVar(v, muted));
        setVar('--time', accentSoft);
    }

    function applyText(s) {
        const name = document.getElementById('subjectName');
        const kicker = document.getElementById('kickerLabel');
        const portrait = document.getElementById('portrait') || document.querySelector('.circle img');
        const nameText = s.main_text || '';
        const kickerText = s.secondary_text || '';

        const templateLabel = document.getElementById('infoLabel');
        if (templateLabel) templateLabel.style.display = 'none';
        document.querySelectorAll('.info-head .counter, .info-head + .track').forEach(el => {
            el.style.display = 'none';
        });

        if (name) {
            name.textContent = nameText;
            name.title = nameText;
            name.style.fontSize = '';
            name.style.lineHeight = '';
            name.style.overflow = 'hidden';
            name.style.textOverflow = 'clip';
            requestAnimationFrame(() => {
                const availableWidth = name.clientWidth || (name.parentElement && name.parentElement.clientWidth) || 0;
                const preferredSize = parseFloat(getComputedStyle(name).fontSize) || 32;
                const minimumSize = 16;
                let fontSize = preferredSize;

                name.style.display = 'block';
                name.style.whiteSpace = 'nowrap';
                name.style.webkitBoxOrient = '';
                name.style.webkitLineClamp = '';

                while (availableWidth && name.scrollWidth > availableWidth && fontSize > minimumSize) {
                    fontSize -= 1;
                    name.style.fontSize = fontSize + 'px';
                }

                if (availableWidth && name.scrollWidth > availableWidth) {
                    // A memorial name should remain readable as a whole. Use a compact,
                    // static second line before falling back to a final ellipsis.
                    fontSize = Math.min(preferredSize, 22);
                    name.style.fontSize = fontSize + 'px';
                    name.style.whiteSpace = 'normal';
                    name.style.lineHeight = '1.05';
                    name.style.display = '-webkit-box';
                    name.style.webkitBoxOrient = 'vertical';

                    const exceedsTwoLines = () => name.scrollHeight > fontSize * 2.2;
                    while (exceedsTwoLines() && fontSize > minimumSize) {
                        fontSize -= 1;
                        name.style.fontSize = fontSize + 'px';
                    }

                    name.style.webkitLineClamp = '2';
                    name.style.textOverflow = exceedsTwoLines() ? 'ellipsis' : 'clip';
                }
            });
        }
        if (kicker) {
            kicker.textContent = kickerText;
            kicker.title = kickerText;
            kicker.style.overflow = 'hidden';
            kicker.style.textOverflow = 'ellipsis';
            kicker.style.whiteSpace = 'nowrap';
        }
        if (portrait) {
            if (s.show_category_image && s.category_image) {
                const desiredSrc = new URL(`/static/${s.category_image}`, window.location.origin).href;
                portrait.style.visibility = 'hidden';
                portrait.onload = () => {
                    if (portrait.src === desiredSrc) portrait.style.visibility = '';
                };
                portrait.onerror = () => { portrait.style.visibility = 'hidden'; };
                if (portrait.src !== desiredSrc) portrait.src = desiredSrc;
                if (portrait.complete && portrait.naturalWidth && portrait.src === desiredSrc) {
                    portrait.style.visibility = '';
                }
                portrait.style.objectPosition = s.image_object_position || 'center center';
            } else {
                portrait.style.visibility = 'hidden';
            }
        }

        const phrases = (s.secondary_phrases || []).filter(Boolean);
        if (!phrases.length && s.secondary_text) phrases.push(s.secondary_text);
        if (!phrases.length) phrases.push('');
        const slides = document.querySelectorAll('#slideStage .slide');
        const slideStage = document.getElementById('slideStage');
        const secondaryVisible = s.show_secondary_text !== false && phrases.some(phrase => phrase.trim());
        applySecondaryLayout(secondaryVisible);
        slides.forEach((slide, index) => {
            slide.classList.remove('info', 'info-type', 'tribute', 'meta');
            const lineA = slide.querySelector('.line-a');
            const lineB = slide.querySelector('.line-b');
            if (lineA) {
                lineA.textContent = phrases[index % phrases.length];
                lineA.title = lineA.textContent;
                lineA.style.overflow = 'hidden';
                lineA.style.textOverflow = 'clip';
                lineA.style.whiteSpace = 'normal';
                lineA.style.display = '-webkit-box';
                lineA.style.webkitBoxOrient = 'vertical';
                lineA.style.webkitLineClamp = '2';
                lineA.style.lineHeight = '1.15';
                lineA.style.fontSize = '22px';
                requestAnimationFrame(() => fitRemembranceText(lineA));
            }
            if (lineB) lineB.style.display = 'none';
        });

        const years = document.getElementById('years');
        const watermark = document.getElementById('watermark');
        if (years) {
            years.textContent = s.company_name || '';
            years.style.display = s.show_company_name === false ? 'none' : '';
        }

        const timeLabel = document.getElementById('timeLabel');
        if (timeLabel && timeLabel.parentElement) {
            timeLabel.parentElement.style.display = s.show_clock === false ? 'none' : '';
        }
        if (watermark) {
            watermark.textContent = s.company_name || '';
            watermark.style.display = s.show_company_name === false ? 'none' : '';
        }

        const ticker = s.ticker_text || phrases.join('  •  ');
        const tickerTrack = document.getElementById('tickerTrack');
        if (tickerTrack) {
            const tickerWrap = tickerTrack.closest('.ticker-wrap');
            if (tickerWrap) tickerWrap.style.display = s.show_ticker === false ? 'none' : '';
            tickerTrack.dataset.liveTicker = ticker;
            syncTicker(tickerTrack);
            if (!tickerObserver && tickerTrack.nodeType === Node.ELEMENT_NODE && tickerTrack.isConnected) {
                tickerObserver = new MutationObserver(() => syncTicker(tickerTrack));
                tickerObserver.observe(tickerTrack, {childList: true});
            }
        }
    }

    function fitRemembranceText(line) {
        const container = line.closest('.slide');
        if (!container || !container.clientHeight) return;
        let size = 22;
        line.style.webkitLineClamp = '';
        while ((line.scrollHeight > container.clientHeight || line.scrollWidth > container.clientWidth) && size > 16) {
            size -= 1;
            line.style.fontSize = size + 'px';
        }
        line.style.webkitLineClamp = '2';
        line.style.textOverflow = line.scrollHeight > container.clientHeight ? 'ellipsis' : 'clip';
    }

    function applySecondaryLayout(visible) {
        if (!root) return;
        root.classList.toggle('secondary-hidden', !visible);
        root.classList.toggle('secondary-visible', visible);
        const show = (selector, enabled = visible) => {
            const element = root.querySelector(selector);
            if (element) element.style.display = enabled ? '' : 'none';
            return element;
        };

        switch (window.MEMORIAL_VARIANT) {
        case 'band': {
            show('.info');
            show('.vr');
            const id = root.querySelector('.id');
            const background = root.querySelector('.band-bg');
            const strap = root.querySelector('.strap');
            if (id) id.style.right = visible ? '' : '42px';
            if (background) background.style.right = visible ? '' : '0';
            if (strap) strap.style.right = visible ? '' : '0';
            break;
        }
        case 'cameo': {
            show('.slot');
            show('.rule');
            const content = root.querySelector('.content');
            if (content) {
                content.style.display = visible ? '' : 'flex';
                content.style.flexDirection = visible ? '' : 'column';
                content.style.justifyContent = visible ? '' : 'center';
                content.style.paddingTop = visible ? '' : '0';
                content.style.paddingBottom = visible ? '' : '0';
            }
            break;
        }
        case 'plate': {
            show('.slot-zone');
            const panelFx = root.querySelector('.panel-fx');
            if (panelFx) panelFx.style.height = visible ? '' : '116px';
            break;
        }
        case 'arch': {
            show('.slot-wrap');
            const panel = root.querySelector('.panel');
            if (panel) panel.style.height = visible ? '' : '148px';
            break;
        }
        case 'classic':
            show('.bar-sub');
            break;
        default:
            show('#slideStage');
        }
    }

    function applyChrome(s) {
        if (!document.getElementById('memorialChromeStyles')) {
            const style = document.createElement('style');
            style.id = 'memorialChromeStyles';
            style.textContent = `
                .memorial-brand-logo{position:fixed;top:28px;z-index:100;width:auto;max-width:180px;height:auto;max-height:72px;object-fit:contain;filter:drop-shadow(0 3px 8px rgba(0,0,0,.28));transition:opacity .35s ease;transform-style:preserve-3d;backface-visibility:visible}
                .memorial-live-badge{position:fixed;top:30px;z-index:100;display:flex;align-items:center;gap:9px;padding:7px 11px;border-radius:4px;background:rgba(10,12,11,.78);color:#fff;font:600 13px/1.2 Arial,sans-serif;letter-spacing:.2px;box-shadow:0 3px 10px rgba(0,0,0,.22);transition:opacity .35s ease}
                .memorial-live-badge i{display:block;width:8px;height:8px;border-radius:50%;background:#e11d48;box-shadow:0 0 0 4px rgba(225,29,72,.18)}
                .memorial-live-badge strong{font-size:11px;letter-spacing:1.4px}
                .memorial-live-badge span:empty{display:none}
                @keyframes memorialLogoFade{from{opacity:0}to{opacity:1}}
                @keyframes memorialLogoLeft{from{opacity:0;transform:translateX(-70px)}to{opacity:1;transform:none}}
                @keyframes memorialLogoRight{from{opacity:0;transform:translateX(70px)}to{opacity:1;transform:none}}
                @keyframes memorialLogoScale{from{opacity:0;transform:scale(.55)}to{opacity:1;transform:scale(1)}}
                @keyframes memorialLogoZoom{from{opacity:0;transform:scale(1.35)}to{opacity:1;transform:scale(1)}}
                @keyframes memorialLogoRotate{0%{transform:perspective(700px) rotateY(0)}33%{transform:perspective(700px) rotateY(360deg)}100%{transform:perspective(700px) rotateY(360deg)}}
                @keyframes memorialBadgePulse{50%{transform:scale(1.04)}}
                @keyframes memorialBadgeGlow{50%{box-shadow:0 3px 18px rgba(225,29,72,.58)}}
                @keyframes memorialBadgeFloat{50%{transform:translateY(-5px)}}
                @keyframes memorialBadgeBounce{40%{transform:translateY(-7px)}60%{transform:translateY(-3px)}}
            `;
            document.head.appendChild(style);
        }

        let logo = document.getElementById('memorialBrandLogo');
        if (!logo) {
            logo = document.createElement('img');
            logo.id = 'memorialBrandLogo';
            logo.className = 'memorial-brand-logo';
            logo.alt = 'Company logo';
            document.body.appendChild(logo);
        }
        chromeState.logo = Boolean(s.show_company_logo && s.company_logo);
        logo.style.left = s.logo_horizontal_position === 'left' ? '36px' : 'auto';
        logo.style.right = s.logo_horizontal_position === 'left' ? 'auto' : '36px';
        if (chromeState.logo) {
            const logoSrc = new URL(`/static/${s.company_logo}`, location.origin).href;
            logo.style.visibility = 'hidden';
            logo.onload = () => { if (logo.src === logoSrc) logo.style.visibility = ''; };
            if (logo.src !== logoSrc) logo.src = logoSrc;
            if (logo.complete && logo.naturalWidth) logo.style.visibility = '';
        } else {
            logo.style.visibility = 'hidden';
        }
        const logoAnimations = {
            'fade-in': 'memorialLogoFade 1s ease both',
            'scale-in': 'memorialLogoScale 1.2s cubic-bezier(.2,.8,.2,1) both',
            'zoom-in': 'memorialLogoZoom 1.2s cubic-bezier(.2,.8,.2,1) both',
            'slide-in-left': 'memorialLogoLeft .9s ease both',
            'slide-in-right': 'memorialLogoRight .9s ease both',
            'rotate-in': 'memorialLogoRotate 12s cubic-bezier(.2,.72,.25,1) infinite'
        };
        logo.style.animation = logoAnimations[s.logo_animation] || 'none';

        let badge = document.getElementById('memorialLiveBadge');
        if (!badge) {
            badge = document.createElement('div');
            badge.id = 'memorialLiveBadge';
            badge.className = 'memorial-live-badge';
            badge.innerHTML = '<i></i><strong></strong><span></span>';
            document.body.appendChild(badge);
        }
        chromeState.live = Boolean(s.show_live_indicator);
        badge.querySelector('strong').textContent = s.live_label || 'LIVE';
        badge.querySelector('span').textContent = s.live_location || '';
        badge.style.left = s.live_indicator_horizontal_position === 'right' ? 'auto' : '36px';
        badge.style.right = s.live_indicator_horizontal_position === 'right' ? '36px' : 'auto';
        const sameCorner = (s.logo_horizontal_position === 'left' ? 'left' : 'right') ===
            (s.live_indicator_horizontal_position === 'right' ? 'right' : 'left');
        badge.style.top = chromeState.logo && sameCorner ? '112px' : '30px';
        badge.style.visibility = chromeState.live ? '' : 'hidden';
        const badgeAnimations = {
            pulse: 'memorialBadgePulse 2s ease-in-out infinite',
            glow: 'memorialBadgeGlow 2.2s ease-in-out infinite',
            float: 'memorialBadgeFloat 2.6s ease-in-out infinite',
            bounce: 'memorialBadgeBounce 1.8s ease-in-out infinite'
        };
        badge.style.animation = badgeAnimations[s.live_indicator_animation] || 'none';

        const overlayIsShown = root && root.style.visibility !== 'hidden' && root.style.opacity !== '0';
        logo.style.opacity = overlayIsShown && chromeState.logo ? '1' : '0';
        badge.style.opacity = overlayIsShown && chromeState.live ? '1' : '0';
    }

    function syncTicker(tickerTrack) {
        const ticker = tickerTrack.dataset.liveTicker || '';
        tickerTrack.querySelectorAll(':scope > span').forEach(span => {
            if (span.textContent !== ticker) span.textContent = ticker;
            span.style.color = current.ticker_text_color || '#FFFFFF';
        });
        const tickerWrap = tickerTrack.closest('.ticker-wrap');
        if (tickerWrap) tickerWrap.style.backgroundColor = current.ticker_bg_color || '';
        requestAnimationFrame(() => {
            if (!tickerTrack.isConnected) return;
            tickerTrack.style.setProperty('--shift', Math.max(1, tickerTrack.scrollWidth / 2) + 'px');
            const speed = Math.max(1, Math.min(100, Number(current.ticker_speed || 50)));
            const pixelsPerSecond = 24 + (speed - 1) * (156 / 99);
            tickerTrack.style.animationDuration = Math.max(tickerTrack.scrollWidth / 2 / pixelsPerSecond, 4) + 's';
        });
    }

    function setShown(shown, animate) {
        if (!root) return;
        root.style.transition = animate ? 'opacity .6s ease, visibility .6s ease' : 'none';
        root.style.opacity = shown ? '1' : '0';
        root.style.visibility = shown ? 'visible' : 'hidden';
        const logo = document.getElementById('memorialBrandLogo');
        const badge = document.getElementById('memorialLiveBadge');
        if (logo) logo.style.opacity = shown && chromeState.logo ? '1' : '0';
        if (badge) badge.style.opacity = shown && chromeState.live ? '1' : '0';
    }

    function configureCycle(s) {
        if (window.MEMORIAL_PREVIEW) {
            setShown(true, false);
            return;
        }
        const signature = [s.is_visible, s.overlay_cycle_enabled, s.overlay_visible_duration,
            s.overlay_hidden_duration].join('|');
        if (signature === cycleSignature) return;
        cycleSignature = signature;
        clearTimeout(cycleTimer);
        cycleTimer = null;

        if (!s.is_visible) {
            setShown(false, true);
            return;
        }
        if (!s.overlay_cycle_enabled) {
            setShown(true, true);
            return;
        }

        const visibleMs = Math.max(1000, Number(s.overlay_visible_duration || 10) * 1000);
        const hiddenMs = Math.max(1000, Number(s.overlay_hidden_duration || 900) * 1000);
        function show() {
            setShown(true, true);
            cycleTimer = setTimeout(hide, visibleMs);
        }
        function hide() {
            setShown(false, true);
            cycleTimer = setTimeout(show, hiddenMs);
        }
        show();
    }

    function applySettings(s) {
        const selectedVariant = !s.layout_style || ['default', 'legacy'].includes(s.layout_style)
            ? 'legacy'
            : s.layout_style;
        if (!window.MEMORIAL_PREVIEW && selectedVariant !== window.MEMORIAL_VARIANT) {
            location.reload();
            return;
        }
        applyPalette(s);
        applyText(s);
        applyChrome(s);
        configureCycle(s);
    }

    async function poll() {
        try {
            const response = await fetch(`/api/poll/${category}`);
            const data = await response.json();
            if (!data.settings) return;
            const payload = JSON.stringify(data.settings);
            if (payload !== lastPayload) {
                lastPayload = payload;
                current = data.settings;
                applySettings(current);
            }
        } catch (error) {
            console.warn('Memorial template poll failed', error);
        }
    }

    applySettings(current);
    setInterval(poll, 1000);
    poll();
}());
