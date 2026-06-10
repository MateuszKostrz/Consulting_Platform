/**
 * Universal Image Lightbox
 * Automatically adds lightbox functionality to images in question content
 */

class ImageLightbox {
    constructor() {
        this.overlay = null;
        this.container = null;
        this.image = null;
        this.closeBtn = null;
        this.loading = null;
        this.isOpen = false;
        
        this.init();
    }
    
    init() {
        this.createLightboxHTML();
        this.bindEvents();
        this.makeImagesClickable();
    }
    
    createLightboxHTML() {
        // Create lightbox overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'lightbox-overlay';
        this.overlay.innerHTML = `
            <div class="lightbox-container">
                <button class="lightbox-close" title="Close (ESC)"><span>&times;</span></button>
                <div class="lightbox-loading"></div>
                <img class="lightbox-image" alt="Enlarged image" style="display: none;">
            </div>
        `;
        
        document.body.appendChild(this.overlay);
        
        // Get references to elements
        this.container = this.overlay.querySelector('.lightbox-container');
        this.image = this.overlay.querySelector('.lightbox-image');
        this.closeBtn = this.overlay.querySelector('.lightbox-close');
        this.loading = this.overlay.querySelector('.lightbox-loading');
    }
    
    bindEvents() {
        // Close button
        this.closeBtn.addEventListener('click', () => this.close());
        
        // Click overlay background to close
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.close();
            }
        });
        
        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
        
        // Prevent body scroll when lightbox is open
        this.overlay.addEventListener('wheel', (e) => {
            e.preventDefault();
        }, { passive: false });
    }
    
    makeImagesClickable() {
        // Find all images in question content
        const imageSelectors = [
            '.question-text img',
            '.answer-content img',
            '.qb-question img',
            '.question img'
        ];
        
        imageSelectors.forEach(selector => {
            const images = document.querySelectorAll(selector);
            images.forEach(img => {
                // Skip if already processed
                if (img.classList.contains('lightbox-enabled')) return;
                
                img.classList.add('lightbox-enabled');
                img.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.open(img.src, img.alt);
                });
                
                // Add title for better UX
                if (!img.title) {
                    img.title = 'Click to enlarge';
                }
            });
        });
    }
    
    open(imageSrc, imageAlt = '') {
        if (this.isOpen) return;
        
        this.isOpen = true;
        this.overlay.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent background scroll
        
        // Show loading spinner
        this.loading.style.display = 'block';
        this.image.style.display = 'none';
        
        // Load image
        const tempImg = new Image();
        tempImg.onload = () => {
            this.image.src = imageSrc;
            this.image.alt = imageAlt;
            this.loading.style.display = 'none';
            this.image.style.display = 'block';
        };
        
        tempImg.onerror = () => {
            this.loading.style.display = 'none';
            this.image.style.display = 'block';
            this.image.src = imageSrc; // Still try to show it
            this.image.alt = imageAlt || 'Image could not be loaded';
        };
        
        tempImg.src = imageSrc;
    }
    
    close() {
        if (!this.isOpen) return;
        
        this.isOpen = false;
        this.overlay.classList.remove('active');
        document.body.style.overflow = ''; // Restore scroll
        
        // Clear image after animation
        setTimeout(() => {
            this.image.src = '';
            this.image.alt = '';
        }, 300);
    }
    
    // Method to refresh clickable images (useful for dynamically loaded content)
    refresh() {
        this.makeImagesClickable();
    }
}

// Initialize lightbox when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.imageLightbox = new ImageLightbox();
});

// Also refresh when new content is loaded (for AJAX content)
document.addEventListener('contentLoaded', () => {
    if (window.imageLightbox) {
        window.imageLightbox.refresh();
    }
});

// Export for potential module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ImageLightbox;
}
