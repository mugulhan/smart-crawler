from django.db import models
from django.utils import timezone


class CrawlJob(models.Model):
    """Represents a crawl job for a specific URL"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    url = models.URLField(max_length=2000, help_text="URL to crawl")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    # Crawl results summary
    total_links = models.IntegerField(default=0)
    internal_links = models.IntegerField(default=0)
    external_links = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.url} - {self.status}"

    def mark_as_running(self):
        self.status = 'running'
        self.started_at = timezone.now()
        self.save()

    def mark_as_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def mark_as_failed(self, error):
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = str(error)
        self.save()


class PageInfo(models.Model):
    """Stores information about the crawled page"""
    crawl_job = models.OneToOneField(CrawlJob, on_delete=models.CASCADE, related_name='page_info')
    title = models.CharField(max_length=500, blank=True)
    meta_description = models.TextField(blank=True)
    status_code = models.IntegerField()
    content_type = models.CharField(max_length=100, blank=True)
    response_time = models.FloatField(help_text="Response time in seconds")
    page_size = models.IntegerField(help_text="Page size in bytes")
    html_structure = models.JSONField(null=True, blank=True, help_text="HTML semantic structure as JSON")
    schema_markup = models.JSONField(null=True, blank=True, help_text="JSON-LD schema markup data")
    lighthouse_score = models.JSONField(null=True, blank=True, help_text="Google Lighthouse performance audit results")

    def __str__(self):
        return f"Page Info for {self.crawl_job.url}"


class Link(models.Model):
    """Represents a link found on the crawled page"""
    LINK_TYPE_CHOICES = [
        ('internal', 'Internal'),
        ('external', 'External'),
    ]

    crawl_job = models.ForeignKey(CrawlJob, on_delete=models.CASCADE, related_name='links')
    url = models.URLField(max_length=2000)
    link_type = models.CharField(max_length=20, choices=LINK_TYPE_CHOICES)
    anchor_text = models.CharField(max_length=500, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    is_broken = models.BooleanField(default=False)
    parent_element = models.CharField(max_length=100, blank=True, null=True, help_text="Parent HTML element (header, footer, nav, etc.)")

    class Meta:
        ordering = ['link_type', 'url']

    def __str__(self):
        return f"{self.url} ({self.link_type})"
