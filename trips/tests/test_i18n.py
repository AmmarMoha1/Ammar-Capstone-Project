"""The Arabic version (/ar/): right-to-left layout, translated text, plurals and number formats."""

from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from trips.services.recommendations import generate_recommendations

from .helpers import make_origin, make_trip, make_user
from .test_recommendations import RecommendationTestCase


class ResetLanguageMixin:
    """Arabic requests leave Arabic active in the test thread; switch back so later tests reverse English URLs."""

    def tearDown(self):
        translation.activate(settings.LANGUAGE_CODE)
        super().tearDown()


class LanguageVersionTests(ResetLanguageMixin, TestCase):
    def test_english_is_the_default_without_a_prefix(self):
        response = self.client.get("/")

        self.assertContains(response, '<html lang="en" dir="ltr"', html=False)
        self.assertContains(response, 'href="/ar/"')  # the switch to the Arabic version

    def test_arabic_home_is_right_to_left_and_translated(self):
        response = self.client.get("/ar/")

        self.assertContains(response, '<html lang="ar" dir="rtl"', html=False)
        self.assertContains(response, "وين")
        self.assertContains(response, "تبليسي")  # catalog city through the |tr filter
        self.assertNotContains(response, "Everyone has a preference")
        self.assertContains(response, 'href="/"')  # the switch back to English

    def test_arabic_urls_reverse_with_prefix(self):
        translation.activate(settings.LANGUAGE_CODE)
        with translation.override("ar"):
            self.assertEqual(reverse("trips:my_trips"), "/ar/trips/")
        self.assertEqual(reverse("trips:my_trips"), "/trips/")

    def test_switch_keeps_the_same_page(self):
        owner = make_user("ammar")
        trip = make_trip(owner, make_origin())
        self.client.force_login(owner)

        response = self.client.get(f"/ar/trips/{trip.pk}/")

        self.assertContains(response, f'href="/trips/{trip.pk}/"')
        self.assertContains(response, "كود الدعوة")
        self.assertContains(response, "الرياض")

    def test_login_redirect_stays_in_arabic(self):
        response = self.client.get("/ar/trips/")

        self.assertRedirects(response, "/ar/accounts/login/?next=/ar/trips/")

    def test_compiled_catalog_is_present(self):
        self.assertTrue((Path(settings.BASE_DIR) / "locale/ar/LC_MESSAGES/django.mo").exists())


class ArabicRecommendationTests(ResetLanguageMixin, RecommendationTestCase):
    def test_exclusion_reasons_use_arabic_plurals(self):
        generate_recommendations(self.trip)
        self.client.force_login(self.faisal)

        response = self.client.get(f"/ar/trips/{self.trip.pk}/recommendations/")

        self.assertContains(response, "تتجاوز ميزانية عضوين")  # dual form for 2 members
        self.assertContains(response, "يحتاجها عضو واحد")       # singular for 1 member
        self.assertContains(response, "لم تناسب الجميع (1)")

    def test_explanation_uses_arabic_month_and_thousands_separator(self):
        generate_recommendations(self.trip)
        self.client.force_login(self.ammar)

        response = self.client.get(f"/ar/trips/{self.trip.pk}/recommendations/{self.baku.pk}/")

        self.assertContains(response, "حوالي 3,300 ريال للشخص")
        self.assertContains(response, "رحلة مباشرة من الرياض")
        self.assertContains(response, "82<small>%</small>", html=False)
