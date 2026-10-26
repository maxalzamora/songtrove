from django.contrib import admin

from .models import Song, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "owner")
    list_filter = ("owner",)
    search_fields = ("name",)


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "display_key", "capo", "rating", "status", "owner")
    list_filter = ("status", "sheet_format", "owner")
    search_fields = ("title", "artist", "notes", "sheet_body")
    filter_horizontal = ("tags",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("owner", "title", "artist")}),
        ("Musical details", {"fields": ("song_key", "mode", "capo", "tempo", "time_signature", "tuning")}),
        ("Practice", {"fields": ("rating", "status", "last_practiced_at", "tags")}),
        ("Sheet", {"fields": ("sheet_format", "sheet_body", "notes", "source_url")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("owner")
