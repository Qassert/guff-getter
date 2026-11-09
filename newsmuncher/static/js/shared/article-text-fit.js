(function (root) {
    'use strict';
    const DEFAULT_MIN_PX = 8; // 6pt at the CSS reference resolution of 96dpi.
    const DEFAULT_MAX_PX = 60;

    class ArticleTextFitter {
        constructor({element, container = element?.parentElement,
                     minPx = DEFAULT_MIN_PX, maxPx = DEFAULT_MAX_PX,
                     lineHeight = 1.35, precision = .25,
                     raf = callback => requestAnimationFrame(callback),
                     cancelRaf = frame => cancelAnimationFrame(frame),
                     resizeTarget = root,
                     ResizeObserverClass = root.ResizeObserver,
                     fonts = root.document?.fonts} = {}) {
            if (!element) throw new TypeError('Article text element is required.');
            Object.assign(this, {element, container: container || element,
                minPx, maxPx, lineHeight, precision,
                raf, cancelRaf, resizeTarget, ResizeObserverClass, fonts});
            this.onResize = () => this.schedule();
            this.resizeTarget?.addEventListener?.('resize', this.onResize, {passive: true});
            if (ResizeObserverClass) {
                this.observer = new ResizeObserverClass(() => this.schedule());
                this.observer.observe(this.container);
            }
            Promise.resolve(fonts?.ready).then(() => {
                if (!this.destroyed) this.schedule();
            }).catch(() => {});
        }
        observe(element) {
            if (element && element !== this.element) this.observer?.observe(element);
            return this;
        }
        schedule() {
            if (this.destroyed || this.frame) return;
            this.frame = this.raf(() => {
                this.frame = null;
                this.fit();
            });
        }
        availableSize() {
            const style = root.getComputedStyle?.(this.container);
            const horizontal = (parseFloat(style?.paddingLeft) || 0) +
                (parseFloat(style?.paddingRight) || 0);
            const vertical = (parseFloat(style?.paddingTop) || 0) +
                (parseFloat(style?.paddingBottom) || 0);
            return {
                width: Math.max(0, this.container.clientWidth - horizontal),
                height: Math.max(0, this.container.clientHeight - vertical)
            };
        }
        fits(available) {
            return this.element.scrollHeight <= available.height + 1 &&
                this.element.scrollWidth <= available.width + 1;
        }
        fit() {
            const element = this.element;
            const available = this.availableSize();
            if (this.destroyed || !available.width || !available.height) return null;
            element.style.width = '100%';
            element.style.height = 'auto';
            element.style.lineHeight = String(this.lineHeight);
            element.style.overflowX = 'hidden';
            element.style.overflowY = 'hidden';
            element.style.fontSize = `${this.maxPx}px`;
            if (this.fits(available)) {
                element.style.height = `${Math.min(element.scrollHeight, available.height)}px`;
                delete element.dataset.textFitOverflow;
                return this.maxPx;
            }
            element.style.fontSize = `${this.minPx}px`;
            if (!this.fits(available)) {
                element.style.height = `${available.height}px`;
                element.style.overflowY = 'auto';
                element.dataset.textFitOverflow = 'true';
                return this.minPx;
            }
            let low = this.minPx, high = this.maxPx, best = this.minPx;
            for (let step = 0; step < 12 && high - low > this.precision; step++) {
                const candidate = (low + high) / 2;
                element.style.fontSize = `${candidate}px`;
                if (this.fits(available)) { best = candidate; low = candidate; }
                else high = candidate;
            }
            element.style.fontSize = `${Math.min(this.maxPx, Math.max(this.minPx, best)).toFixed(2)}px`;
            element.style.overflowY = 'hidden';
            element.style.height = `${Math.min(element.scrollHeight, available.height)}px`;
            delete element.dataset.textFitOverflow;
            return Number.parseFloat(element.style.fontSize);
        }
        disconnect() {
            this.destroyed = true;
            if (this.frame) this.cancelRaf(this.frame);
            this.frame = null;
            this.observer?.disconnect();
            this.resizeTarget?.removeEventListener?.('resize', this.onResize);
        }
    }

    root.ArticleTextFitter = ArticleTextFitter;
    if (typeof module !== 'undefined') module.exports = {
        ArticleTextFitter, DEFAULT_MIN_PX, DEFAULT_MAX_PX
    };
})(typeof globalThis !== 'undefined' ? globalThis : this);
