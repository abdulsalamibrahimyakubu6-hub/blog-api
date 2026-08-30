import django_filters
from .models import Post


class PostFilter(django_filters.FilterSet):
    """FilterSet for Posts supporting author filtering and date range filtering."""

    author = django_filters.CharFilter(
        field_name="author__username", lookup_expr="iexact"
    )
    author_id = django_filters.NumberFilter(
        field_name="author__id", lookup_expr="exact"
    )
    created_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )

    class Meta:
        model = Post
        fields = ["author", "author_id", "created_after", "created_before"]
