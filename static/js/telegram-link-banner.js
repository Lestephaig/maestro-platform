(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root && root.document) api.initTelegramLinkBanner(root.document, root, root.fetch.bind(root));
}(typeof window !== 'undefined' ? window : null, function () {
    function initTelegramLinkBanner(document, window, fetch) {
        const banner = document.getElementById('telegramLinkBanner');
        if (!banner) return null;

        const cta = document.getElementById('telegramLinkBannerCta');
        const close = document.getElementById('telegramLinkBannerClose');
        const status = document.getElementById('telegramLinkBannerStatus');
        let pollTimer = null;

        function hide() {
            banner.hidden = true;
            if (pollTimer !== null) window.clearInterval(pollTimer);
            pollTimer = null;
        }

        async function readJson(response) {
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || 'Не удалось выполнить запрос.');
            return data;
        }

        async function refreshStatus() {
            if (banner.hidden) return false;
            try {
                const response = await fetch(banner.dataset.statusUrl, {
                    headers: {'Accept': 'application/json'},
                    credentials: 'same-origin',
                });
                const data = await readJson(response);
                if (data.linked) hide();
                return data.linked;
            } catch (error) {
                return false;
            }
        }

        close.addEventListener('click', async function () {
            close.disabled = true;
            try {
                await readJson(await fetch(banner.dataset.dismissUrl, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'X-CSRFToken': banner.dataset.csrfToken,
                    },
                    credentials: 'same-origin',
                }));
                hide();
            } catch (error) {
                status.textContent = error.message;
                close.disabled = false;
            }
        });

        cta.addEventListener('click', async function () {
            cta.disabled = true;
            status.textContent = 'Создаём безопасную ссылку…';
            try {
                const data = await readJson(await fetch(banner.dataset.createUrl, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'X-CSRFToken': banner.dataset.csrfToken,
                    },
                    credentials: 'same-origin',
                }));
                pollTimer = window.setInterval(refreshStatus, 3000);
                window.location.assign(data.url);
            } catch (error) {
                status.textContent = error.message;
                cta.disabled = false;
            }
        });

        window.addEventListener('focus', refreshStatus);
        window.addEventListener('pageshow', refreshStatus);
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'visible') refreshStatus();
        });
        refreshStatus();

        return {hide: hide, refreshStatus: refreshStatus};
    }

    return {initTelegramLinkBanner: initTelegramLinkBanner};
}));
