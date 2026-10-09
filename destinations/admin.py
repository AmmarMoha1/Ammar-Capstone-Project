from django.contrib import admin

from .models import Destination, DestinationClimate, Interest, OriginCity, RouteProfile


@admin.register(OriginCity)
class OriginCityAdmin(admin.ModelAdmin):
    list_display = ["name", "airport_code", "is_active"]
    list_filter = ["is_active"]


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ["name"]


class DestinationClimateInline(admin.TabularInline):
    model = DestinationClimate
    extra = 0
    max_num = 4


class RouteProfileInline(admin.TabularInline):
    model = RouteProfile
    extra = 0


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ["city", "country", "country_code", "estimated_daily_cost", "is_active"]
    list_filter = ["is_active", "interests"]
    search_fields = ["city", "country"]
    filter_horizontal = ["interests"]
    inlines = [DestinationClimateInline, RouteProfileInline]


@admin.register(RouteProfile)
class RouteProfileAdmin(admin.ModelAdmin):
    list_display = [
        "origin_city",
        "destination",
        "flight_duration_hours",
        "direct_available",
        "estimated_flight_cost",
    ]
    list_filter = ["origin_city", "direct_available"]
