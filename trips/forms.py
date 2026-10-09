import re

from django import forms
from django.utils import timezone

from destinations.models import OriginCity

from .models import INVITE_CODE_ALPHABET, INVITE_CODE_LENGTH, INVITE_CODE_PREFIX, Trip

INVITE_CODE_PATTERN = re.compile(
    rf"^{INVITE_CODE_PREFIX}[{INVITE_CODE_ALPHABET}]{{{INVITE_CODE_LENGTH}}}$"
)


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ["name", "departure_city", "start_date", "end_date"]
        labels = {
            "name": "Trip name",
            "departure_city": "Departing from",
        }
        help_texts = {
            "name": "For example: Winter Getaway.",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Winter Getaway"}),
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["departure_city"].queryset = OriginCity.objects.filter(is_active=True)
        self.fields["departure_city"].empty_label = "Choose a city"

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_start_date(self):
        start_date = self.cleaned_data["start_date"]
        # Only new trips are checked: an existing trip may legitimately have started.
        if self.instance.pk is None and start_date < timezone.localdate():
            raise forms.ValidationError("The start date can't be in the past.")
        return start_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date <= start_date:
            self.add_error("end_date", "The end date must be after the start date.")
        return cleaned_data


class JoinTripForm(forms.Form):
    code = forms.CharField(
        label="Invite code",
        max_length=20,
        help_text="Ask your organizer for the code. It looks like WJ-8K32L.",
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
            raise forms.ValidationError("That doesn't look like a Wajha code. Codes look like WJ-8K32L.")
        return code
