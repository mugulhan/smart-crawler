from celery import shared_task
from .models import CrawlJob, PageInfo, Link
from .crawler_engine import SmartCrawler


@shared_task
def crawl_url(crawl_job_id):
    """Celery task to crawl a URL"""
    try:
        crawl_job = CrawlJob.objects.get(id=crawl_job_id)
        crawl_job.mark_as_running()

        # Run the crawler
        crawler = SmartCrawler(crawl_job.url)
        result = crawler.crawl()

        if result['success']:
            # Save page info
            PageInfo.objects.create(
                crawl_job=crawl_job,
                **result['page_info']
            )

            # Save links
            for link_data in result['links']:
                Link.objects.create(
                    crawl_job=crawl_job,
                    **link_data
                )

            # Update crawl job summary
            crawl_job.total_links = result['total_links']
            crawl_job.internal_links = result['internal_links']
            crawl_job.external_links = result['external_links']
            crawl_job.mark_as_completed()

        else:
            crawl_job.mark_as_failed(result['error'])

    except Exception as e:
        crawl_job.mark_as_failed(str(e))
