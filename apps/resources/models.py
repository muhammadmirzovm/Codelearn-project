from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from urllib.parse import urlparse


class Category(models.Model):
    name        = models.CharField(_('name'), max_length=100)
    slug        = models.SlugField(unique=True)
    icon        = models.CharField(
        _('icon'), max_length=60, default='bi-globe',
        help_text=_('Bootstrap icon class, e.g. bi-code-slash')
    )
    color       = models.CharField(
        _('color'), max_length=7, default='#0d9488',
        help_text=_('Hex color for the category accent')
    )
    order       = models.PositiveIntegerField(_('order'), default=0)
    description = models.CharField(_('description'), max_length=255, blank=True)

    class Meta:
        verbose_name        = _('Category')
        verbose_name_plural = _('Categories')
        ordering            = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def website_count(self):
        return self.websites.filter(is_active=True).count()


class Tag(models.Model):
    name = models.CharField(_('name'), max_length=50)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name        = _('Tag')
        verbose_name_plural = _('Tags')
        ordering            = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Website(models.Model):
    name              = models.CharField(_('name'), max_length=200)
    url               = models.URLField(_('URL'), unique=True)
    description       = models.TextField(_('description'))
    short_description = models.CharField(
        _('short description'), max_length=160, blank=True,
        help_text=_('Shown on the card. Falls back to description if empty.')
    )
    category    = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='websites', verbose_name=_('category'),
    )
    tags        = models.ManyToManyField(
        Tag, blank=True, related_name='websites', verbose_name=_('tags')
    )
    color       = models.CharField(
        _('accent color'), max_length=7, default='#0d9488',
        help_text=_('Hex color for the card logo background')
    )
    is_featured = models.BooleanField(_('featured'), default=False)
    is_active   = models.BooleanField(_('active'), default=True)
    view_count  = models.PositiveIntegerField(_('view count'), default=0)
    order       = models.PositiveIntegerField(_('order'), default=0)
    created_at  = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at  = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name        = _('Website')
        verbose_name_plural = _('Websites')
        ordering            = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def display_description(self):
        return self.short_description or self.description[:120]

    @property
    def letter(self):
        return self.name[0].upper() if self.name else '?'

    def get_domain(self):
        parsed = urlparse(self.url)
        return parsed.netloc.replace('www.', '')


class WebsiteSuggestion(models.Model):
    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  _('Pending')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_REJECTED, _('Rejected')),
    ]

    suggested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='website_suggestions',
        verbose_name=_('suggested by'),
    )
    name               = models.CharField(_('name'), max_length=200)
    url                = models.URLField(_('URL'), unique=True)
    description        = models.TextField(_('description'))
    category           = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('category'),
    )
    suggested_category = models.CharField(
        _('suggested category'), max_length=100, blank=True,
        help_text=_('If your category is not in the list above, type it here')
    )
    status      = models.CharField(
        _('status'), max_length=20,
        choices=STATUS_CHOICES, default=STATUS_PENDING,
    )
    admin_note  = models.TextField(
        _('admin note'), blank=True,
        help_text=_('Optional note shown to the user')
    )
    created_at  = models.DateTimeField(_('created at'), auto_now_add=True)
    reviewed_at = models.DateTimeField(_('reviewed at'), null=True, blank=True)

    class Meta:
        verbose_name        = _('Website Suggestion')
        verbose_name_plural = _('Website Suggestions')
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.suggested_by.username} ({self.status})'
    
    
import re

class VideoCategory(models.Model):
    name  = models.CharField(_('name'), max_length=100)
    slug  = models.SlugField(unique=True)

    class Meta:
        verbose_name        = _('Video Category')
        verbose_name_plural = _('Video Categories')
        ordering            = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Video(models.Model):
    LANGUAGE_CHOICES = [
        ('uz', "O'zbek"),
        ('ru', 'Русский'),
        ('en', 'English'),
    ]

    title       = models.CharField(_('title'), max_length=200)
    url         = models.TextField(_('YouTube URL or iframe'))
    embed_url   = models.CharField(_('embed URL'), max_length=500, blank=True)
    description = models.TextField(_('description'), blank=True)
    language    = models.CharField(
        _('language'), max_length=5,
        choices=LANGUAGE_CHOICES
    )
    category    = models.ForeignKey(
        VideoCategory, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='videos', verbose_name=_('category'),
    )
    new_category = models.CharField(
        _('new category'), max_length=100, blank=True,
        help_text=_('If your category is not listed, type a new one here')
    )
    added_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name=_('added by'),
    )
    created_at  = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name        = _('Video')
        verbose_name_plural = _('Videos')
        ordering            = ['-created_at']

    def __str__(self):
        return self.title

    @staticmethod
    def extract_youtube_id(raw):
        """Extract YouTube video ID from any URL or iframe."""
        # If it's an iframe tag
        iframe_src = re.search(r'src=["\']([^"\']+)["\']', raw)
        if iframe_src:
            raw = iframe_src.group(1)

        # Match various YouTube URL formats
        patterns = [
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, raw)
            if match:
                return match.group(1)
        return None

    def save(self, *args, **kwargs):
        # Auto-create category from new_category field
        if self.new_category and not self.category:
            cat, _ = VideoCategory.objects.get_or_create(
                slug=slugify(self.new_category),
                defaults={'name': self.new_category}
            )
            self.category = cat
            self.new_category = ''

        # Extract embed URL
        video_id = self.extract_youtube_id(self.url)
        if video_id:
            self.embed_url = f'https://www.youtube.com/embed/{video_id}'

        super().save(*args, **kwargs)