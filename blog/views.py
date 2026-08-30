from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import PostFilter
from .models import Comment, Like, Post
from .pagination import StandardResultsSetPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    CommentSerializer,
    LikeSerializer,
    PostDetailSerializer,
    PostSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Create a new user account.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/auth/me/
    Retrieve or update the authenticated user's profile.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):

            class EditableUserSerializer(UserSerializer):
                class Meta(UserSerializer.Meta):
                    read_only_fields = ["id", "username", "date_joined"]

            return EditableUserSerializer

        return UserSerializer


class PostViewSet(viewsets.ModelViewSet):
    """
    Blog posts.

    GET:
        Public

    POST:
        Authenticated users only

    PUT/PATCH/DELETE:
        Authenticated author only
    """

    queryset = (
        Post.objects.select_related("author")
        .prefetch_related("likes", "comments__replies")
        .all()
    )

    pagination_class = StandardResultsSetPagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = PostFilter

    search_fields = [
        "title",
        "content",
        "author__username",
    ]

    ordering_fields = [
        "created_at",
        "updated_at",
        "title",
    ]

    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PostDetailSerializer

        return PostSerializer

    def get_permissions(self):
        """
        Different permissions for different actions.
        """

        if self.action in [
            "list",
            "retrieve",
        ]:
            return [permissions.AllowAny()]

        if self.action in [
            "like",
            "unlike",
        ]:
            return [permissions.IsAuthenticated()]

        if self.action == "comments":
            if self.request.method == "GET":
                return [permissions.AllowAny()]

            return [permissions.IsAuthenticated()]

        return [IsAuthorOrReadOnly()]

    def perform_create(self, serializer):
        """
        Automatically assign the logged-in user as the author.
        """

        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=["post"],
    )
    def like(self, request, pk=None):
        """
        POST /api/posts/{id}/like/
        """

        post = self.get_object()

        like, created = Like.objects.get_or_create(
            post=post,
            user=request.user,
        )

        likes_count = Like.objects.filter(post=post).count()

        if created:
            message = "Post liked successfully."
            status_code = status.HTTP_201_CREATED
        else:
            message = "You have already liked this post."
            status_code = status.HTTP_200_OK

        return Response(
            {
                "detail": message,
                "likes_count": likes_count,
                "is_liked": True,
            },
            status=status_code,
        )

    @action(
        detail=True,
        methods=["post", "delete"],
    )
    def unlike(self, request, pk=None):
        """
        POST/DELETE /api/posts/{id}/unlike/
        """

        post = self.get_object()

        deleted_count, _ = Like.objects.filter(
            post=post,
            user=request.user,
        ).delete()

        likes_count = Like.objects.filter(post=post).count()

        if deleted_count > 0:
            message = "Post unliked successfully."
        else:
            message = "You had not liked this post."

        return Response(
            {
                "detail": message,
                "likes_count": likes_count,
                "is_liked": False,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["get", "post"],
    )
    def comments(self, request, pk=None):
        """
        GET /api/posts/{id}/comments/
        Publicly view comments.

        POST /api/posts/{id}/comments/
        Authenticated users can create comments.
        """

        post = self.get_object()

        if request.method == "GET":
            root_comments = (
                post.comments
                .filter(parent=None)
                .select_related("author")
                .prefetch_related("replies")
            )

            serializer = CommentSerializer(
                root_comments,
                many=True,
                context={"request": request},
            )

            return Response(serializer.data)

        data = request.data.copy()
        data["post"] = post.id

        serializer = CommentSerializer(
            data=data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        serializer.save(author=request.user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )


class CommentViewSet(viewsets.ModelViewSet):
    """
    Comments.

    GET:
        Public

    POST:
        Authenticated users only

    PUT/PATCH/DELETE:
        Comment author only
    """

    queryset = (
        Comment.objects
        .select_related("author", "post")
        .prefetch_related("replies")
        .all()
    )

    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.action in [
            "list",
            "retrieve",
        ]:
            return [permissions.AllowAny()]

        return [IsAuthorOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
