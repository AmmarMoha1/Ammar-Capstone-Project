from django import forms
from django.utils import timezone

from destinations.models import OriginCity

from .models import Trip


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
