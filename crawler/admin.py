from django.contrib import admin
from .models import CrawlJob, PageInfo, Link


@admin.register(CrawlJob)
class CrawlJobAdmin(admin.ModelAdmin):
    list_display = ['url', 'status', 'total_links', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['url']
    readonly_fields = ['created_at', 'started_at', 'completed_at']


@admin.register(PageInfo)
class PageInfoAdmin(admin.ModelAdmin):
    list_display = ['crawl_job', 'status_code', 'title', 'response_time']
    search_fields = ['title', 'crawl_job__url']


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ['url', 'link_type', 'status_code', 'is_broken', 'crawl_job']
    list_filter = ['link_type', 'is_broken']
    search_fields = ['url', 'anchor_text']
