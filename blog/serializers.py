from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Comment, Like, Post, MicroPost

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public representation of a user."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "bio", "profile_image", "date_joined"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "password2", "bio"]
        extra_kwargs = {
            "email": {"required": True},
        }

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating authenticated user profile."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "bio", "profile_image", "date_joined"]
        read_only_fields = ["id", "username", "date_joined"]

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        user = self.instance
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk if user else None).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for comments supporting nested replies."""

    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "author",
            "content",
            "parent",
            "replies",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_replies(self, obj):
        replies = obj.replies.all()
        if replies:
            return CommentSerializer(
                replies, many=True, context=self.context
            ).data
        return []

    def validate(self, attrs):
        post = attrs.get("post")
        parent = attrs.get("parent")
        if parent and post and parent.post != post:
            raise serializers.ValidationError(
                {"parent": "The parent comment must belong to the same post."}
            )
        return attrs


class LikeSerializer(serializers.ModelSerializer):
    """Serializer for Likes."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ["id", "post", "user", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class PostSerializer(serializers.ModelSerializer):
    """Serializer for Posts in list and standard operations."""

    author = UserSerializer(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "author",
            "likes_count",
            "comments_count",
            "is_liked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "author",
            "likes_count",
            "comments_count",
            "is_liked",
            "created_at",
            "updated_at",
        ]

    def get_is_liked(self, obj) -> bool:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Check if user liked this post (optimized if preloaded/annotated or query)
            if hasattr(obj, "_prefetched_objects_cache") and "likes" in obj._prefetched_objects_cache:
                return any(like.user_id == request.user.id for like in obj.likes.all())
            return obj.likes.filter(user=request.user).exists()
        return False 


class PostDetailSerializer(PostSerializer):
    """Detailed post serializer including top-level comments with their nested replies."""
    comments = serializers.SerializerMethodField()

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ["comments"]

    def get_comments(self, obj):
        # Top-level comments only (parent is None)
        root_comments = obj.comments.filter(parent=None).select_related("author").prefetch_related("replies")
        return CommentSerializer(root_comments, many=True, context=self.context).data


class MicroPostSerializer(serializers.ModelSerializer):
    """Serializer for MicroPost model."""
    author = UserSerializer(source="user", read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    reposts_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = MicroPost
        fields = [
            "id",
            "user",
            "author",
            "content",
            "image",
            "type",
            "parent_post",
            "media",
            "media_type",
            "created_at",
            "likes_count",
            "reposts_count",
            "is_liked",
        ]
        read_only_fields = ["id", "user", "author", "likes_count", "reposts_count", "is_liked", "created_at"]

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
