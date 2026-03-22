from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.utils.text import slugify
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import Category, Tag, Website, WebsiteSuggestion


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display        = ['name', 'slug', 'colored_icon', 'order', 'website_count']
    list_editable       = ['order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields       = ['name']

    def colored_icon(self, obj):
        return format_html(
            '<i class="bi {}" style="color:{};font-size:1.2rem;"></i> {}',
            obj.icon, obj.color, obj.icon
        )
    colored_icon.short_description = 'Icon'

    def website_count(self, obj):
        return obj.websites.filter(is_active=True).count()
    website_count.short_description = 'Sites'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display        = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields       = ['name']


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display      = ['colored_letter', 'name', 'category', 'domain',
                         'is_featured', 'is_active', 'view_count', 'created_at']
    list_filter       = ['category', 'is_featured', 'is_active', 'tags']
    list_editable     = ['is_featured', 'is_active']
    search_fields     = ['name', 'description', 'url']
    filter_horizontal = ['tags']
    readonly_fields   = ['view_count', 'created_at', 'updated_at']
    fieldsets = (
        (None,         {'fields': ('name', 'url', 'category', 'tags')}),
        ('Content',    {'fields': ('description', 'short_description')}),
        ('Appearance', {'fields': ('color',)}),
        ('Settings',   {'fields': ('is_featured', 'is_active', 'order')}),
        ('Stats',      {'fields': ('view_count', 'created_at', 'updated_at'),
                        'classes': ('collapse',)}),
    )

    def colored_letter(self, obj):
        return format_html(
            '<div style="width:28px;height:28px;border-radius:6px;background:{}; '
            'display:inline-flex;align-items:center;justify-content:center;'
            'color:#fff;font-weight:800;font-size:13px;">{}</div>',
            obj.color, obj.letter
        )
    colored_letter.short_description = ''

    def domain(self, obj):
        return obj.get_domain()
    domain.short_description = 'Domain'


@admin.register(WebsiteSuggestion)
class WebsiteSuggestionAdmin(admin.ModelAdmin):
    list_display    = ['name', 'suggested_by', 'category', 'suggested_category',
                       'status_badge', 'created_at', 'reviewed_at']
    list_filter     = ['status', 'category']
    search_fields   = ['name', 'url', 'suggested_by__username', 'suggested_category']
    readonly_fields = ['suggested_by', 'name', 'url', 'description',
                       'category', 'suggested_category', 'created_at']
    actions         = ['approve_suggestions', 'reject_suggestions']
    fieldsets = (
        ('Submission', {
            'fields': ('suggested_by', 'name', 'url', 'category',
                       'suggested_category', 'description', 'created_at')
        }),
        ('Review', {
            'fields': ('status', 'admin_note', 'reviewed_at')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return list(self.readonly_fields) + ['status']
        return self.readonly_fields

    def status_badge(self, obj):
        colors = {
            'pending':  ('#92400e', 'rgba(250,204,21,.15)'),
            'approved': ('#065f46', 'rgba(16,185,129,.15)'),
            'rejected': ('#991b1b', 'rgba(239,68,68,.15)'),
        }
        icons  = {'pending': '⏳', 'approved': '✅', 'rejected': '❌'}
        color, bg = colors.get(obj.status, ('#333', '#eee'))
        return format_html(
            '<span style="padding:2px 10px;border-radius:99px;font-size:.75rem;'
            'font-weight:700;background:{};color:{};">{} {}</span>',
            bg, color, icons.get(obj.status, ''), obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def approve_suggestions(self, request, queryset):
        created = 0
        for s in queryset:
            # Skip if website with same URL already exists
            if Website.objects.filter(url=s.url).exists():
                continue

            category = s.category
            if not category and s.suggested_category:
                category, _created = Category.objects.get_or_create(
                    name=s.suggested_category,
                    defaults={
                        'slug':  slugify(s.suggested_category),
                        'order': 99,
                    }
                )

            Website.objects.create(
                name=s.name,
                url=s.url,
                description=s.description,
                short_description=s.description[:160],
                category=category,
                is_active=True,
            )
            s.status      = WebsiteSuggestion.STATUS_APPROVED
            s.reviewed_at = timezone.now()
            s.save()
            created += 1

        self.message_user(
            request,
            _(f'{created} suggestion(s) approved and published successfully.'),
            messages.SUCCESS,
        )
    approve_suggestions.short_description = '✅ Approve and publish selected suggestions'

    def reject_suggestions(self, request, queryset):
        updated = queryset.update(
            status=WebsiteSuggestion.STATUS_REJECTED,
            reviewed_at=timezone.now(),
        )
        self.message_user(
            request,
            _(f'{updated} suggestion(s) rejected.'),
            messages.WARNING,
        )
    reject_suggestions.short_description = '❌ Reject selected suggestions'