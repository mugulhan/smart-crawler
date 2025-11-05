# Smart Crawler

Django-based intelligent web crawler application. Crawls web pages, collects links, checks status codes, and analyzes page meta information.

## Features

- Automatic web page crawling
- Link collection (internal and external links)
- HTTP status code checking
- Page title and meta description extraction
- Broken link detection
- Dashboard visualization
- Asynchronous crawling with Celery
- Docker support
- PostgreSQL database

## Installation

### Requirements

- Docker
- Docker Compose

### Steps

1. Clone the project:
```bash
git clone <repo-url>
cd smart-crawler
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Start Docker containers:
```bash
docker-compose up -d --build
```

4. Run database migrations:
```bash
docker-compose exec web python manage.py migrate
```

5. Create superuser (optional):
```bash
docker-compose exec web python manage.py createsuperuser
```

6. Collect static files:
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

## Usage

The application runs at http://localhost:8001 by default.

### Dashboard

On the main page:
- Start new crawls
- View existing crawls
- Track statistics

### Starting a Crawl

1. Enter the URL to crawl in the Dashboard URL field
2. Click the "Start Crawl" button
3. The crawl runs in the background with Celery
4. View results on the detail page

### Admin Panel

Access the Django admin panel at http://localhost:8001/admin.

## Services

The application includes the following services:

- **web**: Django web application (Port: 8001)
- **db**: PostgreSQL database (Port: 5432)
- **redis**: Redis cache/broker (Port: 6379)
- **celery**: Celery worker (background tasks)
- **celery-beat**: Celery beat (scheduled tasks)

## Docker Commands

```bash
# Start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Restart a specific service
docker-compose restart web

# Open shell
docker-compose exec web python manage.py shell

# Create migrations
docker-compose exec web python manage.py makemigrations

# Run migrations
docker-compose exec web python manage.py migrate
```

## Database

PostgreSQL is used. Default credentials:

- **Database**: smart_crawler
- **User**: crawler
- **Password**: crawler123
- **Host**: db
- **Port**: 5432

## Development

### Adding New Models

1. Edit `crawler/models.py`
2. Create migrations:
```bash
docker-compose exec web python manage.py makemigrations
```
3. Apply migrations:
```bash
docker-compose exec web python manage.py migrate
```

### Adding Celery Tasks

You can add new tasks to `crawler/tasks.py`:

```python
from celery import shared_task

@shared_task
def my_task():
    # Task logic
    pass
```

## Technical Details

### Crawler Features

- **requests**: For HTTP requests
- **BeautifulSoup**: For HTML parsing
- **lxml**: For fast XML/HTML processing
- Status code checking for first 50 links (for performance)
- User-Agent configured
- Timeout: 10 seconds
- 0.1 second delay between links

### Models

- **CrawlJob**: Stores crawl jobs
- **PageInfo**: Stores page meta information
- **Link**: Stores found links

## Port Information

- 8001: Django web application
- 5432: PostgreSQL
- 6379: Redis

To change ports, edit the `docker-compose.yml` file.

## Troubleshooting

### Container won't start

```bash
docker-compose logs web
```

### Database connection error

Ensure containers start in order:
```bash
docker-compose down
docker-compose up -d db
# Wait a few seconds
docker-compose up -d
```

### Static files not loading

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

## License

MIT

## Contributing

Pull requests are welcome.
