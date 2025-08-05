// Point of Sale (POS) JavaScript functionality
// Handles all POS-specific operations and UI interactions

class POSSystem {
    constructor() {
        this.cart = [];
        this.customer = null;
        this.warehouse_id = null;
        this.searchTimeout = null;
        this.lastSale = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadSettings();
        this.setupKeyboardShortcuts();
        this.focusSearchInput();
        
        console.log('POS System initialized');
    }
    
    setupEventListeners() {
        // Product search
        $('#product_search').on('input', this.debounce((e) => {
            this.searchProducts(e.target.value);
        }, 300));
        
        // Barcode input (handle immediate entry)
        $('#product_search').on('keypress', (e) => {
            if (e.which === 13) { // Enter key
                e.preventDefault();
                this.handleBarcodeInput(e.target.value);
            }
        });
        
        // Customer selection
        $('#pos_customer').on('change', (e) => {
            this.selectCustomer(e.target.value);
        });
        
        // Payment method change
        $('#pos_payment_method').on('change', (e) => {
            this.handlePaymentMethodChange(e.target.value);
        });
        
        // Discount and tax inputs
        $('#pos_discount, #pos_tax').on('input', () => {
            this.calculateTotals();
        });
        
        // Payment received input
        $('#pos_received').on('input', () => {
            this.calculateChange();
        });
        
        // Quick customer form
        $('#quickCustomerForm').on('submit', (e) => {
            e.preventDefault();
            this.createQuickCustomer();
        });
        
        // Clear cart
        $(document).on('click', '[data-action="clear-cart"]', () => {
            this.clearCart();
        });
        
        // Remove item from cart
        $(document).on('click', '[data-action="remove-item"]', (e) => {
            const index = $(e.target).data('index');
            this.removeFromCart(index);
        });
        
        // Update quantity
        $(document).on('change', '.cart-quantity', (e) => {
            const index = $(e.target).data('index');
            const quantity = parseFloat(e.target.value) || 1;
            this.updateQuantity(index, quantity);
        });
        
        // Update price
        $(document).on('change', '.cart-price', (e) => {
            const index = $(e.target).data('index');
            const price = parseFloat(e.target.value) || 0;
            this.updatePrice(index, price);
        });
        
        // Process sale
        $('#process_sale').on('click', () => {
            this.processSale();
        });
    }
    
    setupKeyboardShortcuts() {
        $(document).on('keydown', (e) => {
            // F2 - Focus search
            if (e.key === 'F2') {
                e.preventDefault();
                this.focusSearchInput();
            }
            
            // F3 - Select customer
            if (e.key === 'F3') {
                e.preventDefault();
                $('#pos_customer').focus();
            }
            
            // F4 - Process sale
            if (e.key === 'F4') {
                e.preventDefault();
                this.processSale();
            }
            
            // F5 - Clear cart
            if (e.key === 'F5') {
                e.preventDefault();
                this.clearCart();
            }
            
            // F6 - New customer
            if (e.key === 'F6') {
                e.preventDefault();
                this.showQuickCustomer();
            }
            
            // F9 - Hold sale
            if (e.key === 'F9') {
                e.preventDefault();
                this.holdSale();
            }
            
            // Plus key - Add to quantity
            if (e.key === '+' && this.cart.length > 0) {
                e.preventDefault();
                this.updateQuantity(this.cart.length - 1, this.cart[this.cart.length - 1].quantity + 1);
            }
            
            // Minus key - Subtract from quantity
            if (e.key === '-' && this.cart.length > 0) {
                e.preventDefault();
                const lastItem = this.cart[this.cart.length - 1];
                if (lastItem.quantity > 1) {
                    this.updateQuantity(this.cart.length - 1, lastItem.quantity - 1);
                }
            }
        });
    }
    
    loadSettings() {
        // Load warehouse selection
        this.warehouse_id = $('#warehouse_id').val() || localStorage.getItem('pos_warehouse_id');
        
        // Load last customer
        const lastCustomerId = localStorage.getItem('pos_last_customer');
        if (lastCustomerId) {
            $('#pos_customer').val(lastCustomerId);
        }
        
        // Load payment method preference
        const lastPaymentMethod = localStorage.getItem('pos_payment_method');
        if (lastPaymentMethod) {
            $('#pos_payment_method').val(lastPaymentMethod);
        }
    }
    
    focusSearchInput() {
        $('#product_search').focus().select();
    }
    
    searchProducts(query) {
        if (!query || query.length < 1) {
            $('#search_results').empty();
            return;
        }
        
        if (!this.warehouse_id) {
            InventorySystem.showNotification('Seleccione una bodega primero', 'warning');
            return;
        }
        
        // Show loading indicator
        $('#search_results').html('<div class="text-center p-3"><i class="fas fa-spinner fa-spin"></i> Buscando...</div>');
        
        $.get('/pos/search_product', {
            q: query,
            warehouse_id: this.warehouse_id
        })
        .done((data) => {
            this.displaySearchResults(data.products);
        })
        .fail(() => {
            $('#search_results').html('<div class="text-center p-3 text-muted">Error en la búsqueda</div>');
        });
    }
    
    handleBarcodeInput(barcode) {
        if (!barcode.trim()) return;
        
        // First try to find in search results
        const existingResults = $('#search_results .product-result');
        if (existingResults.length === 1) {
            // If only one result, add it automatically
            existingResults.first().click();
            return;
        }
        
        // Search for exact barcode match
        this.searchProducts(barcode);
    }
    
    displaySearchResults(products) {
        const resultsContainer = $('#search_results');
        resultsContainer.empty();
        
        if (!products || products.length === 0) {
            resultsContainer.html('<div class="text-center p-3 text-muted">No se encontraron productos</div>');
            return;
        }
        
        // If exact barcode match, add automatically
        if (products.length === 1 && products[0].exact_match) {
            this.addToCart(products[0]);
            this.clearSearch();
            return;
        }
        
        products.forEach(product => {
            const resultItem = $(`
                <div class="list-group-item list-group-item-action product-result" 
                     data-product='${JSON.stringify(product)}'>
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${product.name}</h6>
                            <small class="text-muted">
                                SKU: ${product.sku} | 
                                Stock: <span class="badge bg-${product.quantity > 0 ? 'success' : 'danger'}">${product.quantity}</span>
                            </small>
                            ${product.barcode ? `<br><small class="text-muted">Código: ${product.barcode}</small>` : ''}
                        </div>
                        <div class="text-end">
                            <strong class="text-primary">$${product.price1.toFixed(2)}</strong>
                            ${product.exact_match ? '<br><span class="badge bg-success">Coincidencia exacta</span>' : ''}
                        </div>
                    </div>
                </div>
            `);
            
            resultItem.on('click', () => {
                this.addToCart(product);
                this.clearSearch();
            });
            
            resultsContainer.append(resultItem);
        });
    }
    
    addToCart(product) {
        // Check if product already in cart
        const existingIndex = this.cart.findIndex(item => item.product_id === product.id);
        
        if (existingIndex >= 0) {
            // Increase quantity
            this.cart[existingIndex].quantity += 1;
        } else {
            // Add new item
            const customerPriceLevel = this.getCustomerPriceLevel();
            const price = this.getProductPrice(product, customerPriceLevel);
            
            const cartItem = {
                product_id: product.id,
                name: product.name,
                sku: product.sku,
                quantity: 1,
                unit_price: price,
                discount_percent: 0,
                stock: product.quantity,
                track_serial: product.track_serial,
                serial_id: null
            };
            
            this.cart.push(cartItem);
        }
        
        this.updateCartDisplay();
        this.calculateTotals();
        this.playAddSound();
        
        // Show success notification
        InventorySystem.showNotification(`${product.name} agregado al carrito`, 'success', 2000);
    }
    
    getCustomerPriceLevel() {
        const customer = $('#pos_customer').find(':selected');
        return parseInt(customer.data('price-level')) || 1;
    }
    
    getProductPrice(product, priceLevel) {
        const prices = {
            1: product.price1,
            2: product.price2 || product.price1,
            3: product.price3 || product.price1,
            4: product.price4 || product.price1
        };
        
        return prices[priceLevel] || product.price1;
    }
    
    removeFromCart(index) {
        if (index >= 0 && index < this.cart.length) {
            const item = this.cart[index];
            this.cart.splice(index, 1);
            this.updateCartDisplay();
            this.calculateTotals();
            
            InventorySystem.showNotification(`${item.name} eliminado del carrito`, 'info', 2000);
        }
    }
    
    updateQuantity(index, quantity) {
        if (index >= 0 && index < this.cart.length && quantity > 0) {
            const item = this.cart[index];
            
            // Check stock availability
            if (quantity > item.stock) {
                InventorySystem.showNotification(`Stock insuficiente. Disponible: ${item.stock}`, 'warning');
                return;
            }
            
            this.cart[index].quantity = quantity;
            this.updateCartDisplay();
            this.calculateTotals();
        }
    }
    
    updatePrice(index, price) {
        if (index >= 0 && index < this.cart.length && price >= 0) {
            this.cart[index].unit_price = price;
            this.updateCartDisplay();
            this.calculateTotals();
        }
    }
    
    updateCartDisplay() {
        const cartContainer = $('#cart_items');
        const emptyCart = $('#empty_cart');
        
        if (this.cart.length === 0) {
            emptyCart.show();
            cartContainer.children('.pos-cart-item').remove();
            return;
        }
        
        emptyCart.hide();
        cartContainer.children('.pos-cart-item').remove();
        
        this.cart.forEach((item, index) => {
            const total = item.quantity * item.unit_price;
            
            const cartItem = $(`
                <div class="pos-cart-item">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${item.name}</h6>
                            <small class="text-muted">SKU: ${item.sku}</small>
                            ${item.stock <= item.quantity ? '<br><span class="badge bg-warning">Stock bajo</span>' : ''}
                        </div>
                        <button type="button" class="btn btn-sm btn-outline-danger" 
                                data-action="remove-item" data-index="${index}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    
                    <div class="row g-2">
                        <div class="col-4">
                            <label class="form-label form-label-sm">Cant.</label>
                            <input type="number" class="form-control form-control-sm cart-quantity" 
                                   value="${item.quantity}" min="1" max="${item.stock}" 
                                   data-index="${index}">
                        </div>
                        <div class="col-4">
                            <label class="form-label form-label-sm">Precio</label>
                            <input type="number" class="form-control form-control-sm cart-price" 
                                   value="${item.unit_price}" min="0" step="0.01" 
                                   data-index="${index}">
                        </div>
                        <div class="col-4">
                            <label class="form-label form-label-sm">Total</label>
                            <div class="form-control form-control-sm bg-light">
                                $${total.toFixed(2)}
                            </div>
                        </div>
                    </div>
                    
                    ${item.track_serial ? this.renderSerialSelector(item, index) : ''}
                </div>
            `);
            
            cartContainer.append(cartItem);
        });
    }
    
    renderSerialSelector(item, index) {
        return `
            <div class="mt-2">
                <label class="form-label form-label-sm">Serial/IMEI</label>
                <select class="form-select form-select-sm" data-action="select-serial" data-index="${index}">
                    <option value="">Seleccionar serial</option>
                </select>
            </div>
        `;
    }
    
    calculateTotals() {
        let subtotal = 0;
        
        this.cart.forEach(item => {
            subtotal += item.quantity * item.unit_price;
        });
        
        const discountPercent = parseFloat($('#pos_discount').val()) || 0;
        const taxPercent = parseFloat($('#pos_tax').val()) || 0;
        
        const discountAmount = subtotal * (discountPercent / 100);
        const taxableAmount = subtotal - discountAmount;
        const taxAmount = taxableAmount * (taxPercent / 100);
        const total = taxableAmount + taxAmount;
        
        // Update display
        $('#pos_subtotal').text(InventorySystem.formatCurrency(subtotal));
        $('#pos_discount_amount').text(InventorySystem.formatCurrency(discountAmount));
        $('#pos_tax_amount').text(InventorySystem.formatCurrency(taxAmount));
        $('#pos_total').text(InventorySystem.formatCurrency(total));
        
        this.calculateChange();
    }
    
    calculateChange() {
        const total = this.getTotalAmount();
        const received = parseFloat($('#pos_received').val()) || 0;
        const change = received - total;
        
        $('#pos_change').text(InventorySystem.formatCurrency(change));
        $('#pos_change').removeClass('text-success text-danger');
        
        if (change >= 0) {
            $('#pos_change').addClass('text-success');
        } else if (received > 0) {
            $('#pos_change').addClass('text-danger');
        }
    }
    
    getTotalAmount() {
        const totalText = $('#pos_total').text().replace(/[^0-9.-]+/g, '');
        return parseFloat(totalText) || 0;
    }
    
    selectCustomer(customerId) {
        if (customerId) {
            $.get(`/pos/get_customer/${customerId}`)
                .done((customer) => {
                    this.customer = customer;
                    // Update prices based on customer price level
                    this.updateCartPricesForCustomer();
                    localStorage.setItem('pos_last_customer', customerId);
                })
                .fail(() => {
                    InventorySystem.showNotification('Error al cargar información del cliente', 'error');
                });
        } else {
            this.customer = null;
            localStorage.removeItem('pos_last_customer');
        }
    }
    
    updateCartPricesForCustomer() {
        // This would require fetching updated prices from server
        // For now, we'll recalculate with current prices
        this.calculateTotals();
    }
    
    handlePaymentMethodChange(method) {
        if (method === 'cash') {
            $('#payment_calculator').show();
        } else {
            $('#payment_calculator').hide();
        }
        
        localStorage.setItem('pos_payment_method', method);
    }
    
    showQuickCustomer() {
        const modal = new bootstrap.Modal(document.getElementById('quickCustomerModal'));
        modal.show();
        
        // Focus first input when modal is shown
        $('#quickCustomerModal').on('shown.bs.modal', function() {
            $('#quick_customer_name').focus();
        });
    }
    
    createQuickCustomer() {
        const formData = {
            name: $('#quick_customer_name').val(),
            document: $('#quick_customer_document').val(),
            phone: $('#quick_customer_phone').val()
        };
        
        if (!formData.name.trim()) {
            InventorySystem.showNotification('El nombre es requerido', 'error');
            return;
        }
        
        InventorySystem.showLoading('Creando cliente...');
        
        $.ajax({
            url: '/pos/quick_customer',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData)
        })
        .done((response) => {
            if (response.success) {
                // Add to customer select
                const option = $(`<option value="${response.customer.id}" data-price-level="${response.customer.price_level}">${response.customer.name}</option>`);
                $('#pos_customer').append(option);
                $('#pos_customer').val(response.customer.id);
                
                this.selectCustomer(response.customer.id);
                
                // Close modal and reset form
                bootstrap.Modal.getInstance(document.getElementById('quickCustomerModal')).hide();
                $('#quickCustomerForm')[0].reset();
                
                InventorySystem.showNotification('Cliente creado exitosamente', 'success');
            } else {
                InventorySystem.showNotification('Error al crear cliente: ' + response.error, 'error');
            }
        })
        .fail(() => {
            InventorySystem.showNotification('Error de conexión', 'error');
        })
        .always(() => {
            InventorySystem.hideLoading();
        });
    }
    
    processSale() {
        if (this.cart.length === 0) {
            InventorySystem.showNotification('El carrito está vacío', 'warning');
            return;
        }
        
        // Validate stock
        for (const item of this.cart) {
            if (item.quantity > item.stock) {
                InventorySystem.showNotification(`Stock insuficiente para ${item.name}`, 'error');
                return;
            }
        }
        
        const saleData = {
            customer_id: $('#pos_customer').val() || null,
            payment_method: $('#pos_payment_method').val(),
            items: this.cart,
            subtotal: this.getSubtotalAmount(),
            discount_amount: this.getDiscountAmount(),
            tax_amount: this.getTaxAmount(),
            total: this.getTotalAmount()
        };
        
        InventorySystem.showLoading('Procesando venta...');
        $('#process_sale').prop('disabled', true);
        
        $.ajax({
            url: '/pos/process_sale',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(saleData)
        })
        .done((response) => {
            if (response.success) {
                this.lastSale = response;
                this.showSaleSuccess(response);
                this.clearCart();
                this.focusSearchInput();
            } else {
                InventorySystem.showNotification('Error al procesar venta: ' + response.error, 'error');
            }
        })
        .fail(() => {
            InventorySystem.showNotification('Error de conexión', 'error');
        })
        .always(() => {
            InventorySystem.hideLoading();
            $('#process_sale').prop('disabled', false);
        });
    }
    
    getSubtotalAmount() {
        const subtotalText = $('#pos_subtotal').text().replace(/[^0-9.-]+/g, '');
        return parseFloat(subtotalText) || 0;
    }
    
    getDiscountAmount() {
        const discountText = $('#pos_discount_amount').text().replace(/[^0-9.-]+/g, '');
        return parseFloat(discountText) || 0;
    }
    
    getTaxAmount() {
        const taxText = $('#pos_tax_amount').text().replace(/[^0-9.-]+/g, '');
        return parseFloat(taxText) || 0;
    }
    
    showSaleSuccess(saleData) {
        $('#success_invoice_number').text(saleData.invoice_number);
        $('#success_total').text(`Total: ${InventorySystem.formatCurrency(saleData.total || 0)}`);
        
        const modal = new bootstrap.Modal(document.getElementById('saleSuccessModal'));
        modal.show();
    }
    
    clearCart() {
        this.cart = [];
        this.updateCartDisplay();
        this.calculateTotals();
        $('#pos_received').val('');
        $('#pos_discount').val('0');
        $('#pos_tax').val('0');
    }
    
    clearSearch() {
        $('#product_search').val('');
        $('#search_results').empty();
    }
    
    holdSale() {
        if (this.cart.length === 0) {
            InventorySystem.showNotification('No hay productos en el carrito', 'warning');
            return;
        }
        
        const heldSales = JSON.parse(localStorage.getItem('pos_held_sales') || '[]');
        const saleData = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            cart: [...this.cart],
            customer_id: $('#pos_customer').val(),
            discount: $('#pos_discount').val(),
            tax: $('#pos_tax').val()
        };
        
        heldSales.push(saleData);
        localStorage.setItem('pos_held_sales', JSON.stringify(heldSales));
        
        this.clearCart();
        InventorySystem.showNotification('Venta retenida exitosamente', 'success');
    }
    
    showRecentSales() {
        // Load recent sales from server or localStorage
        window.open('/pos/recent_sales', 'recent_sales', 'width=800,height=600');
    }
    
    playAddSound() {
        // Simple beep sound for adding items
        if (window.AudioContext || window.webkitAudioContext) {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        }
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Global functions for HTML onclick handlers
function clearCart() {
    if (window.posSystem) {
        window.posSystem.clearCart();
    }
}

function processSale() {
    if (window.posSystem) {
        window.posSystem.processSale();
    }
}

function holdSale() {
    if (window.posSystem) {
        window.posSystem.holdSale();
    }
}

function showRecentSales() {
    if (window.posSystem) {
        window.posSystem.showRecentSales();
    }
}

function showQuickCustomer() {
    if (window.posSystem) {
        window.posSystem.showQuickCustomer();
    }
}

function printReceipt() {
    if (window.posSystem && window.posSystem.lastSale) {
        window.open(`/pos/reprint/${window.posSystem.lastSale.sale_id}`, '_blank');
    }
}

function newSale() {
    if (window.posSystem) {
        window.posSystem.clearCart();
        bootstrap.Modal.getInstance(document.getElementById('saleSuccessModal')).hide();
        window.posSystem.focusSearchInput();
    }
}

// Initialize POS system when DOM is ready
$(document).ready(function() {
    if ($('#product_search').length) {
        window.posSystem = new POSSystem();
        console.log('POS System loaded successfully');
    }
});
