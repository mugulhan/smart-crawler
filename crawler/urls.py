from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('crawl/create/', views.create_crawl, name='create_crawl'),
    path('crawl/<int:crawl_id>/', views.crawl_detail, name='crawl_detail'),
    path('crawl/<int:crawl_id>/delete/', views.delete_crawl, name='delete_crawl'),
    path('api/crawl-status/', views.api_crawl_status, name='api_crawl_status'),
    path('api/graph-data/<int:crawl_id>/', views.api_graph_data, name='api_graph_data'),
]
