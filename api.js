/* SHEDS POS - API Client
 * Multi-tenant API using X-API-Key authentication.
 * Usage: API.init(apiKey, username); then API.get('/products'), API.post('/sales', data), etc.
 */
var API = (function() {
    var BASE_URL = (typeof window !== 'undefined' && window.__API_BASE_URL) ? window.__API_BASE_URL : '/api';
    var apiKey = localStorage.getItem('danzona_api_key') || '';
    var username = localStorage.getItem('danzona_username') || '';
    var pharmacyName = localStorage.getItem('danzona_pharmacy_name') || '';
    var currentUser = null;
    try {
        var raw = localStorage.getItem('danzona_current_user');
        if (raw) currentUser = JSON.parse(raw);
    } catch (e) {
        currentUser = null;
    }

    function headers() {
        var h = { 'Content-Type': 'application/json' };
        if (apiKey) h['X-API-Key'] = apiKey;
        if (username) h['X-Username'] = username;
        return h;
    }

    function request(method, path, data) {
        return fetch(BASE_URL + path, {
            method: method,
            headers: headers(),
            body: data ? JSON.stringify(data) : null
        }).then(function(res) {
            if (res.status === 401) {
                logout();
                window.location.href = 'login.html';
                return Promise.reject(new Error('Session expired'));
            }
            if (!res.ok) {
                return res.json().then(function(err) {
                    return Promise.reject(new Error(err.error || 'Request failed'));
                }).catch(function() {
                    return Promise.reject(new Error('Request failed: ' + res.status));
                });
            }
            return res.json();
        });
    }

    return {
        init: function(key, uname, pharmName, user, storeId) {
            if (key) localStorage.setItem('danzona_api_key', key);
            if (uname) localStorage.setItem('danzona_username', uname);
            if (pharmName) localStorage.setItem('danzona_pharmacy_name', pharmName);
            if (user) localStorage.setItem('danzona_current_user', JSON.stringify(user));
            if (storeId) localStorage.setItem('danzona_store_id', storeId);
            apiKey = key || apiKey;
            username = uname || username;
            pharmacyName = pharmName || pharmacyName;
            currentUser = user || currentUser;
        },

        isLoggedIn: function() {
            return !!apiKey && !!username;
        },

        getRole: function() {
            if (currentUser && currentUser.role) return currentUser.role;
            return 'staff';
        },

        getUserName: function() {
            if (currentUser && currentUser.name) return currentUser.name;
            return username;
        },

        getPharmacyName: function() {
            return pharmacyName;
        },

        logout: function() {
            localStorage.removeItem('danzona_api_key');
            localStorage.removeItem('danzona_username');
            localStorage.removeItem('danzona_pharmacy_name');
            localStorage.removeItem('danzona_current_user');
            apiKey = '';
            username = '';
            pharmacyName = '';
            currentUser = null;
        },

        get: function(path) { return request('GET', path); },
        post: function(path, data) { return request('POST', path, data); },
        put: function(path, data) { return request('PUT', path, data); },
        delete: function(path) { return request('DELETE', path); },

        // Auth
        registerPharmacy: function(data) {
            return fetch(BASE_URL + '/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(function(res) { return res.json(); });
        },
        login: function(apiKeyVal, uname, pwd) {
            return fetch(BASE_URL + '/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKeyVal, username: uname, password: pwd })
            }).then(function(res) { return res.json(); });
        },
        staffLogin: function(uname, pwd) {
            return fetch(BASE_URL + '/auth/staff-login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: uname, password: pwd })
            }).then(function(res) { return res.json(); });
        },

        // Products
        getProducts: function() { return this.get('/products'); },
        saveProduct: function(data) { return this.post('/products', data); },
        updateProduct: function(id, data) { return this.put('/products/' + id, data); },
        deleteProduct: function(id) { return this.delete('/products/' + id); },

        // Sales
        getSales: function() { return this.get('/sales'); },
        saveSale: function(data) { return this.post('/sales', data); },
        getSale: function(id) { return this.get('/sales/' + id); },

        // Customers
        getCustomers: function() { return this.get('/customers'); },
        saveCustomer: function(data) { return this.post('/customers', data); },
        updateCustomer: function(id, data) { return this.put('/customers/' + id, data); },
        deleteCustomer: function(id) { return this.delete('/customers/' + id); },

        // Employees
        getEmployees: function() { return this.get('/employees'); },
        saveEmployee: function(data) { return this.post('/employees', data); },
        updateEmployee: function(id, data) { return this.put('/employees/' + id, data); },
        deleteEmployee: function(id) { return this.delete('/employees/' + id); },

        // Inventory
        getInventory: function() { return this.get('/inventory'); },
        saveInventory: function(data) { return this.post('/inventory', data); },
        updateInventory: function(id, data) { return this.put('/inventory/' + id, data); },

        // Expenses
        getExpenses: function() { return this.get('/expenses'); },
        saveExpense: function(data) { return this.post('/expenses', data); },
        deleteExpense: function(id) { return this.delete('/expenses/' + id); },

        // Payments
        getPayments: function() { return this.get('/payments'); },
        savePayment: function(data) { return this.post('/payments', data); },
        updatePayment: function(id, data) { return this.put('/payments/' + id, data); },
        deletePayment: function(id) { return this.delete('/payments/' + id); },

        // Locations
        getLocations: function() { return this.get('/locations'); },
        saveLocation: function(data) { return this.post('/locations', data); },
        updateLocation: function(id, data) { return this.put('/locations/' + id, data); },
        deleteLocation: function(id) { return this.delete('/locations/' + id); },

        // Appointments
        getAppointments: function() { return this.get('/appointments'); },
        saveAppointment: function(data) { return this.post('/appointments', data); },
        updateAppointment: function(id, data) { return this.put('/appointments/' + id, data); },
        deleteAppointment: function(id) { return this.delete('/appointments/' + id); },

        // Gift Cards
        getGiftCards: function() { return this.get('/giftcards'); },
        saveGiftCard: function(data) { return this.post('/giftcards', data); },
        updateGiftCard: function(id, data) { return this.put('/giftcards/' + id, data); },
        deleteGiftCard: function(id) { return this.delete('/giftcards/' + id); },

        // Messages
        getMessages: function() { return this.get('/messages'); },
        saveMessage: function(data) { return this.post('/messages', data); },
        deleteMessage: function(id) { return this.delete('/messages/' + id); },

        // Deliveries
        getDeliveries: function() { return this.get('/deliveries'); },
        saveDelivery: function(data) { return this.post('/deliveries', data); },

        // Invoices
        getInvoices: function() { return this.get('/invoices'); },
        saveInvoice: function(data) { return this.post('/invoices', data); },

        // Dashboard
        getDashboard: function() { return this.get('/dashboard'); },

        // Users/Staff
        getUsers: function() { return this.get('/users'); },
        registerStaff: function(data) { return this.post('/users/register', data); },
        updateUser: function(id, data) { return this.put('/users/' + id, data); },
        deleteUser: function(id) { return this.delete('/users/' + id); },

        // Suppliers
        getSuppliers: function() { return this.get('/suppliers'); },
        saveSupplier: function(data) { return this.post('/suppliers', data); },
        updateSupplier: function(id, data) { return this.put('/suppliers/' + id, data); },
        deleteSupplier: function(id) { return this.delete('/suppliers/' + id); },

        // Catalogue
        getCatalogue: function() { return this.get('/catalogue'); }
    };
})();
