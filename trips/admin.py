from django.contrib import admin

from .models import Trip, TripMember


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
