/* Store Configuration - Centralized settings */
var StoreConfig = (function() {
    var KEY = 'danzona_store_config';
    var defaults = {
        storeName: 'SHEDS POS', storeAddress: '', phoneNumber: '', emailAddress: '',
        currency: '₦', currencyLocale: 'en-NG', lowStockThreshold: 5, sessionTimeout: 30,
        storeLogo: '', footerText: 'Thank you for choosing SHEDS POS!', printerType: 'small',
        pharmacyName: 'SHEDS POS',
        siteTagline: 'Point of Sale System', siteDescription: '',
        taxEnabled: false, taxRate: 7.5, taxName: 'VAT',
        allowDiscount: true, maxDiscount: 20,
        requireManagerForDiscount: false, requireManagerForVoid: true,
        receiptPrefix: 'DAN', autoPrintReceipt: true, showReceiptLogo: true,
        receiptPageSize: '80mm', receiptFontSize: '12', receiptMargin: '10',
        expiryAlertDays: 30, expiryBlockSales: false,
        lowStockAlert: true, lowStockEmail: '',
        openingTime: '08:00', closingTime: '20:00', openDays: 'Mon-Sat',
        allowStoreAccount: true, allowGiftCard: true, allowCardPayment: true, allowPosPayment: true,
        sidebarMode: 'expanded', tableDensity: 'normal', dateFormat: 'DD/MM/YYYY',
        timeFormat: '12', enableAnimations: true, dashboardCardsPerRow: '4',
        showQuickActions: true, compactMode: false,
        themeMode: 'light', primaryColor: '#10b981', fontFamily: 'Inter, Arial, sans-serif',
        baseFontSize: 14, borderRadius: '10px', shadowIntensity: 'normal',
        headerStyle: 'gradient', tableStyle: 'bordered', contentWidth: 'full',
        cardStyle: 'shadow', customCSS: '',
        defaultPaymentMethod: 'cash', productsPerRow: '4',
        confirmBeforeSale: false, showProductImages: true, allowNegativeStock: false,
        requireCustomerForSale: false, enableSound: false,
        notificationPosition: 'top-right', lowStockNotification: false,
        expiryNotification: false, notificationDuration: 4,
        showDesktopNotification: false, lockScreenTimeout: 5,
        requirePasswordForVoid: false, requirePasswordForDiscount: false,
        requirePasswordForRefund: false, enableAuditLog: false,
        autoBackup: false, backupTime: '02:00', autoSync: false, syncInterval: 15
    };
    function getAll() { try { var raw = localStorage.getItem(KEY); if (!raw) return JSON.parse(JSON.stringify(defaults)); var parsed = JSON.parse(raw); return Object.assign({}, defaults, parsed); } catch (e) { return JSON.parse(JSON.stringify(defaults)); } }
    function get(key) { var cfg = getAll(); return cfg[key] !== undefined ? cfg[key] : defaults[key]; }
    function set(key, value) { var cfg = getAll(); cfg[key] = value; save(cfg); }
    function save(cfg) { try { localStorage.setItem(KEY, JSON.stringify(cfg)); return true; } catch (e) { console.error('StoreConfig save error:', e); return false; } }
    function formatCurrency(amount) { var currency = get('currency'); var locale = get('currencyLocale'); try { return currency + (parseFloat(amount) || 0).toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); } catch (e) { return currency + (parseFloat(amount) || 0).toFixed(2); } }
    function formatDate(dateStr) { try { return new Date(dateStr).toLocaleDateString(get('currencyLocale'), { day: 'numeric', month: 'short', year: 'numeric' }); } catch (e) { return dateStr || '-'; } }
    function getStoreName() { return get('storeName') || defaults.storeName; }
    function getCurrency() { return get('currency') || defaults.currency; }
    function getLowStockThreshold() { return parseInt(get('lowStockThreshold')) || defaults.lowStockThreshold; }
    function getPharmacyName() { return get('pharmacyName') || get('storeName') || defaults.storeName; }
    async function syncFromServer() {
        try {
            if (!API.isLoggedIn()) return;
            var data = await API.get('/store-config');
            if (data && Object.keys(data).length > 0) {
                save(data);
            }
        } catch (e) {
            console.error('StoreConfig sync error:', e);
        }
    }
    async function syncToServer() {
        try {
            if (!API.isLoggedIn()) return;
            var cfg = getAll();
            await API.put('/store-config', cfg);
        } catch (e) {
            console.error('StoreConfig syncToServer error:', e);
        }
    }
    return { getAll: getAll, get: get, set: set, save: save, formatCurrency: formatCurrency, formatDate: formatDate, getStoreName: getStoreName, getCurrency: getCurrency, getLowStockThreshold: getLowStockThreshold, getPharmacyName: getPharmacyName, syncFromServer: syncFromServer, syncToServer: syncToServer, defaults: defaults, KEY: KEY };
})();

var POS = (function() {
    var pages = {
        'index.html': { label: 'Home', icon: 'fa-home' },
        'dashboard.html': { label: 'Dashboard', icon: 'fa-home' },
        'sales.html': { label: 'SALES', icon: 'fa-shopping-cart' },
        'suspended-sales.html': { label: 'Suspended Sales', icon: 'fa-pause' },
        'receipt.html': { label: 'Receipt', icon: 'fa-receipt' },
        'variations.html': { label: 'Add / Edit Product', icon: 'fa-plus-circle' },
        'inventory.html': { label: 'Inventory', icon: 'fa-boxes' },
        'customers.html': { label: 'Customers', icon: 'fa-users' },
        'suppliers.html': { label: 'Suppliers', icon: 'fa-truck' },
        'reports.html': { label: 'Reports', icon: 'fa-chart-bar' },
        'receiving.html': { label: 'Receiving', icon: 'fa-file-import' },
        'expenses.html': { label: 'Expenses', icon: 'fa-receipt' },
        'employees.html': { label: 'Employees', icon: 'fa-user-tie' },
        'shifts.html': { label: 'Shift Manager', icon: 'fa-clock' },
        'appointments.html': { label: 'Appointments', icon: 'fa-calendar' },
        'giftcards.html': { label: 'Gift Cards', icon: 'fa-gift' },
        'invoices.html': { label: 'Invoices', icon: 'fa-file-invoice' },
        'deliveries.html': { label: 'Deliveries', icon: 'fa-truck-loading' },
        'cashier-closeout.html': { label: 'Cashier Closeout', icon: 'fa-calculator' },
        'sales-returns.html': { label: 'Sales Returns', icon: 'fa-rotate-left' },
        'audit-log.html': { label: 'Audit Log', icon: 'fa-clipboard-list' },
        'stock-transfer.html': { label: 'Stock Transfer', icon: 'fa-truck-ramp-box' },
        'purchase-orders.html': { label: 'Purchase Orders', icon: 'fa-file-invoice-dollar' },
        'daily-summary.html': { label: 'Daily Sales Summary', icon: 'fa-calendar-day' },
        'bank-reconciliation.html': { label: 'Bank Reconciliation', icon: 'fa-building-columns' },
        'user-roles.html': { label: 'User Roles & Permissions', icon: 'fa-user-shield' },
        'tax-settings.html': { label: 'Tax & Vat', icon: 'fa-percent' },
        'backups.html': { label: 'System Backups', icon: 'fa-download' },
        'promo-engine.html': { label: 'Promos & Discounts', icon: 'fa-tags' },
        'prescriptions.html': { label: 'Prescriptions / Rx', icon: 'fa-prescription' },
        'expiry-alerts.html': { label: 'Expiry & Batch Alerts', icon: 'fa-triangle-exclamation' },
        'drug-categories.html': { label: 'Drug Categories', icon: 'fa-tags' },
        'payments.html': { label: 'Payments', icon: 'fa-credit-card' },
        'locations.html': { label: 'Locations', icon: 'fa-store' },
        'messages.html': { label: 'Messages', icon: 'fa-envelope' },
        'config.html': { label: 'Store Config', icon: 'fa-cog' },
        'login.html': { label: 'Logout', icon: 'fa-sign-out-alt' }
    };
    function $(id) { return document.getElementById(id); }
    function esc(value) {
        var text = value == null ? '' : String(value);
        return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    }
    function navigateTo(page) { window.location.href = page; }
    function formatCurrency(value) { try { return StoreConfig.formatCurrency(value); } catch (e) { return '₦' + (parseFloat(value) || 0).toLocaleString('en-NG', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); } }
    function formatNumber(value) { try { var locale = StoreConfig.get('currencyLocale') || 'en-NG'; return (parseFloat(value) || 0).toLocaleString(locale); } catch (e) { return (parseFloat(value) || 0).toLocaleString('en-NG'); } }
    function formatDate(value, options) {
        if (!value) return '-';
        try { var locale = StoreConfig.get('currencyLocale') || 'en-NG'; return new Date(value).toLocaleDateString(locale, options || { day: 'numeric', month: 'short', year: 'numeric' }); } catch (e) { return new Date(value).toLocaleDateString('en-NG', options || { day: 'numeric', month: 'short', year: 'numeric' }); }
    }
    function today() { return new Date().toISOString().split('T')[0]; }
    function getDatePart(d) {
        if (!d) return '';
        var s = String(d);
        var idx = s.indexOf(' ');
        return idx > -1 ? s.substring(0, idx) : s;
    }
    function getQueryParameter(name) { return new URLSearchParams(window.location.search).get(name) || ''; }
    function showToast(message, isError) {
        var t = $('toast');
        if (!t) return;
        t.textContent = message;
        t.className = 'toast' + (isError ? ' error' : '');
        t.style.display = 'block';
        setTimeout(function() { t.style.display = 'none'; }, 3500);
    }
    function openModal(id) { var el = $(id); if (el) el.classList.add('open'); }
    function closeModal(id) { var el = $(id); if (el) el.classList.remove('open'); }
    function csvCell(value) {
        var text = value == null ? '' : String(value);
        return '"' + text.split('"').join('""') + '"';
    }
    function exportCSV(filename, headers, rows) {
        var lines = [headers.map(csvCell).join(',')];
        rows.forEach(function(row) { lines.push(headers.map(function(h) { return csvCell(row[h] == null ? '' : row[h]); }).join(',')); });
        var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('CSV exported');
    }
    function printTable(title, headers, rows) {
        var html = '<html><head><title>' + esc(title) + '</title><style>body{font-family:Inter,Arial,sans-serif;padding:24px;}table{width:100%;border-collapse:collapse;}th,td{border:1px solid #ddd;padding:10px;text-align:left;}th{background:#f8fafc;}h2{text-align:center;color:#10b981;}</style></head><body><h2>' + esc(title) + '</h2><p>Generated: ' + esc(new Date().toLocaleString()) + '</p><table><thead><tr>';
        headers.forEach(function(h) { html += '<th>' + esc(h) + '</th>'; });
        html += '</tr></thead><tbody>';
        rows.forEach(function(row) { html += '<tr>'; headers.forEach(function(h) { html += '<td>' + esc(row[h] == null ? '' : row[h]) + '</td>'; }); html += '</tr>'; });
        html += '</tbody></table></body></html>';
        var win = window.open('', '', 'width=980,height=700');
        if (win) { win.document.write(html); win.document.close(); win.focus(); win.print(); }
    }
    function renderSidebar() {
        var el = $('sidebar');
        if (!el) return;
        var current = window.location.pathname.split('/').pop();
        var groups = [
            {title:'Main',items:[['index.html','Home','fa-home'],['dashboard.html','Dashboard','fa-home'],['sales.html','SALES','fa-shopping-cart'],['suspended-sales.html','Suspended Sales','fa-pause'],['variations.html','Add Product','fa-plus-circle'],['inventory.html','Inventory','fa-boxes'],['receiving.html','Receiving','fa-file-import'],['reports.html','Reports','fa-chart-bar']]},
            {title:'Catalogue',items:[['customers.html','Customers','fa-users'],['suppliers.html','Suppliers','fa-truck'],['locations.html','Locations','fa-store'],['product-variations.html','Product Variations','fa-layer-group']]},
            {title:'Pharmacy',items:[['prescriptions.html','Prescriptions / Rx','fa-prescription'],['expiry-alerts.html','Expiry & Batch Alerts','fa-triangle-exclamation'],['drug-categories.html','Drug Categories','fa-tags']]},
            {title:'Finance',items:[['payments.html','Payments','fa-credit-card'],['store_account_payment.html','Store Account','fa-wallet'],['bank-reconciliation.html','Bank Reconciliation','fa-building-columns'],['tax-settings.html','Tax & Vat','fa-percent'],['promo-engine.html','Promos & Discounts','fa-tags'],['expenses.html','Expenses','fa-receipt'],['invoices.html','Invoices','fa-file-invoice'],['purchase-orders.html','Purchase Orders','fa-file-invoice-dollar'],['subscription.html','Subscription Fee','fa-calendar-check']]},
            {title:'Operations',items:[['employees.html','Employees','fa-user-tie'],['user-roles.html','User Roles','fa-user-shield'],['appointments.html','Appointments','fa-calendar'],['suspended-sales.html','Suspended Sales','fa-pause'],['receipt.html','Receipt','fa-receipt'],['giftcards.html','Gift Cards','fa-gift'],['deliveries.html','Deliveries','fa-truck-loading'],['cashier-closeout.html','Cashier Closeout','fa-calculator'],['daily-summary.html','Daily Sales Summary','fa-calendar-day'],['sales-returns.html','Sales Returns','fa-rotate-left'],['stock-transfer.html','Stock Transfer','fa-truck-ramp-box'],['messages.html','Messages','fa-envelope']]},
            {title:'Reports',items:[['reports.html','Reports','fa-chart-bar'],['audit-log.html','Audit Log','fa-clipboard-list'],['backups.html','System Backups','fa-download'],['config.html','Store Config','fa-cog'],['login.html','Logout','fa-sign-out-alt']]}
        ];
        el.innerHTML = '<div class="sidebar-header"><div class="sidebar-brand"><i class="fas fa-clinic-medical"></i><div><h1>' + esc(StoreConfig.getStoreName()) + '</h1><p>Point of Sale System</p></div></div></div><div class="sidebar-body">' + groups.map(function(group){return '<div class="sidebar-section"><div class="sidebar-section-title">'+esc(group.title)+'</div>'+group.items.map(function(item){var href = item[0], label = esc(item[1]), icon = item[2], isExternal = href.indexOf('http://') === 0 || href.indexOf('https://') === 0; return '<a class="sidebar-link '+(item[0]===current?'active':'')+'" href="' + esc(href) + '"' + (isExternal ? ' target="_blank" rel="noopener"' : ' onclick="POS.navigateTo(\'' + esc(href).replace(/'/g, "\\'") + '\');return false;"') + '><i class="fas ' + esc(icon) + '"></i><span>' + label + '</span></a>';}).join('')+'</div>';}).join('')+'</div><div class="sidebar-footer"><div><strong>' + esc(StoreConfig.getStoreName()) + '</strong><span>Secure POS Session</span></div><i class="fas fa-shield-alt"></i></div>';
    }
    function renderUserMenu() {
        var el = $('userMenu');
        if (!el) return;
        var name = API.getUserName ? API.getUserName() : 'Admin User';
        var role = API.getRole ? API.getRole() : 'admin';
        var pharm = API.getPharmacyName ? API.getPharmacyName() : 'SHEDS POS';
        el.innerHTML = '<span class="user-avatar"><i class="fas fa-user"></i></span><div class="user-text"><strong>' + esc(name || 'Admin User') + '</strong><small>' + esc(role || 'Role') + '</small></div><i class="fas fa-chevron-down"></i><div class="user-dropdown"><div class="user-info"><strong>' + esc(name || 'Admin User') + '</strong><small>' + esc(pharm || 'SHEDS POS') + '</small></div><hr><a href="#" onclick="POS.navigateTo(\'config.html\');return false;"><i class="fas fa-cog"></i> Settings</a><a href="#" onclick="POS.navigateTo(\'payments.html\');return false;"><i class="fas fa-credit-card"></i> Store Payments</a><a href="#" onclick="POS.switchToAdmin();return false;"><i class="fas fa-user-shield"></i> Switch to Admin</a><hr><a href="#" onclick="POS.logout();return false;"><i class="fas fa-sign-out-alt"></i> Logout</a></div>';
    }
    function switchToAdmin() {
        if (API.init) API.init('', '', '', { name: 'Admin User', role: 'admin' }, '');
        renderUserMenu();
        showToast('Switched to Admin User');
    }
    function logout() {
        if (!confirm('Are you sure you want to logout?')) return;
        if (API.logout) API.logout();
        navigateTo('login.html');
    }
    function statusBadge(status, extraClass) {
        var s = String(status || '').toLowerCase();
        var cls = 'badge';
        if (extraClass) cls += ' ' + extraClass;
        else if (['active', 'paid', 'completed', 'delivered', 'scheduled', 'read', 'in_stock', 'high', 'confirmed'].indexOf(s) > -1) cls += ' badge-success';
        else if (['inactive', 'cancelled', 'expired', 'used', 'outstanding', 'overdue', 'delayed', 'low', 'out', 'unread', 'pending', 'draft', 'partial'].indexOf(s) > -1) cls += ' badge-warning';
        else cls += ' badge-info';
        return '<span class="' + cls + '">' + esc(status || 'Draft') + '</span>';
    }
    function debounce(fn, delay) {
        var t;
        return function() {
            var args = arguments;
            clearTimeout(t);
            t = setTimeout(function() { fn.apply(null, args); }, delay || 250);
        };
    }
function startClock() {
    var el = $('topClock');
    if (!el) return;
    function update() {
        var now = new Date();
        el.innerHTML = '<i class="fas fa-clock"></i> ' + now.toLocaleString('en-NG', {
            weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    }
    update();
    setInterval(update, 1000);
}
function checkSubscription() {
    var page = window.location.pathname.split('/').pop();
    if (window.location.protocol === 'file:') return;
    if (['subscription.html', 'login.html', 'create-account.html'].indexOf(page) !== -1) return;
    var sub = null;
    var trial = null;
    try { 
        sub = JSON.parse(localStorage.getItem('danzona_subscription') || 'null'); 
        trial = JSON.parse(localStorage.getItem('danzona_trial') || 'null');
    } catch(e) { sub = null; trial = null; }
    
    var isActive = sub && sub.status === 'active';
    var isTrial = trial && trial.status === 'active' && new Date(trial.endDate) >= new Date();
    
    if (isTrial) {
        return;
    } else if (!isActive) {
        var overlay = document.createElement('div');
        overlay.id = 'subscriptionLock';
        overlay.style.cssText = 'position:fixed;inset:0;background:linear-gradient(135deg,#0f172a,#1e293b);z-index:99999;display:flex;align-items:center;justify-content:center;color:#fff;font-family:Inter,Arial,sans-serif;';
        overlay.innerHTML = '<div style="text-align:center;max-width:480px;padding:40px;"><div style="font-size:60px;margin-bottom:20px;"><i class="fas fa-lock" style="color:#ef4444;"></i></div><h1 style="font-size:28px;font-weight:900;margin-bottom:12px;">Subscription Required</h1><p style="color:#94a3b8;font-size:15px;margin-bottom:24px;">Your free trial has ended. Please subscribe to continue using ' + esc(StoreConfig.getStoreName()) + '.</p><button onclick="window.location.href=\'subscription.html\'" style="background:#10b981;color:#fff;border:none;padding:14px 32px;border-radius:10px;font-size:16px;font-weight:800;cursor:pointer;display:inline-flex;align-items:center;gap:8px;"><i class="fas fa-calendar-check"></i> Go to Subscription</button></div>';
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';
    }
}
function initCommon() {
    renderSidebar();
    renderUserMenu();
    startClock();
    checkSubscription();
    applyAppearanceSettings();
    var name = $('pharmacyName') || $('pharmacyNameDisplay');
    if (name && API.getPharmacyName) name.innerHTML = '<i class="fas fa-clinic-medical"></i> ' + esc(API.getPharmacyName() || 'SHEDS POS');
}
function applyAppearanceSettings() {
    try {
        var cfg = StoreConfig.getAll();
        var body = document.body;
        if (!body) return;

        if (cfg.themeMode === 'dark') body.classList.add('theme-dark');
        else body.classList.remove('theme-dark');

        if (cfg.sidebarMode === 'collapsed') { body.classList.add('sidebar-collapsed'); body.classList.remove('sidebar-mini'); }
        else if (cfg.sidebarMode === 'mini') { body.classList.add('sidebar-mini'); body.classList.remove('sidebar-collapsed'); }
        else { body.classList.remove('sidebar-collapsed', 'sidebar-mini'); }

        if (cfg.compactMode) body.classList.add('compact-mode');
        else body.classList.remove('compact-mode');

        if (cfg.enableAnimations === false) body.classList.add('no-animations');
        else body.classList.remove('no-animations');

        if (cfg.fontFamily) document.documentElement.style.setProperty('--app-font', cfg.fontFamily);
        if (cfg.primaryColor) document.documentElement.style.setProperty('--app-primary', cfg.primaryColor);
        if (cfg.baseFontSize) document.documentElement.style.fontSize = cfg.baseFontSize + 'px';
        if (cfg.borderRadius) document.documentElement.style.setProperty('--app-radius', cfg.borderRadius);
        if (cfg.shadowIntensity === 'none') document.documentElement.style.setProperty('--app-shadow', 'none');
        else if (cfg.shadowIntensity === 'light') document.documentElement.style.setProperty('--app-shadow', '0 1px 2px rgba(0,0,0,0.04)');
        else if (cfg.shadowIntensity === 'heavy') document.documentElement.style.setProperty('--app-shadow', '0 20px 50px rgba(0,0,0,0.15)');
        else document.documentElement.style.setProperty('--app-shadow', '0 12px 30px rgba(15,23,42,.08)');

        var kpiGrid = document.querySelector('.kpi-grid');
        if (kpiGrid) {
            kpiGrid.classList.remove('density-compact', 'density-comfortable');
            if (cfg.tableDensity === 'compact') kpiGrid.classList.add('density-compact');
            else if (cfg.tableDensity === 'comfortable') kpiGrid.classList.add('density-comfortable');
        }

        var fastStats = document.querySelector('.fast-stats');
        if (fastStats) {
            fastStats.classList.remove('density-compact', 'density-comfortable');
            if (cfg.tableDensity === 'compact') fastStats.classList.add('density-compact');
            else if (cfg.tableDensity === 'comfortable') fastStats.classList.add('density-comfortable');
            var cols = cfg.dashboardCardsPerRow || '4';
            fastStats.style.gridTemplateColumns = 'repeat(' + cols + ', minmax(160px, 1fr))';
        }

        var header = document.querySelector('.header');
        if (header) {
            header.classList.remove('header-gradient', 'header-solid', 'header-minimal');
            if (cfg.headerStyle === 'gradient') header.classList.add('header-gradient');
            else if (cfg.headerStyle === 'solid') header.classList.add('header-solid');
            else if (cfg.headerStyle === 'minimal') header.classList.add('header-minimal');
            header.style.background = '';
            header.style.color = '';
        }

        if (cfg.contentWidth === 'boxed') { body.classList.add('content-boxed'); body.classList.remove('content-narrow'); }
        else if (cfg.contentWidth === 'narrow') { body.classList.add('content-narrow'); body.classList.remove('content-boxed'); }
        else { body.classList.remove('content-boxed', 'content-narrow'); }

        if (cfg.cardStyle === 'shadow') document.body.classList.add('card-shadow-body');
        else if (cfg.cardStyle === 'bordered') document.body.classList.add('card-bordered-body');
        else document.body.classList.add('card-flat-body');

        if (cfg.tableStyle === 'striped') document.body.classList.add('table-striped');
        else document.body.classList.remove('table-striped');
        if (cfg.tableStyle === 'minimal') document.body.classList.add('table-minimal');
        else document.body.classList.remove('table-minimal');
        if (cfg.tableStyle === 'bordered') document.body.classList.add('table-bordered');
        else document.body.classList.remove('table-bordered');

        if (cfg.customCSS) {
            var styleEl = document.getElementById('custom-store-css');
            if (!styleEl) { styleEl = document.createElement('style'); styleEl.id = 'custom-store-css'; document.head.appendChild(styleEl); }
            styleEl.textContent = cfg.customCSS;
        } else {
            var existing = document.getElementById('custom-store-css');
            if (existing) existing.remove();
        }
    } catch (e) {
        console.error('applyAppearanceSettings error:', e);
    }
}
window.POS.applyAppearanceSettings = applyAppearanceSettings;
    function requireAuth() {
        if (API.isLoggedIn && API.isLoggedIn()) return true;
        if (getQueryParameter('demo') === '1') return true;
        navigateTo('login.html');
        return false;
    }
    function getPrinterType(){try{return StoreConfig.get('printerType')||'small';}catch(e){return 'small';}}
    function getReceiptConfig(){try{return{footerText:StoreConfig.get('footerText')||'Thank you for choosing SHEDS POS!',storeName:StoreConfig.getPharmacyName(),storeAddress:StoreConfig.get('storeAddress')||'',phone:StoreConfig.get('phoneNumber')||''};}catch(e){return{footerText:'Thank you for choosing SHEDS POS!',storeName:'SHEDS POS',storeAddress:'',phone:''};}}
    function fmt(v){try{return StoreConfig.formatCurrency(v);}catch(e){return '₦'+(parseFloat(v)||0).toLocaleString('en-NG',{minimumFractionDigits:2});}}
    function buildSmallReceipt(cart,sub,disc,total,tendered,paymentMethod){var pmLabel=paymentMethod==='store_account'?'Store Account':paymentMethod==='card'?'Card':paymentMethod==='pos'?'POS':paymentMethod==='giftcard'?'Gift Card':'Cash';var rc=getReceiptConfig();var html='<html><head><title>Receipt</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:"Courier New",monospace;font-size:14px;color:#000;width:100%;padding:20px;background:#fff;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}.receipt{max-width:380px;margin:0 auto}.center{text-align:center}.left{text-align:left}.right{text-align:right}.line{border-bottom:1px dashed #000;margin:10px 0;padding:6px 0}.item-row{display:flex;justify-content:space-between;margin:6px 0}.totals{display:flex;justify-content:space-between;font-weight:bold;font-size:16px;margin-top:10px}.footer{margin-top:14px;font-size:12px;text-align:center;color:#333}@media print{@page{size:80mm auto;margin:0}}</style></head><body>';html+='<div class="receipt"><div class="center"><h2 style="font-size:16px;margin:0;">'+esc(rc.storeName)+'</h2>';if(rc.storeAddress){html+='<div style="font-size:10px;margin-top:4px;">'+esc(rc.storeAddress)+'</div>';}if(rc.phone){html+='<div style="font-size:10px;">'+esc(rc.phone)+'</div>';}html+='<div style="font-size:10px;margin-top:4px;">Date: '+(new Date()).toLocaleString()+'</div><div style="font-size:10px;">Receipt: #POS'+Date.now().toString().slice(-6)+'</div><div style="font-size:10px;">Cashier: '+esc(API.getUserName?API.getUserName():'Staff')+'</div></div><div class="line"></div><div style="font-weight:bold;margin:8px 0;">Items Purchased</div>';cart.forEach(function(it){var lt=(parseFloat(it.price)||0)*(parseFloat(it.qty)||0)-(parseFloat(it.discount)||0);html+='<div class="item-row"><span class="left">'+esc(it.name)+'</span><span class="right">'+esc(it.qty)+' x '+fmt(lt)+'</span></div>';if(it.discount>0){html+='<div class="item-row" style="font-size:10px;color:#666;"><span class="left">Discount</span><span class="right">-'+fmt(it.discount)+'</span></div>';}});html+='<div class="line"></div><div class="totals"><span>Total</span><span>'+fmt(total)+'</span></div>';if(pmLabel!=='Cash'){html+='<div class="item-row"><span class="left">Payment Method</span><span class="right">'+esc(pmLabel)+'</span></div>';}if(tendered>0||pmLabel==='Store Account'){html+='<div class="totals"><span>Amount Paid</span><span>'+fmt(pmLabel==='Store Account'?total:tendered)+'</span></div>';html+='<div class="totals"><span>Change</span><span>'+fmt(Math.max(0,(pmLabel==='Store Account'?total:tendered)-total))+'</span></div>';}html+='<div class="line"></div><div class="center footer">'+esc(rc.footerText)+'</div></div></body></html>';return html;}
    function buildLargeReceipt(cart,sub,disc,total,tendered,paymentMethod){var pmLabel=paymentMethod==='store_account'?'Store Account':paymentMethod==='card'?'Card':paymentMethod==='pos'?'POS':paymentMethod==='giftcard'?'Gift Card':'Cash';var rc=getReceiptConfig();var html='<html><head><title>Receipt</title><style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#000;padding:32px;background:#fff;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}.r-header{text-align:center;margin-bottom:20px}.r-header h1{font-size:22px;font-weight:900;text-transform:uppercase;color:#000}.r-header p{font-size:14px;color:#333;margin-top:4px}.r-section{margin-bottom:18px}.r-section h3{font-size:14px;font-weight:800;text-transform:uppercase;color:#000;border-bottom:2px solid #000;padding-bottom:6px;margin-bottom:10px}.r-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px}.r-grid div{font-size:14px}.r-grid .r-label{color:#555}.r-grid .r-value{font-weight:700;text-align:right}table{width:100%;border-collapse:collapse;margin-bottom:10px}th{background:#f1f5f9;text-align:left;padding:8px 10px;font-size:12px;font-weight:800;text-transform:uppercase;color:#333;border-bottom:2px solid #000}td{padding:8px 10px;font-size:14px;border-bottom:1px solid #e5e7eb}.r-total{font-weight:900;color:#000}.r-footer{text-align:center;margin-top:14px;font-size:12px;color:#555}</style></head><body>';html+='<div class="r-header"><h1>'+esc(rc.storeName)+'</h1>';if(rc.storeAddress){html+='<p>'+esc(rc.storeAddress)+'</p>';}if(rc.phone){html+='<p>Phone: '+esc(rc.phone)+'</p>';}html+='<p>Date: '+(new Date()).toLocaleString()+'</p><p>Cashier: '+esc(API.getUserName?API.getUserName():'Staff')+'</p><p>Receipt: #POS'+Date.now().toString().slice(-6)+'</p></div>';html+='<div class="r-section"><h3>Items Sold</h3><table><thead><tr><th>Item Name</th><th style="text-align:right">Price</th><th style="text-align:center">Qty</th><th style="text-align:right">Total</th></tr></thead><tbody>';var totalQty=0;cart.forEach(function(it){var lt=(parseFloat(it.price)||0)*(parseFloat(it.qty)||0)-(parseFloat(it.discount)||0);totalQty+=parseFloat(it.qty)||0;html+='<tr><td>'+esc(it.name)+'</td><td style="text-align:right">'+fmt(it.price)+'</td><td style="text-align:center">'+esc(it.qty)+'</td><td style="text-align:right" class="r-total">'+fmt(lt)+'</td></tr>';});html+='</tbody></table></div>';html+='<div class="r-section"><h3>Sales Summary</h3><div class="r-grid"><div><span class="r-label">Subtotal:</span> <span class="r-value">'+fmt(sub)+'</span></div><div><span class="r-label">Sales Tax:</span> <span class="r-value">'+fmt(0)+' (0.000%)</span></div><div class="r-total"><span class="r-label">Total Amount:</span> <span class="r-value">'+fmt(total)+'</span></div><div><span class="r-label">Number of Items:</span> <span class="r-value">'+totalQty+'</span></div></div></div>';html+='<div class="r-section"><h3>Payment Information</h3><div class="r-grid"><div><span class="r-label">Payment Type:</span> <span class="r-value">'+esc(pmLabel)+'</span></div><div><span class="r-label">Amount Paid:</span> <span class="r-value">'+fmt(pmLabel==='Store Account'?total:tendered)+'</span></div><div><span class="r-label">Change Due:</span> <span class="r-value">'+fmt(Math.max(0,(pmLabel==='Store Account'?total:tendered)-total))+'</span></div></div></div>';html+='<div class="r-footer">'+esc(rc.footerText)+'</div></body></html>';return html;}
    return {
        $: $, esc: esc, navigateTo: navigateTo, formatCurrency: formatCurrency, formatNumber: formatNumber, formatDate: formatDate, today: today, getQueryParameter: getQueryParameter, showToast: showToast, openModal: openModal, closeModal: closeModal, exportCSV: exportCSV, printTable: printTable, renderSidebar: renderSidebar, renderUserMenu: renderUserMenu, switchToAdmin: switchToAdmin, logout: logout, statusBadge: statusBadge, debounce: debounce, initCommon: initCommon, requireAuth: requireAuth, getPrinterType: getPrinterType, buildSmallReceipt: buildSmallReceipt, buildLargeReceipt: buildLargeReceipt, fmt: fmt, startClock: startClock
    };
})();
window.POS = POS;
document.addEventListener('DOMContentLoaded', function() { POS.initCommon(); });
