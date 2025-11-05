from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from urllib.parse import urlparse
from .models import CrawlJob, PageInfo, Link
from .tasks import crawl_url


def dashboard(request):
    """Main dashboard view"""
    crawl_jobs = CrawlJob.objects.all()[:20]

    stats = {
        'total_crawls': CrawlJob.objects.count(),
        'completed_crawls': CrawlJob.objects.filter(status='completed').count(),
        'running_crawls': CrawlJob.objects.filter(status='running').count(),
        'failed_crawls': CrawlJob.objects.filter(status='failed').count(),
    }

    context = {
        'crawl_jobs': crawl_jobs,
        'stats': stats,
    }
    return render(request, 'crawler/dashboard.html', context)


def create_crawl(request):
    """Create a new crawl job"""
    if request.method == 'POST':
        url = request.POST.get('url')
        if url:
            crawl_job = CrawlJob.objects.create(url=url)
            # Trigger Celery task
            crawl_url.delay(crawl_job.id)
            messages.success(request, f'Crawl job created for {url}')
            return redirect('dashboard')
        else:
            messages.error(request, 'URL is required')

    return redirect('dashboard')


def crawl_detail(request, crawl_id):
    """View details of a specific crawl job"""
    crawl_job = get_object_or_404(CrawlJob, id=crawl_id)

    try:
        page_info = crawl_job.page_info
    except PageInfo.DoesNotExist:
        page_info = None

    links = crawl_job.links.all()

    context = {
        'crawl_job': crawl_job,
        'page_info': page_info,
        'links': links,
    }
    return render(request, 'crawler/crawl_detail.html', context)


def delete_crawl(request, crawl_id):
    """Delete a crawl job"""
    crawl_job = get_object_or_404(CrawlJob, id=crawl_id)
    crawl_job.delete()
    messages.success(request, 'Crawl job deleted successfully')
    return redirect('dashboard')


def api_crawl_status(request):
    """API endpoint to get crawl jobs status and stats"""
    crawl_jobs = CrawlJob.objects.all()[:20]

    jobs_data = []
    for job in crawl_jobs:
        jobs_data.append({
            'id': job.id,
            'url': job.url,
            'status': job.status,
            'status_display': job.get_status_display(),
            'total_links': job.total_links,
            'internal_links': job.internal_links,
            'external_links': job.external_links,
            'created_at': job.created_at.strftime('%b %d, %Y %H:%M'),
        })

    stats = {
        'total_crawls': CrawlJob.objects.count(),
        'completed_crawls': CrawlJob.objects.filter(status='completed').count(),
        'running_crawls': CrawlJob.objects.filter(status='running').count(),
        'failed_crawls': CrawlJob.objects.filter(status='failed').count(),
    }

    return JsonResponse({
        'jobs': jobs_data,
        'stats': stats
    })


def api_graph_data(request, crawl_id):
    """API endpoint to get graph data for visualization"""
    crawl_job = get_object_or_404(CrawlJob, id=crawl_id)
    links = crawl_job.links.all()

    # Parse main URL
    main_parsed = urlparse(crawl_job.url)
    main_domain = main_parsed.netloc

    # Create nodes and edges
    nodes = [
        {
            'id': 'root',
            'label': main_domain,
            'url': crawl_job.url,
            'type': 'root',
            'domain': main_domain,
            'layer': 0
        }
    ]

    edges = []
    node_map = {}
    node_id_counter = 0

    # Separate internal and external links
    internal_links = [l for l in links if l.link_type == 'internal'][:50]
    external_links = [l for l in links if l.link_type == 'external'][:30]

    # Group links by parent element for better visualization
    links_by_element = {}
    for link in internal_links:
        parent = link.parent_element or 'body'
        if parent not in links_by_element:
            links_by_element[parent] = []
        links_by_element[parent].append(link)

    # Create parent element nodes first
    element_nodes = {}
    element_layer_map = {
        'header': 1,
        'nav': 1,
        'main': 1,
        'footer': 1,
        'aside': 1,
        'section': 2,
        'article': 2,
        'body': 1
    }

    for parent_element, element_links in links_by_element.items():
        # Create parent element node if it has multiple links
        if len(element_links) > 1:
            element_node_id = f"element_{node_id_counter}"
            node_id_counter += 1

            # Extract base tag name
            import re
            base_tag = re.split(r'[#.]', parent_element)[0] if isinstance(parent_element, str) else parent_element
            layer = element_layer_map.get(base_tag, 1)

            element_nodes[parent_element] = {
                'id': element_node_id,
                'layer': layer
            }

            nodes.append({
                'id': element_node_id,
                'label': parent_element.upper(),
                'url': crawl_job.url,
                'type': 'element_group',
                'domain': main_domain,
                'layer': layer,
                'parent_element': parent_element
            })

            # Add edge from root to element group
            edges.append({
                'from': 'root',
                'to': element_node_id
            })

    # Process internal links
    for parent_element, element_links in links_by_element.items():
        for link in element_links:
            parsed = urlparse(link.url)
            path = parsed.path or '/'

            # Create unique node ID based on full path
            node_id = f"internal_{node_id_counter}"
            node_id_counter += 1

            # Get path segments for additional layer depth
            path_segments = [p for p in path.split('/') if p]
            base_tag = parent_element.split('#')[0].split('.')[0] if parent_element else 'body'
            base_layer = element_layer_map.get(base_tag, 1)

            # Calculate layer: base layer + path depth
            path_depth = min(len(path_segments), 2)
            layer = base_layer + path_depth + 1

            # Create label from path
            if path == '/':
                label = 'Home'
            else:
                # Use last segment or shorten path
                segments = path.strip('/').split('/')
                label = segments[-1] if segments else 'Page'
                if len(label) > 20:
                    label = label[:18] + '..'

            nodes.append({
                'id': node_id,
                'label': label,
                'url': link.url,
                'type': 'internal',
                'domain': parsed.netloc,
                'path': path,
                'status_code': link.status_code,
                'is_broken': link.is_broken,
                'layer': layer,
                'anchor_text': link.anchor_text[:30] if link.anchor_text else '',
                'parent_element': parent_element
            })

            # Add edge - connect to parent element node if exists, otherwise to root
            if parent_element in element_nodes and len(element_links) > 1:
                edges.append({
                    'from': element_nodes[parent_element]['id'],
                    'to': node_id,
                    'path': path
                })
            else:
                edges.append({
                    'from': 'root',
                    'to': node_id,
                    'path': path
                })

    # Process external links (group by domain)
    external_domains = {}
    for link in external_links:
        parsed = urlparse(link.url)
        domain = parsed.netloc

        if domain not in external_domains:
            node_id = f"external_{node_id_counter}"
            node_id_counter += 1

            external_domains[domain] = {
                'node_id': node_id,
                'count': 0,
                'urls': []
            }

            nodes.append({
                'id': node_id,
                'label': domain,
                'url': link.url,
                'type': 'external',
                'domain': domain,
                'path': parsed.path or '/',
                'status_code': link.status_code,
                'is_broken': link.is_broken,
                'layer': 1,
                'parent_element': link.parent_element or 'body'
            })

        external_domains[domain]['count'] += 1
        external_domains[domain]['urls'].append(link.url)

        # Add edge
        edges.append({
            'from': 'root',
            'to': external_domains[domain]['node_id'],
            'count': external_domains[domain]['count']
        })

    return JsonResponse({
        'nodes': nodes,
        'edges': edges,
        'stats': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'internal': len([n for n in nodes if n.get('type') == 'internal']),
            'external': len([n for n in nodes if n.get('type') == 'external']),
            'layers': max([n.get('layer', 0) for n in nodes])
        }
    })
