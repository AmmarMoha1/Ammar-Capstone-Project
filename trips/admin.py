from django.contrib import admin

from .models import Availability, Trip, TripMember, Vote


class TripMemberInline(admin.TabularInline):
    model = TripMember
    extra = 0
    readonly_fields = ["joined_at"]


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "departure_city", "start_date", "end_date", "status", "invite_code"]
    list_filter = ["status", "departure_city"]
    search_fields = ["name", "invite_code", "owner__username"]
    readonly_fields = ["invite_code", "created_at", "updated_at"]
    inlines = [TripMemberInline]


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ["trip_member", "recommendation", "updated_at"]
    list_select_related = ["trip_member__user", "trip_member__trip", "recommendation__destination"]


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ["trip_member", "start_date", "end_date"]
    list_select_related = ["trip_member__user", "trip_member__trip"]
