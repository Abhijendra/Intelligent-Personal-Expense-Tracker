// main.js — students will add JavaScript here as features are built

function refreshCategories() {
    var btn = document.getElementById('refresh-btn');
    if (!btn || btn.disabled) return;

    btn.disabled = true;
    btn.classList.add('is-loading');

    fetch('/refresh-categories', { method: 'POST' })
        .then(function(res) { return res.json(); })
        .then(function(data) {
            if (data.status === 'ok') {
                window.location.reload();
            } else {
                btn.disabled = false;
                btn.classList.remove('is-loading');
            }
        })
        .catch(function() {
            btn.disabled = false;
            btn.classList.remove('is-loading');
        });
}

function applyToggle(showAll) {
    var rows = document.querySelectorAll('.mock-bar-row');
    var container = document.getElementById('mock-bars-container');
    rows.forEach(function(row) {
        var idx = parseInt(row.getAttribute('data-index'), 10);
        row.style.display = (!showAll && idx > 5) ? 'none' : '';
    });
    if (container) {
        if (showAll && rows.length > 5) {
            container.classList.add('mock-bars--overflow');
        } else {
            container.classList.remove('mock-bars--overflow');
        }
    }
}

function initCategoryToggle() {
    var checkbox = document.getElementById('show-all-categories');
    if (!checkbox) return;
    var saved = localStorage.getItem('spendly_show_all_categories') === 'true';
    checkbox.checked = saved;
    applyToggle(saved);
    checkbox.addEventListener('change', function() {
        localStorage.setItem('spendly_show_all_categories', this.checked);
        applyToggle(this.checked);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initCategoryToggle();
});
