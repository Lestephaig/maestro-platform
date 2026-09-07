from django.test import SimpleTestCase

from core.settings import validate_telegram_delivery_api_url


class TelegramDeliveryApiUrlValidationTests(SimpleTestCase):
    def test_production_accepts_https_url(self):
        validate_telegram_delivery_api_url(
            'https://bot.example/internal/v1/telegram/messages',
            debug=False,
            allow_insecure_http=False,
        )

    def test_development_accepts_http_url(self):
        validate_telegram_delivery_api_url(
            'http://127.0.0.1:8080/internal/v1/telegram/messages',
            debug=True,
            allow_insecure_http=False,
        )

    def test_production_requires_explicit_http_opt_in(self):
        with self.assertRaisesMessage(
            ValueError,
            'TELEGRAM_DELIVERY_ALLOW_INSECURE_HTTP=True',
        ):
            validate_telegram_delivery_api_url(
                'http://8.8.8.8:8080/internal/v1/telegram/messages',
                debug=False,
                allow_insecure_http=False,
            )

    def test_production_opt_in_accepts_public_ip(self):
        validate_telegram_delivery_api_url(
            'http://8.8.8.8:8080/internal/v1/telegram/messages',
            debug=False,
            allow_insecure_http=True,
        )

    def test_production_opt_in_rejects_hostname_and_non_public_ip(self):
        invalid_urls = (
            'http://bot.example:8080/internal/v1/telegram/messages',
            'http://127.0.0.1:8080/internal/v1/telegram/messages',
            'http://10.0.0.1:8080/internal/v1/telegram/messages',
        )
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaisesMessage(
                ValueError,
                'must use a public IP address',
            ):
                validate_telegram_delivery_api_url(
                    url,
                    debug=False,
                    allow_insecure_http=True,
                )
