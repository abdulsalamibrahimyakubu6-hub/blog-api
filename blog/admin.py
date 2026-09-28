from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Comment, Like, Post, User, MicroPost, MicroPostLike


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "is_staff", "date_joined")
    search_fields = ("username", "email")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Profile", {"fields": ("bio",)}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Profile", {"fields": ("bio",)}),
    )


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("author", "content", "parent", "created_at")
    readonly_fields = ("created_at",)


class LikeInline(admin.TabularInline):
    model = Like
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "author",
        "likes_count",
        "comments_count",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "author")
    search_fields = ("title", "content", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [CommentInline, LikeInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "parent", "created_at")
    list_filter = ("created_at", "author")
    search_fields = ("content", "author__username", "post__title")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "post__title")


@admin.register(MicroPost)
class MicroPostAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "image", "type", "media_type", "created_at")
    list_filter = ("created_at", "type", "media_type")
    search_fields = ("content", "user__username")

@admin.register(MicroPostLike)
class MicroPostLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "micropost", "user", "created_at")
    list_filter = ("created_at",)



