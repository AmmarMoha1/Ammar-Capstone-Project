import re
from datetime import timedelta

from django import forms
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from destinations.models import Interest, OriginCity

from .models import INVITE_CODE_ALPHABET, INVITE_CODE_LENGTH, INVITE_CODE_PREFIX, Availability, Preference, Trip

INVITE_CODE_PATTERN = re.compile(
    rf"^{INVITE_CODE_PREFIX}[{INVITE_CODE_ALPHABET}]{{{INVITE_CODE_LENGTH}}}$"
)


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ["name", "departure_city", "start_date", "end_date"]
        labels = {
            "name": _("Trip name"),
            "departure_city": _("Departing from"),
            "start_date": _("Start date"),
            "end_date": _("End date"),
        }
        help_texts = {
            "name": _("For example: Winter Getaway."),
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Winter Getaway")}),
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["departure_city"].queryset = OriginCity.objects.filter(is_active=True)
        self.fields["departure_city"].empty_label = _("Choose a city")
        self.fields["departure_city"].label_from_instance = (
            lambda city: f"{gettext(city.name)} ({city.airport_code})"
        )

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_start_date(self):
        start_date = self.cleaned_data["start_date"]
        # New trips and changed dates are checked; an unchanged date on an existing trip is left alone.
        is_new_or_changed = self.instance.pk is None or "start_date" in self.changed_data
        if is_new_or_changed and start_date < timezone.localdate():
            raise forms.ValidationError(_("The start date can't be in the past."))
        return start_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date <= start_date:
            self.add_error("end_date", _("The end date must be after the start date."))
        return cleaned_data


class JoinTripForm(forms.Form):
    code = forms.CharField(
        label=_("Invite code"),
        max_length=20,
        help_text=_("Ask your organizer for the code. It looks like WJ-8K32L."),
        widget=forms.TextInput(attrs={
            "placeholder": "WJ-8K32L",
            "autocomplete": "off",
            "autocapitalize": "characters",
            "spellcheck": "false",
        }),
    )

    def clean_code(self):
        # Accept "wj-8k32l", " WJ 8K32L ", "WJ8K32L" or just "8K32L"; normalise to "WJ-8K32L".
        code = re.sub(r"\s", "", self.cleaned_data["code"]).upper()
        if code.startswith(INVITE_CODE_PREFIX):
            code = code[len(INVITE_CODE_PREFIX):]
        elif len(code) == len("WJ") + INVITE_CODE_LENGTH and code.startswith("WJ"):
            # Typed without the dash. Only strip "WJ" when all 7 characters are present,
            # because the 5-character part may itself start with "WJ" (e.g. WJ-WJ3K2).
            code = code[2:]
        code = INVITE_CODE_PREFIX + code
        if not INVITE_CODE_PATTERN.match(code):
            raise forms.ValidationError(_("That doesn't look like a Wajha code. Codes look like WJ-8K32L."))
        return code


class InterestChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return gettext(obj.name)


class PreferenceForm(forms.ModelForm):
    interests = InterestChoiceField(
        queryset=Interest.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_("What do you want to do there?"),
        help_text=_("Choose at least one."),
        error_messages={"required": _("Choose at least one interest.")},
    )

    class Meta:
        model = Preference
        fields = ["max_budget", "max_flight_hours", "weather_preference", "direct_only", "interests"]
        labels = {
            "max_budget": _("Maximum budget per person (SAR)"),
            "max_flight_hours": _("Longest flight you'll accept (hours)"),
            "weather_preference": _("Preferred weather"),
            "direct_only": _("Direct flights only"),
        }
        help_texts = {
            "max_budget": _("Your total for the whole trip: return flight plus accommodation, food and local transport."),
            "max_flight_hours": _("One way. Use whole or half hours, e.g. 4 or 5.5."),
            "direct_only": _("Only show destinations with a direct flight from your departure city."),
        }
        widgets = {
            "max_budget": forms.NumberInput(attrs={
                "min": Preference.MIN_BUDGET, "max": Preference.MAX_BUDGET, "step": 50,
                "placeholder": "4000", "inputmode": "numeric",
            }),
            "max_flight_hours": forms.NumberInput(attrs={
                "min": Preference.MIN_FLIGHT_HOURS, "max": Preference.MAX_FLIGHT_HOURS, "step": "0.5",
                "placeholder": "5", "inputmode": "decimal",
            }),
            "weather_preference": forms.RadioSelect,
        }
        error_messages = {
            "max_budget": {
                "min_value": _("Budget must be at least 500 SAR."),
                "max_value": _("Budget can't be more than 100,000 SAR."),
            },
            "max_flight_hours": {
                "min_value": _("Flight time must be at least 1 hour."),
                "max_value": _("Flight time can't be more than 24 hours."),
            },
        }

    def clean_max_flight_hours(self):
        hours = self.cleaned_data["max_flight_hours"]
        if (hours * 2) % 1 != 0:
            raise forms.ValidationError(_("Use whole or half hours, e.g. 4 or 5.5."))
        return hours


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ["start_date", "end_date"]
        labels = {
            "start_date": _("Free from"),
            "end_date": _("Free until"),
        }
        help_texts = {
            "end_date": _("The last day you could be back home."),
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean_start_date(self):
        start_date = self.cleaned_data["start_date"]
        if start_date < timezone.localdate():
            raise forms.ValidationError(_("The start date can't be in the past."))
        return start_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date:
            if end_date <= start_date:
                self.add_error("end_date", _("The end date must be after the start date."))
            elif (end_date - start_date).days > Availability.MAX_DAYS:
                self.add_error("end_date", _("A range can be at most 90 days. Add another range for more."))
            elif end_date > timezone.localdate() + timedelta(days=Availability.MAX_DAYS_AHEAD):
                self.add_error("end_date", _("Ranges can end at most a year from today."))
        return cleaned_data
