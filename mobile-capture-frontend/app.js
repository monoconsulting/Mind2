// Mobile Receipt Capture App
// Implements the user flow from MIND_FUNCTION_DESCRIPTION.md

class ReceiptCaptureApp {
    constructor() {
        this.photos = [];
        this.selectedTags = [];
        this.includeLocation = false;
        this.availableTags = [];
        this.currentStream = null;
        
        this.init();
    }

    init() {
        this.loadAvailableTags();
        this.bindEvents();
        this.showScreen('capture-screen');
    }

    bindEvents() {
        // Camera and Gallery buttons
        document.getElementById('btn-camera').addEventListener('click', () => this.startCamera());
        document.getElementById('btn-gallery').addEventListener('click', () => this.openGallery());
        document.getElementById('file-picker').addEventListener('change', (e) => this.handleFileSelection(e));

        // Photo actions
        document.getElementById('btn-retake').addEventListener('click', () => this.retakePhoto());
        document.getElementById('btn-add-page').addEventListener('click', () => this.addPage());
        document.getElementById('btn-finished').addEventListener('click', () => this.finishedCapturing());

        // Tags and location
        document.getElementById('btn-location-yes').addEventListener('click', () => this.setLocation(true));
        document.getElementById('btn-location-no').addEventListener('click', () => this.setLocation(false));

        // Navigation
        document.getElementById('btn-back').addEventListener('click', () => this.goBack());
        document.getElementById('btn-submit').addEventListener('click', () => this.submitReceipt());
        document.getElementById('btn-new-receipt').addEventListener('click', () => this.startNewReceipt());
    }

    async loadAvailableTags() {
        try {
            const res = await fetch('/ai/api/tags');
            if (res.ok) {
                const items = await res.json();
                this.availableTags = (items || []).map(x => x.name).filter(Boolean);
            }
            if (!this.availableTags || this.availableTags.length === 0) {
                this.availableTags = ['Business', 'Travel', 'Food', 'Office'];
            }
            this.renderTags();
        } catch (error) {
            console.error('Failed to load tags:', error);
            this.availableTags = ['Business', 'Travel', 'Food', 'Office'];
            this.renderTags();
        }
    }

    renderTags() {
        const tagsList = document.getElementById('tags-list');
        tagsList.innerHTML = '';
        
        this.availableTags.forEach(tag => {
            const button = document.createElement('button');
            button.className = 'tag-btn';
            button.textContent = tag;
            button.addEventListener('click', () => this.toggleTag(tag, button));
            tagsList.appendChild(button);
        });
    }

    toggleTag(tag, button) {
        const index = this.selectedTags.indexOf(tag);
        if (index > -1) {
            this.selectedTags.splice(index, 1);
            button.classList.remove('selected');
        } else {
            this.selectedTags.push(tag);
            button.classList.add('selected');
        }
    }

    async startCamera() {
        try {
            if (this.currentStream) {
                this.currentStream.getTracks().forEach(track => track.stop());
            }

            this.currentStream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment' } 
            });
            
            const video = document.getElementById('preview-video');
            video.srcObject = this.currentStream;
            video.style.display = 'block';
            
            // Wait for video to be ready, then capture
            video.addEventListener('loadedmetadata', () => {
                setTimeout(() => this.capturePhoto(), 500);
            });

        } catch (error) {
            alert('Camera not available: ' + error.message);
        }
    }

    openGallery() {
        document.getElementById('file-picker').click();
    }

    handleFileSelection(event) {
        const files = Array.from(event.target.files);
        files.forEach(file => this.addPhotoFromFile(file));
        this.showPhotoActions();
    }

    capturePhoto() {
        const video = document.getElementById('preview-video');
        const canvas = document.getElementById('preview-canvas');
        
        if (video.readyState >= 2) {
            const ctx = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            ctx.drawImage(video, 0, 0);
            
            canvas.toBlob(blob => {
                if (blob) {
                    this.addPhoto(blob);
                    this.showPhotoActions();
                    video.style.display = 'none';
                    this.stopCamera();
                }
            }, 'image/jpeg', 0.92);
        }
    }

    addPhotoFromFile(file) {
        const blob = new Blob([file], { type: file.type || 'image/jpeg' });
        this.addPhoto(blob);
    }

    addPhoto(blob) {
        const photoId = 'photo-' + Date.now();
        const photoData = {
            id: photoId,
            blob: blob,
            url: URL.createObjectURL(blob)
        };
        
        this.photos.push(photoData);
        this.renderPhotoQueue();
    }

    renderPhotoQueue() {
        const queue = document.getElementById('photo-queue');
        queue.innerHTML = '';
        
        this.photos.forEach(photo => {
            const photoDiv = document.createElement('div');
            photoDiv.className = 'photo-item';
            photoDiv.innerHTML = `
                <img src="${photo.url}" alt="Receipt photo">
                <button class="remove-btn" onclick="app.removePhoto('${photo.id}')">×</button>
            `;
            queue.appendChild(photoDiv);
        });
    }

    removePhoto(photoId) {
        const index = this.photos.findIndex(p => p.id === photoId);
        if (index > -1) {
            URL.revokeObjectURL(this.photos[index].url);
            this.photos.splice(index, 1);
            this.renderPhotoQueue();
            
            if (this.photos.length === 0) {
                this.hidePhotoActions();
            }
        }
    }

    showPhotoActions() {
        document.getElementById('photo-actions').style.display = 'flex';
    }

    hidePhotoActions() {
        document.getElementById('photo-actions').style.display = 'none';
    }

    retakePhoto() {
        // Remove last photo and restart camera
        if (this.photos.length > 0) {
            this.removePhoto(this.photos[this.photos.length - 1].id);
        }
        this.startCamera();
    }

    addPage() {
        // Add another photo
        this.startCamera();
    }

    finishedCapturing() {
        if (this.photos.length === 0) {
            alert('Please capture at least one photo');
            return;
        }
        
        this.showScreen('tags-screen');
    }

    setLocation(include) {
        this.includeLocation = include;
        
        // Update button states
        const yesBtn = document.getElementById('btn-location-yes');
        const noBtn = document.getElementById('btn-location-no');
        
        if (include) {
            yesBtn.classList.add('btn-primary');
            yesBtn.classList.remove('btn-secondary');
            noBtn.classList.add('btn-secondary');
            noBtn.classList.remove('btn-primary');
        } else {
            noBtn.classList.add('btn-primary');
            noBtn.classList.remove('btn-secondary');
            yesBtn.classList.add('btn-secondary');
            yesBtn.classList.remove('btn-primary');
        }
    }

    async submitReceipt() {
        if (this.photos.length === 0) {
            alert('No photos to submit');
            return;
        }

        const submitBtn = document.getElementById('btn-submit');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Uploading...';

        try {
            const formData = new FormData();
            
            // Add photos
            this.photos.forEach((photo, index) => {
                formData.append('images', photo.blob, `page-${index + 1}.jpg`);
            });
            
            // Add metadata
            formData.set('tags', JSON.stringify(this.selectedTags));
            
            // Add location if requested
            if (this.includeLocation && navigator.geolocation) {
                try {
                    const position = await this.getCurrentPosition();
                    const locationData = {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        acc: position.coords.accuracy
                    };
                    formData.set('location', JSON.stringify(locationData));
                } catch (error) {
                    console.warn('Could not get location:', error);
                }
            }

            // Submit to API
            const response = await fetch('/ai/api/capture/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Upload successful:', result);
                this.showScreen('success-screen');
            } else {
                throw new Error(`Upload failed: ${response.status}`);
            }

        } catch (error) {
            console.error('Upload error:', error);
            alert('Upload failed: ' + error.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Receipt';
        }
    }

    getCurrentPosition() {
        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: false,
                timeout: 5000,
                maximumAge: 300000
            });
        });
    }

    goBack() {
        this.showScreen('capture-screen');
    }

    startNewReceipt() {
        // Reset state
        this.photos.forEach(photo => URL.revokeObjectURL(photo.url));
        this.photos = [];
        this.selectedTags = [];
        this.includeLocation = false;
        
        // Reset UI
        this.renderPhotoQueue();
        this.hidePhotoActions();
        this.renderTags();
        this.setLocation(false);
        
        this.showScreen('capture-screen');
    }

    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        document.getElementById(screenId).classList.add('active');
    }

    stopCamera() {
        if (this.currentStream) {
            this.currentStream.getTracks().forEach(track => track.stop());
            this.currentStream = null;
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ReceiptCaptureApp();
});
