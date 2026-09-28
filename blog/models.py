from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
import uuid


class User(AbstractUser):
    """Custom user model.

    Email is required and unique; username remains the login identifier.
    """

    email = models.EmailField("email address", unique=True)
    bio = models.TextField(blank=True, max_length=500)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.username


class Post(models.Model):
    """Blog post model with author, slug, timestamps, likes, and comments."""

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    content = models.TextField()
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="posts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "post"
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def likes_count(self) -> int:
        return self.likes.count()

    @property
    def comments_count(self) -> int:
        return self.comments.count()


class Comment(models.Model):
    """Comment on a post. Supports nested replies via self-referential `parent`."""

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField()
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment by {self.author} on {self.post}"


class Like(models.Model):
    """Represents a user liking a post."""

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="likes"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user"], name="unique_post_user_like"
            )
        ]

class MicroPostLike(models.Model):
    """Represents a user liking a MicroPost."""
    micropost = models.ForeignKey('MicroPost', on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='micropost_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['micropost', 'user'], name='unique_micropost_user_like')
        ]

    def __str__(self) -> str:
        return f"{self.user} liked {self.micropost}"

class MicroPost(models.Model):
    """Micro‑blogging post model mimicking Twitter/X"""

    TYPE_CHOICES = [
        ("standard", "Standard"),
        ("repost", "Repost"),
    ]
    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("none", "None"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="micro_posts"
    )
    content = models.CharField(max_length=280)
    image = models.ImageField(upload_to='microposts/', blank=True, null=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="standard")
    parent_post = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reposts",
    )
    media = models.JSONField(default=list, blank=True)
    media_type = models.CharField(
        max_length=10, choices=MEDIA_TYPE_CHOICES, default="none"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.content[:20]}"

    @property
    def likes_count(self) -> int:
        return self.likes.count()

    @property
    def reposts_count(self) -> int:
        return self.reposts.count()
