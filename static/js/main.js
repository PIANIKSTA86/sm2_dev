// Main JavaScript file for the inventory system
// Contains common functionality used across the application

// Global variables
let currentUser = null;
let currentTheme = 'blue';
let loadingCount = 0;

// Initialize the application
$(document).ready(function() {
    initializeApp();
    setupEventListeners();
    setupGlobalKeyboardShortcuts();
    loadUserPreferences();
});

// Initialize application
function initializeApp() {
    // Get current user info from session
    currentUser = {
        id: $('#navbar').data('user-id'),
        username: $('#navbar').data('username'),
        role: $('#navbar').data('role')
    };
    
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Initialize popovers
    $('[data-bs-toggle="popover"]').popover();
    
    // Setup CSRF token for AJAX requests
    setupCSRFToken();
    
    // Initialize theme
    initializeTheme();
    
    // Auto-save form data
    setupAutoSave();
    
    // Setup confirmation dialogs
    setupConfirmationDialogs();
    
    console.log('Inventory System initialized successfully');
}

// Setup global event listeners
function setupEventListeners() {
    // Handle loading states
    $(document).ajaxStart(function() {
        showLoading();
    }).ajaxStop(function() {
        hideLoading();
    });
    
    // Handle AJAX errors
    $(document).ajaxError(function(event, jqXHR, ajaxSettings, thrownError) {
        hideLoading();
        if (jqXHR.status === 401) {
            window.location.href = '/login';
        } else if (jqXHR.status === 403) {
            showNotification('No tiene permisos para realizar esta acción', 'error');
        } else if (jqXHR.status >= 500) {
            showNotification('Error del servidor. Intente nuevamente.', 'error');
        }
    });
    
    // Handle form submissions
    $('form').on('submit', function() {
        const submitButton = $(this).find('button[type="submit"]');
        submitButton.prop('disabled', true);
        
        // Re-enable after 10 seconds to prevent permanent disabled state
        setTimeout(function() {
            submitButton.prop('disabled', false);
        }, 10000);
    });
    
    // Handle number inputs
    $('input[type="number"]').on('input', function() {
        const value = parseFloat($(this).val());
        const min = parseFloat($(this).attr('min'));
        const max = parseFloat($(this).attr('max'));
        
        if (min !== undefined && value < min) {
            $(this).val(min);
        }
        if (max !== undefined && value > max) {
            $(this).val(max);
        }
    });
    
    // Auto-resize textareas
    $('textarea').on('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Handle file inputs
    $('input[type="file"]').on('change', function() {
        const files = this.files;
        const maxSize = 5 * 1024 * 1024; // 5MB
        
        for (let i = 0; i < files.length; i++) {
            if (files[i].size > maxSize) {
                showNotification('El archivo es demasiado grande. Máximo 5MB.', 'warning');
                $(this).val('');
                break;
            }
        }
    });
}

// Setup global keyboard shortcuts
function setupGlobalKeyboardShortcuts() {
    $(document).keydown(function(e) {
        // Ctrl/Cmd + S to save (prevent default browser save)
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const form = $('form:visible').first();
            if (form.length) {
                form.submit();
            }
        }
        
        // Ctrl/Cmd + N for new item
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            const newButton = $('a[href*="/new"], button[onclick*="new"]').first();
            if (newButton.length) {
                newButton[0].click();
            }
        }
        
        // F1 for help
        if (e.key === 'F1') {
            e.preventDefault();
            showHelp();
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            $('.modal.show').modal('hide');
        }
        
        // Ctrl/Cmd + F for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            const searchInput = $('input[type="search"], input[name="search"]').first();
            if (searchInput.length) {
                searchInput.focus().select();
            }
        }
    });
}

// CSRF Token setup
function setupCSRFToken() {
    // Add CSRF token to all AJAX requests
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                const token = $('meta[name=csrf-token]').attr('content');
                if (token) {
                    xhr.setRequestHeader("X-CSRFToken", token);
                }
            }
        }
    });
}

// Theme management
function initializeTheme() {
    const savedTheme = localStorage.getItem('inventoryTheme') || 'blue';
    applyTheme(savedTheme);
}

function applyTheme(theme) {
    currentTheme = theme;
    
    // Remove all theme classes
    $('body').removeClass('theme-blue theme-green theme-purple theme-orange');
    
    // Add the selected theme class
    $('body').addClass('theme-' + theme);
    
    // Save to localStorage
    localStorage.setItem('inventoryTheme', theme);
    
    // Update theme selector if exists
    $('.theme-option').removeClass('active');
    $('.theme-option.' + theme).addClass('active');
    
    console.log('Theme applied:', theme);
}

// Loading management
function showLoading(message = 'Cargando...') {
    loadingCount++;
    const overlay = $('#loadingOverlay');
    if (overlay.length) {
        overlay.find('.spinner-text').text(message);
        overlay.removeClass('d-none');
    }
}

function hideLoading() {
    loadingCount = Math.max(0, loadingCount - 1);
    if (loadingCount === 0) {
        const overlay = $('#loadingOverlay');
        if (overlay.length) {
            overlay.addClass('d-none');
        }
    }
}

// Notification system
function showNotification(message, type = 'info', duration = 5000) {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';
    
    const icon = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-triangle',
        'warning': 'fa-exclamation-circle',
        'info': 'fa-info-circle'
    }[type] || 'fa-info-circle';
    
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show notification-alert" role="alert">
            <i class="fas ${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Find container for notifications
    let container = $('.notification-container');
    if (!container.length) {
        container = $('<div class="notification-container position-fixed top-0 end-0 p-3" style="z-index: 9999;"></div>');
        $('body').append(container);
    }
    
    const alert = $(alertHtml);
    container.append(alert);
    
    // Auto-dismiss after duration
    if (duration > 0) {
        setTimeout(function() {
            alert.alert('close');
        }, duration);
    }
    
    return alert;
}

// Confirmation dialogs
function setupConfirmationDialogs() {
    $('[data-confirm]').on('click', function(e) {
        const message = $(this).data('confirm');
        if (!confirm(message)) {
            e.preventDefault();
            return false;
        }
    });
}

// Auto-save functionality
function setupAutoSave() {
    const autoSaveForms = $('form[data-autosave]');
    
    autoSaveForms.each(function() {
        const form = $(this);
        const interval = parseInt(form.data('autosave')) || 30000; // Default 30 seconds
        
        setInterval(function() {
            if (form.find(':input').filter(function() {
                return $(this).val() !== $(this).prop('defaultValue');
            }).length > 0) {
                saveFormData(form);
            }
        }, interval);
    });
}

function saveFormData(form) {
    const formId = form.attr('id') || 'form_' + Date.now();
    const formData = form.serialize();
    
    localStorage.setItem('autosave_' + formId, formData);
    console.log('Form data auto-saved:', formId);
}

function loadFormData(formId) {
    const savedData = localStorage.getItem('autosave_' + formId);
    if (savedData) {
        // Parse and populate form fields
        const data = new URLSearchParams(savedData);
        data.forEach((value, key) => {
            const field = $(`[name="${key}"]`);
            if (field.length) {
                field.val(value);
            }
        });
    }
}

function clearFormData(formId) {
    localStorage.removeItem('autosave_' + formId);
}

// User preferences
function loadUserPreferences() {
    // Load theme preference
    const theme = localStorage.getItem('inventoryTheme');
    if (theme) {
        applyTheme(theme);
    }
    
    // Load other preferences
    const prefs = JSON.parse(localStorage.getItem('userPreferences') || '{}');
    
    // Apply pagination preferences
    if (prefs.itemsPerPage) {
        $('select[name="per_page"]').val(prefs.itemsPerPage);
    }
    
    // Apply table view preferences
    if (prefs.tableView) {
        $('.view-toggle button[data-view="' + prefs.tableView + '"]').addClass('active');
    }
}

function saveUserPreference(key, value) {
    const prefs = JSON.parse(localStorage.getItem('userPreferences') || '{}');
    prefs[key] = value;
    localStorage.setItem('userPreferences', JSON.stringify(prefs));
}

// Utility functions
function formatCurrency(amount, currency = '$') {
    return currency + parseFloat(amount).toLocaleString('es-CO', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatNumber(number, decimals = 0) {
    return parseFloat(number).toLocaleString('es-CO', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

function formatDate(date, includeTime = false) {
    const d = new Date(date);
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    };
    
    if (includeTime) {
        options.hour = '2-digit';
        options.minute = '2-digit';
    }
    
    return d.toLocaleDateString('es-CO', options);
}

function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction() {
        const context = this;
        const args = arguments;
        const later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Data validation
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePhone(phone) {
    const re = /^[\+]?[1-9][\d]{0,15}$/;
    return re.test(phone.replace(/\s/g, ''));
}

function validateRequired(value) {
    return value !== null && value !== undefined && value.toString().trim() !== '';
}

// Form validation
function validateForm(form) {
    let isValid = true;
    const errors = [];
    
    // Check required fields
    form.find('[required]').each(function() {
        const field = $(this);
        const value = field.val();
        
        if (!validateRequired(value)) {
            field.addClass('is-invalid');
            isValid = false;
            errors.push(`${field.attr('name')} es requerido`);
        } else {
            field.removeClass('is-invalid');
        }
    });
    
    // Check email fields
    form.find('input[type="email"]').each(function() {
        const field = $(this);
        const value = field.val();
        
        if (value && !validateEmail(value)) {
            field.addClass('is-invalid');
            isValid = false;
            errors.push('Email no válido');
        }
    });
    
    // Check phone fields
    form.find('input[type="tel"]').each(function() {
        const field = $(this);
        const value = field.val();
        
        if (value && !validatePhone(value)) {
            field.addClass('is-invalid');
            isValid = false;
            errors.push('Teléfono no válido');
        }
    });
    
    if (!isValid) {
        showNotification('Por favor corrija los errores en el formulario: ' + errors.join(', '), 'error');
    }
    
    return isValid;
}

// Help system
function showHelp() {
    const currentPage = window.location.pathname;
    const helpContent = getHelpContent(currentPage);
    
    const modal = $(`
        <div class="modal fade" id="helpModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-question-circle me-2"></i>Ayuda
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${helpContent}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                    </div>
                </div>
            </div>
        </div>
    `);
    
    $('body').append(modal);
    modal.modal('show');
    
    modal.on('hidden.bs.modal', function() {
        modal.remove();
    });
}

function getHelpContent(page) {
    const helpTexts = {
        '/dashboard': `
            <h6>Dashboard Principal</h6>
            <p>Esta es la página principal del sistema donde puede ver:</p>
            <ul>
                <li>Resumen de ventas del día y mes</li>
                <li>Productos con stock bajo</li>
                <li>Ventas recientes</li>
                <li>Accesos rápidos a funciones principales</li>
            </ul>
            <p><strong>Atajos de teclado:</strong></p>
            <ul>
                <li><kbd>Ctrl+N</kbd> - Crear nuevo elemento</li>
                <li><kbd>F1</kbd> - Mostrar ayuda</li>
            </ul>
        `,
        '/inventory': `
            <h6>Gestión de Inventario</h6>
            <p>Aquí puede gestionar todos sus productos:</p>
            <ul>
                <li>Ver lista de productos con filtros</li>
                <li>Crear nuevos productos</li>
                <li>Editar información de productos</li>
                <li>Gestionar stock por bodega</li>
            </ul>
            <p><strong>Consejos:</strong></p>
            <ul>
                <li>Use códigos de barras para búsquedas rápidas</li>
                <li>Configure stock mínimo para alertas</li>
                <li>Mantenga actualizados los precios</li>
            </ul>
        `,
        '/pos': `
            <h6>Punto de Venta (POS)</h6>
            <p>Sistema optimizado para ventas rápidas:</p>
            <ul>
                <li>Escanee códigos de barras o busque productos</li>
                <li>Agregue productos al carrito</li>
                <li>Configure descuentos e impuestos</li>
                <li>Procese la venta</li>
            </ul>
            <p><strong>Flujo recomendado:</strong></p>
            <ol>
                <li>Seleccione bodega</li>
                <li>Agregue productos</li>
                <li>Verifique totales</li>
                <li>Procese el pago</li>
            </ol>
        `
    };
    
    return helpTexts[page] || `
        <h6>Ayuda General</h6>
        <p>Bienvenido al Sistema de Inventario. Este sistema le permite:</p>
        <ul>
            <li>Gestionar productos e inventario</li>
            <li>Procesar ventas y compras</li>
            <li>Administrar clientes y proveedores</li>
            <li>Generar reportes</li>
        </ul>
        <p><strong>Atajos globales:</strong></p>
        <ul>
            <li><kbd>Ctrl+S</kbd> - Guardar formulario</li>
            <li><kbd>Ctrl+N</kbd> - Nuevo elemento</li>
            <li><kbd>Ctrl+F</kbd> - Buscar</li>
            <li><kbd>F1</kbd> - Ayuda</li>
            <li><kbd>Esc</kbd> - Cerrar modal</li>
        </ul>
    `;
}

// Export functions for global use
window.InventorySystem = {
    showNotification,
    showLoading,
    hideLoading,
    applyTheme,
    formatCurrency,
    formatNumber,
    formatDate,
    validateForm,
    debounce,
    throttle,
    showHelp
};

// Initialize when DOM is ready
$(document).ready(function() {
    console.log('Inventory System Main JS loaded successfully');
});
