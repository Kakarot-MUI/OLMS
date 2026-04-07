/* ── Theme Switcher ─────────────────────────────────────────────
   Handles dark/light theme toggle with localStorage persistence.
   ═══════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

    // ── Password show/hide toggle ─────────────────────────────────
    document.querySelectorAll('input[type="password"]').forEach(function (input) {
        var wrapper = document.createElement('div');
        wrapper.className = 'input-group';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-outline-secondary';
        btn.style.borderColor = 'var(--border-color)';
        btn.innerHTML = '<i class="bi bi-eye"></i>';
        btn.title = 'Show password';
        wrapper.appendChild(btn);

        btn.addEventListener('click', function () {
            var icon = btn.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.className = 'bi bi-eye-slash';
                btn.title = 'Hide password';
            } else {
                input.type = 'password';
                icon.className = 'bi bi-eye';
                btn.title = 'Show password';
            }
        });
    });

    // ── Auto-dismiss flash messages after 5 seconds ───────────────
    const alerts = document.querySelectorAll('.flash-container .alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // ── Sidebar toggle for mobile ─────────────────────────────────
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('show');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function (e) {
            if (window.innerWidth < 992) {
                if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                    sidebar.classList.remove('show');
                }
            }
        });
    }

    // ── Confirm delete dialogs ────────────────────────────────────
    const deleteForms = document.querySelectorAll('form[data-confirm]');
    deleteForms.forEach(function (form) {
        form.addEventListener('submit', function (e) {
            const message = form.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // ── Active nav link highlighting ──────────────────────────────
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar-nav a, .navbar-nav .nav-link').forEach(function (link) {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // ── Theme Switcher ─────────────────────────────────────────────
    const html = document.documentElement;
    const updateTheme = (theme) => {
        html.setAttribute('data-theme', theme);
        html.setAttribute('data-bs-theme', theme);
        localStorage.setItem('olms-theme', theme);

        // Sync all switches
        document.querySelectorAll('#darkModeSwitch, .theme-toggle-mobile').forEach(sw => {
            sw.checked = (theme === 'dark');
        });
    };

    const savedTheme = localStorage.getItem('olms-theme') || 'light';
    updateTheme(savedTheme);

    // Handle button clicks (traditional dropdown items)
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            updateTheme(btn.getAttribute('data-theme-value'));
        });
    });

    // Handle switch toggles (new dropdown switch)
    document.querySelectorAll('#darkModeSwitch, .theme-toggle-mobile').forEach(sw => {
        sw.addEventListener('change', () => {
            updateTheme(sw.checked ? 'dark' : 'light');
        });
    });
});

/* ── Web Push Notifications ──────────────────────────────────────
   Handles user permission, subscription generation, and backend sync.
   ═══════════════════════════════════════════════════════════════════ */

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(function (reg) {
            console.log('Service Worker Registered on scope:', reg.scope);
        }).catch(function (err) {
            console.error('Service Worker registration failed:', err);
        });
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function subscribeUserToPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.warn('Push messaging is not supported.');
        return;
    }

    try {
        // IMPORTANT: Request permission FIRST to preserve the user gesture context
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            console.log('Permission not granted for Notification');
            return;
        }

        const registration = await navigator.serviceWorker.ready;

        // Fetch the VAPID public key from our backend
        const response = await fetch('/api/push/vapid_public_key');
        if (!response.ok) throw new Error('Could not fetch VAPID key');

        const data = await response.json();
        const convertedVapidKey = urlBase64ToUint8Array(data.public_key);

        // Subscribe the user using the VAPID key
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: convertedVapidKey
        });

        // Retrieve the CSRF token to prevent Flask from rejecting the POST request
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : '';

        // Send the subscription details to our Flask backend to save in the database
        await fetch('/api/push/subscribe', {
            method: 'POST',
            body: JSON.stringify(subscription),
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });

        console.log('User is subscribed to Push Notifications.');
        
        // Show a simple visual confirmation since the browser popup only appears once
        alert('🔔 Notifications Enabled! You will now receive alerts for messages and due books.');

    } catch (error) {
        console.error('Failed to subscribe the user: ', error);
    }
}

// Execute subscription logic when page loads
document.addEventListener('DOMContentLoaded', function () {
    if ('Notification' in window && Notification.permission === 'granted') {
        // Automatically sync subscription if they already granted permission in the past
        subscribeUserToPush();
    }

    // Explicitly bind the click event to any button with the enable-push-btn class
    document.querySelectorAll('.enable-push-btn').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            subscribeUserToPush();
        });
    });
});
