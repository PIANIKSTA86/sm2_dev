// Barcode scanning functionality
// Supports various barcode input methods including camera and keyboard wedge scanners

class BarcodeScanner {
    constructor() {
        this.isScanning = false;
        this.scanBuffer = '';
        this.scanTimeout = null;
        this.lastKeyTime = 0;
        this.keySequence = [];
        this.stream = null;
        this.video = null;
        this.canvas = null;
        
        this.init();
    }
    
    init() {
        this.setupKeyboardScanner();
        this.setupEventListeners();
        console.log('Barcode Scanner initialized');
    }
    
    setupKeyboardScanner() {
        // Listen for rapid keyboard input (typical of barcode scanners)
        $(document).on('keypress', (e) => {
            const currentTime = Date.now();
            const timeDiff = currentTime - this.lastKeyTime;
            
            // If time between keystrokes is very short (< 20ms), likely a scanner
            if (timeDiff < 20 && timeDiff > 0) {
                this.keySequence.push(e.key);
                
                // Clear existing timeout
                if (this.scanTimeout) {
                    clearTimeout(this.scanTimeout);
                }
                
                // Set timeout to process the sequence
                this.scanTimeout = setTimeout(() => {
                    this.processBarcodeSequence();
                }, 50);
            } else if (timeDiff > 100) {
                // Reset sequence if too much time has passed
                this.keySequence = [e.key];
            } else {
                this.keySequence.push(e.key);
            }
            
            this.lastKeyTime = currentTime;
            
            // Handle Enter key from scanner
            if (e.which === 13 && this.keySequence.length > 3) {
                e.preventDefault();
                this.processBarcodeSequence();
            }
        });
    }
    
    processBarcodeSequence() {
        if (this.keySequence.length >= 4) { // Minimum barcode length
            const barcode = this.keySequence.join('').replace(/[\r\n]/g, '');
            
            if (this.isValidBarcode(barcode)) {
                this.handleBarcodeScanned(barcode);
            }
        }
        
        this.keySequence = [];
    }
    
    setupEventListeners() {
        // Manual barcode input button
        $(document).on('click', '[data-action="scan-barcode"]', () => {
            this.showBarcodeInput();
        });
        
        // Camera scanner button
        $(document).on('click', '[data-action="camera-scanner"]', () => {
            this.startCameraScanner();
        });
        
        // Manual barcode form submission
        $(document).on('submit', '#manualBarcodeForm', (e) => {
            e.preventDefault();
            const barcode = $('#manual_barcode').val().trim();
            if (barcode) {
                this.handleBarcodeScanned(barcode);
                $('#manualBarcodeModal').modal('hide');
            }
        });
    }
    
    isValidBarcode(barcode) {
        // Basic barcode validation
        if (!barcode || barcode.length < 4) return false;
        
        // Check for common barcode patterns
        const patterns = [
            /^\d{8}$/,      // EAN-8
            /^\d{12}$/,     // UPC-A
            /^\d{13}$/,     // EAN-13
            /^[0-9A-Z\-\.\ \$\/\+\%]{1,}$/ // Code 39
        ];
        
        return patterns.some(pattern => pattern.test(barcode));
    }
    
    handleBarcodeScanned(barcode) {
        console.log('Barcode scanned:', barcode);
        
        // Emit custom event
        $(document).trigger('barcode:scanned', { barcode: barcode });
        
        // Handle based on current page context
        if (window.posSystem) {
            // POS context
            $('#product_search').val(barcode);
            window.posSystem.handleBarcodeInput(barcode);
        } else if ($('#product_search').length) {
            // Inventory search context
            $('#product_search').val(barcode).trigger('input');
        } else if ($('#barcode').length) {
            // Product form context
            $('#barcode').val(barcode);
        } else {
            // Generic search
            const searchInput = $('input[type="search"], input[name="search"]').first();
            if (searchInput.length) {
                searchInput.val(barcode).trigger('input');
            }
        }
        
        // Show success feedback
        this.showScanFeedback(barcode);
    }
    
    showScanFeedback(barcode) {
        // Visual feedback for successful scan
        const feedback = $(`
            <div class="scan-feedback position-fixed top-50 start-50 translate-middle">
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    <i class="fas fa-barcode me-2"></i>
                    Código escaneado: <strong>${barcode}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            </div>
        `);
        
        $('body').append(feedback);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            feedback.remove();
        }, 3000);
        
        // Audio feedback
        this.playBeep();
    }
    
    showBarcodeInput() {
        const modal = $(`
            <div class="modal fade" id="manualBarcodeModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-barcode me-2"></i>Escanear Código de Barras
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <form id="manualBarcodeForm">
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="manual_barcode" class="form-label">Código de Barras</label>
                                    <input type="text" class="form-control form-control-lg" id="manual_barcode" 
                                           placeholder="Escanee o escriba el código..." required autofocus>
                                    <div class="form-text">
                                        Use un escáner de código de barras o escriba el código manualmente
                                    </div>
                                </div>
                                
                                <div class="d-flex gap-2">
                                    <button type="button" class="btn btn-outline-primary flex-fill" 
                                            data-action="camera-scanner">
                                        <i class="fas fa-camera me-2"></i>Usar Cámara
                                    </button>
                                    <button type="button" class="btn btn-outline-info flex-fill" 
                                            onclick="generateSampleBarcode()">
                                        <i class="fas fa-magic me-2"></i>Generar Muestra
                                    </button>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                    Cancelar
                                </button>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-check me-2"></i>Procesar
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(modal);
        modal.modal('show');
        
        // Clean up when modal is hidden
        modal.on('hidden.bs.modal', function() {
            modal.remove();
        });
        
        // Focus the input when modal is shown
        modal.on('shown.bs.modal', function() {
            $('#manual_barcode').focus();
        });
    }
    
    startCameraScanner() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            InventorySystem.showNotification('Cámara no disponible en este dispositivo', 'error');
            return;
        }
        
        this.showCameraModal();
    }
    
    showCameraModal() {
        const modal = $(`
            <div class="modal fade" id="cameraScannerModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-camera me-2"></i>Escáner de Cámara
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <div id="camera-container" class="position-relative">
                                <video id="barcode-video" width="100%" height="400" autoplay muted></video>
                                <canvas id="barcode-canvas" style="display: none;"></canvas>
                                
                                <!-- Scanning overlay -->
                                <div class="scanner-overlay position-absolute top-50 start-50 translate-middle">
                                    <div class="scanner-line"></div>
                                    <div class="scanner-corner scanner-corner-tl"></div>
                                    <div class="scanner-corner scanner-corner-tr"></div>
                                    <div class="scanner-corner scanner-corner-bl"></div>
                                    <div class="scanner-corner scanner-corner-br"></div>
                                </div>
                            </div>
                            
                            <div class="mt-3">
                                <p class="text-muted">Posicione el código de barras dentro del área de escaneo</p>
                                <button type="button" class="btn btn-success" id="capture-barcode">
                                    <i class="fas fa-camera me-2"></i>Capturar
                                </button>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                Cerrar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `);
        
        $('body').append(modal);
        modal.modal('show');
        
        // Initialize camera when modal is shown
        modal.on('shown.bs.modal', () => {
            this.initializeCamera();
        });
        
        // Clean up when modal is hidden
        modal.on('hidden.bs.modal', () => {
            this.stopCamera();
            modal.remove();
        });
        
        // Capture button handler
        $(document).on('click', '#capture-barcode', () => {
            this.captureBarcode();
        });
    }
    
    async initializeCamera() {
        try {
            this.video = document.getElementById('barcode-video');
            this.canvas = document.getElementById('barcode-canvas');
            
            const constraints = {
                video: {
                    facingMode: 'environment', // Use back camera
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            // Set canvas dimensions
            this.video.addEventListener('loadedmetadata', () => {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
            });
            
        } catch (error) {
            console.error('Camera initialization error:', error);
            InventorySystem.showNotification('Error al acceder a la cámara', 'error');
        }
    }
    
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }
    
    captureBarcode() {
        if (!this.video || !this.canvas) return;
        
        const context = this.canvas.getContext('2d');
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        // For a real implementation, you would use a barcode detection library
        // like QuaggaJS or ZXing-js here to decode the barcode from the canvas
        
        // Simulated barcode detection
        this.simulateBarcodeDetection();
    }
    
    simulateBarcodeDetection() {
        // This is a placeholder - in a real implementation, you would use
        // a proper barcode detection library
        const sampleBarcodes = [
            '1234567890123',
            '9876543210987',
            '4567890123456',
            '7890123456789'
        ];
        
        const detectedBarcode = sampleBarcodes[Math.floor(Math.random() * sampleBarcodes.length)];
        
        setTimeout(() => {
            this.handleBarcodeScanned(detectedBarcode);
            $('#cameraScannerModal').modal('hide');
        }, 1000);
    }
    
    playBeep() {
        // Play a beep sound for scan feedback
        if (window.AudioContext || window.webkitAudioContext) {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 1000;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
        }
    }
    
    generateBarcode(text, type = 'ean13') {
        // Basic barcode generation for testing
        // In a real implementation, use a library like JsBarcode
        
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = 200;
        canvas.height = 50;
        
        // Simple representation
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = '#fff';
        for (let i = 0; i < text.length; i++) {
            const x = (i * canvas.width) / text.length;
            const width = canvas.width / text.length;
            
            if (parseInt(text[i]) % 2 === 0) {
                ctx.fillRect(x, 0, width, canvas.height);
            }
        }
        
        return canvas.toDataURL();
    }
}

// Global functions for HTML onclick handlers
function scanBarcode() {
    if (window.barcodeScanner) {
        window.barcodeScanner.showBarcodeInput();
    }
}

function generateSampleBarcode() {
    const samples = [
        '1234567890123',
        '9876543210987',
        '4567890123456',
        '7890123456789'
    ];
    
    const sample = samples[Math.floor(Math.random() * samples.length)];
    $('#manual_barcode').val(sample);
}

// CSS styles for scanner overlay
const scannerStyles = `
<style>
.scanner-overlay {
    width: 300px;
    height: 200px;
    border: 2px solid #ff0000;
    pointer-events: none;
}

.scanner-line {
    position: absolute;
    top: 50%;
    left: 0;
    right: 0;
    height: 2px;
    background: #ff0000;
    animation: scanLine 2s linear infinite;
}

@keyframes scanLine {
    0% { top: 10%; }
    50% { top: 90%; }
    100% { top: 10%; }
}

.scanner-corner {
    position: absolute;
    width: 20px;
    height: 20px;
    border: 3px solid #00ff00;
}

.scanner-corner-tl {
    top: -2px;
    left: -2px;
    border-right: none;
    border-bottom: none;
}

.scanner-corner-tr {
    top: -2px;
    right: -2px;
    border-left: none;
    border-bottom: none;
}

.scanner-corner-bl {
    bottom: -2px;
    left: -2px;
    border-right: none;
    border-top: none;
}

.scanner-corner-br {
    bottom: -2px;
    right: -2px;
    border-left: none;
    border-top: none;
}

.scan-feedback {
    z-index: 9999;
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from {
        transform: translate(-50%, -60%);
        opacity: 0;
    }
    to {
        transform: translate(-50%, -50%);
        opacity: 1;
    }
}
</style>
`;

// Add scanner styles to head
$(document).ready(function() {
    $('head').append(scannerStyles);
    
    // Initialize barcode scanner
    window.barcodeScanner = new BarcodeScanner();
    console.log('Barcode Scanner loaded successfully');
    
    // Set up global keyboard scanner detection
    let barcodeBuffer = '';
    let lastBarcodeTime = 0;
    
    $(document).on('keydown', function(e) {
        const currentTime = Date.now();
        
        // Reset buffer if too much time has passed
        if (currentTime - lastBarcodeTime > 100) {
            barcodeBuffer = '';
        }
        
        lastBarcodeTime = currentTime;
        
        // Add character to buffer
        if (e.key.length === 1) {
            barcodeBuffer += e.key;
        }
        
        // Process on Enter
        if (e.key === 'Enter' && barcodeBuffer.length >= 8) {
            e.preventDefault();
            if (window.barcodeScanner) {
                window.barcodeScanner.handleBarcodeScanned(barcodeBuffer);
            }
            barcodeBuffer = '';
        }
    });
});
