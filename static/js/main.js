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
