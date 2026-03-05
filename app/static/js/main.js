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
