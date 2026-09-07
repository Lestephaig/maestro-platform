const test = require('node:test');
const assert = require('node:assert/strict');

const {initTelegramLinkBanner} = require('../../static/js/telegram-link-banner.js');

class EventTarget {
    constructor(properties = {}) {
        Object.assign(this, properties);
        this.listeners = {};
    }

    addEventListener(name, listener) {
        this.listeners[name] = this.listeners[name] || [];
        this.listeners[name].push(listener);
    }

    async emit(name) {
        await Promise.all((this.listeners[name] || []).map((listener) => listener()));
    }
}

function response(data, ok = true) {
    return {ok, json: async () => data};
}

function fixture(fetch) {
    const elements = {
        telegramLinkBanner: new EventTarget({
            hidden: false,
            dataset: {
                statusUrl: '/status/',
                createUrl: '/create/',
                dismissUrl: '/dismiss/',
                csrfToken: 'csrf-token',
            },
        }),
        telegramLinkBannerCta: new EventTarget({disabled: false}),
        telegramLinkBannerClose: new EventTarget({disabled: false}),
        telegramLinkBannerStatus: new EventTarget({textContent: ''}),
    };
    const document = new EventTarget({
        visibilityState: 'visible',
        getElementById: (id) => elements[id],
    });
    const assigned = [];
    const window = new EventTarget({
        location: {assign: (url) => assigned.push(url)},
        setInterval: () => 7,
        clearInterval: () => {},
    });
    const controller = initTelegramLinkBanner(document, window, fetch);
    return {elements, document, window, assigned, controller};
}

test('close persists dismissal and hides the banner', async () => {
    const calls = [];
    const page = fixture(async (url, options = {}) => {
        calls.push({url, options});
        if (url === '/dismiss/') return response({dismissed: true});
        return response({linked: false});
    });

    await page.elements.telegramLinkBannerClose.emit('click');

    assert.equal(page.elements.telegramLinkBanner.hidden, true);
    const dismissCall = calls.find((call) => call.url === '/dismiss/');
    assert.equal(dismissCall.options.method, 'POST');
    assert.equal(dismissCall.options.headers['X-CSRFToken'], 'csrf-token');
});

test('CTA uses the existing create endpoint and opens its deep link', async () => {
    const calls = [];
    const page = fixture(async (url, options = {}) => {
        calls.push({url, options});
        if (url === '/create/') return response({url: 'https://t.me/MaestroTestBot?start=token'});
        return response({linked: false});
    });

    await page.elements.telegramLinkBannerCta.emit('click');

    assert.deepEqual(page.assigned, ['https://t.me/MaestroTestBot?start=token']);
    const createCall = calls.find((call) => call.url === '/create/');
    assert.equal(createCall.options.method, 'POST');
    assert.equal(createCall.options.headers['X-CSRFToken'], 'csrf-token');
});

test('linked status hides the banner without a page reload', async () => {
    const page = fixture(async () => response({linked: true}));

    await page.controller.refreshStatus();

    assert.equal(page.elements.telegramLinkBanner.hidden, true);
});
