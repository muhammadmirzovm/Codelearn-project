from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F

from .models import Category, Website, WebsiteSuggestion ,Video, VideoCategory
from .forms import WebsiteSuggestionForm, VideoForm






def _base_context(request, category_slug='', search_query=''):
    websites = (
        Website.objects
        .filter(is_active=True)
        .select_related('category')
        .prefetch_related('tags')
    )
    if category_slug:
        websites = websites.filter(category__slug=category_slug)
    if search_query:
        websites = websites.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()

    return {
        'websites':       websites,
        'categories':     Category.objects.filter(websites__is_active=True).distinct().order_by('order', 'name'),
        'all_categories': Category.objects.order_by('name'),   # ← for datalist
        'active_slug':    category_slug,
        'search_query':   search_query,
        'total_count':    websites.count(),
        'my_suggestions': WebsiteSuggestion.objects.filter(suggested_by=request.user).order_by('-created_at')[:5],
        'suggest_form':   WebsiteSuggestionForm(),
    }


@login_required
def website_list(request):
    category_slug = request.GET.get('category', '').strip()
    search_query  = request.GET.get('q', '').strip()
    context = _base_context(request, category_slug, search_query)
    context['active_category'] = Category.objects.filter(slug=category_slug).first() if category_slug else None
    return render(request, 'resources/website_list.html', context)


@login_required
def website_visit(request, pk):
    website = get_object_or_404(Website, pk=pk, is_active=True)
    Website.objects.filter(pk=pk).update(view_count=F('view_count') + 1)
    return redirect(website.url)


@login_required
def website_suggest(request):
    if request.method != 'POST':
        return redirect('resources:website_list')

    form = WebsiteSuggestionForm(request.POST)
    if form.is_valid():
        suggestion = form.save(commit=False)
        suggestion.suggested_by = request.user
        suggestion.save()
        messages.success(request, _('Your suggestion has been submitted for review. Thank you! 🙌'))
        return redirect('resources:website_list')

    category_slug = request.GET.get('category', '').strip()
    context = _base_context(request, category_slug)
    context['suggest_form'] = form
    context['open_suggest'] = True
    return render(request, 'resources/website_list.html', context)




@login_required
def resource_home(request):
    return render(request, 'resources/home.html', {
        'website_count': Website.objects.filter(is_active=True).count(),
        'video_count':   Video.objects.count(),
    })


@login_required
def video_list(request):
    language = request.GET.get('lang', '').strip()
    category_slug = request.GET.get('category', '').strip()
    search_query = request.GET.get('q', '').strip()

    videos = Video.objects.select_related('category', 'added_by')

    if language:
        videos = videos.filter(language=language)
    if category_slug:
        videos = videos.filter(category__slug=category_slug)
    if search_query:
        videos = videos.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    return render(request, 'resources/video_list.html', {
        'videos':          videos,
        'video_categories': VideoCategory.objects.all(),
        'active_lang':     language,
        'active_slug':     category_slug,
        'search_query':    search_query,
        'video_form':      VideoForm(),
        'language_choices': Video.LANGUAGE_CHOICES,
    })


@login_required
def video_add(request):
    if request.method != 'POST':
        return redirect('resources:video_list')

    form = VideoForm(request.POST)
    if form.is_valid():
        video = form.save(commit=False)
        video.added_by = request.user
        video.save()
        messages.success(request, _('Video added successfully! 🎉'))
        return redirect('resources:video_list')

    language = request.GET.get('lang', '').strip()
    videos = Video.objects.select_related('category', 'added_by')
    if language:
        videos = videos.filter(language=language)

    return render(request, 'resources/video_list.html', {
        'videos':           videos,
        'video_categories': VideoCategory.objects.all(),
        'active_lang':      language,
        'video_form':       form,
        'language_choices': Video.LANGUAGE_CHOICES,
        'open_video_form':  True,
    })


@login_required
def video_delete(request, pk):
    video = get_object_or_404(Video, pk=pk)
    if request.user == video.added_by or request.user.is_staff:
        video.delete()
        messages.success(request, _('Video deleted.'))
    return redirect('resources:video_list')