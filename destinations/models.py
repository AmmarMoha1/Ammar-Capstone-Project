from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q


class WeatherType(models.TextChoices):
    COLD = "COLD", "Cold"
    MILD = "MILD", "Mild"
    WARM = "WARM", "Warm"
    HOT = "HOT", "Hot"


class ClimatePeriod(models.IntegerChoices):
    # Stored as 1-4 so periods sort in calendar order.
    JAN_MAR = 1, "Jan – Mar"
    APR_JUN = 2, "Apr – Jun"
    JUL_SEP = 3, "Jul – Sep"
    OCT_DEC = 4, "Oct – Dec"

    @classmethod
    def for_date(cls, day):
        """The period a date falls in: months 1-3 -> 1, 4-6 -> 2, 7-9 -> 3, 10-12 -> 4."""
        return cls((day.month - 1) // 3 + 1)


class OriginCity(models.Model):
    """A Saudi city that trips can depart from."""

    name = models.CharField(max_length=100, unique=True)
    airport_code = models.CharField(
        max_length=3,
        unique=True,
        validators=[RegexValidator(r"^[A-Z]{3}$", "Use a 3-letter uppercase IATA code.")],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "origin cities"

    def __str__(self):
        return f"{self.name} ({self.airport_code})"


class Interest(models.Model):
    """A travel interest such as Nature or Food."""

    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Destination(models.Model):
    """A destination city in the catalog.

    estimated_daily_cost is an illustrative per-person estimate (SAR) for
    normal on-ground costs: accommodation, food and local transport.
    It is not a live price.
    """

    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    country_code = models.CharField(
        max_length=2,
        validators=[RegexValidator(r"^[A-Z]{2}$", "Use a 2-letter uppercase ISO country code.")],
    )
    estimated_daily_cost = models.PositiveIntegerField(
        help_text="Illustrative SAR per person per day (accommodation, food, local transport)."
    )
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    interests = models.ManyToManyField(Interest, related_name="destinations", blank=True)

    class Meta:
        ordering = ["city"]
        constraints = [
            models.UniqueConstraint(
                fields=["city", "country"], name="unique_destination_city_country"
            ),
            models.CheckConstraint(
                condition=Q(estimated_daily_cost__gt=0),
                name="destination_daily_cost_positive",
            ),
        ]

    def __str__(self):
        return f"{self.city}, {self.country}"


class DestinationClimate(models.Model):
    """Typical weather at a destination during one three-month period."""

    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="climates"
    )
    period = models.PositiveSmallIntegerField(choices=ClimatePeriod.choices)
    weather_type = models.CharField(max_length=4, choices=WeatherType.choices)

    class Meta:
        ordering = ["destination", "period"]
        constraints = [
            models.UniqueConstraint(
                fields=["destination", "period"], name="unique_climate_destination_period"
            ),
        ]

    def __str__(self):
        return f"{self.destination.city} {self.get_period_display()}: {self.get_weather_type_display()}"


class RouteProfile(models.Model):
    """Flight information that depends on both the origin and the destination.

    estimated_flight_cost is an illustrative return economy fare per person (SAR).
    """

    origin_city = models.ForeignKey(
        OriginCity, on_delete=models.CASCADE, related_name="routes"
    )
    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="routes"
    )
    flight_duration_hours = models.DecimalField(max_digits=4, decimal_places=1)
    direct_available = models.BooleanField(default=False)
    estimated_flight_cost = models.PositiveIntegerField(
        help_text="Illustrative return fare in SAR per person."
    )

    class Meta:
        ordering = ["origin_city", "destination"]
        constraints = [
            models.UniqueConstraint(
                fields=["origin_city", "destination"], name="unique_route_origin_destination"
            ),
            models.CheckConstraint(
                condition=Q(flight_duration_hours__gt=0),
                name="route_flight_duration_positive",
            ),
            models.CheckConstraint(
                condition=Q(estimated_flight_cost__gt=0),
                name="route_flight_cost_positive",
            ),
        ]

    def __str__(self):
        return f"{self.origin_city.airport_code} → {self.destination.city}"
