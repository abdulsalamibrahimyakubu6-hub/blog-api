from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Comment, Like, Post, MicroPost, MicroPostLike

User = get_user_model()


class AuthenticationApiTests(APITestCase):
    def test_register_hashes_password_and_returns_user(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "writer",
                "email": "writer@example.com",
                "password": "A-secure-password-123",
                "password2": "A-secure-password-123",
                "bio": "Tech writer",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="writer")
        self.assertTrue(user.check_password("A-secure-password-123"))
        self.assertEqual(user.bio, "Tech writer")
        self.assertNotIn("password", response.data)

    def test_home_page_returns_api_root_json(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Welcome to the Blog & MicroPost REST API", response.json()["message"])
        self.assertIn("/api/posts/", response.json()["endpoints"]["posts"])

    def test_register_get_request_returns_without_500_error(self):
        response = self.client.get("/api/auth/register/")
        # GET on CreateAPIView renders the browsable API or returns 405 Method Not Allowed cleanly
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED])

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "mismatch_user",
                "email": "mismatch@example.com",
                "password": "Password123!",
                "password2": "Password456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password2", response.data)

    def test_jwt_token_obtain_and_refresh(self):
        User.objects.create_user(
            username="jwtuser",
            email="jwtuser@example.com",
            password="A-secure-password-123",
        )
        # Obtain token
        login_res = self.client.post(
            "/api/auth/token/",
            {
                "username": "jwtuser",
                "password": "A-secure-password-123",
            },
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_res.data)
        self.assertIn("refresh", login_res.data)

        # Refresh token
        refresh_res = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": login_res.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

    def test_authenticated_user_can_read_and_update_own_profile(self):
        user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="A-secure-password-123",
            bio="Original Bio",
        )
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "reader")
        self.assertEqual(response.data["bio"], "Original Bio")

        # Update profile
        patch_res = self.client.patch(
            "/api/auth/me/",
            {"bio": "Updated Bio"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["bio"], "Updated Bio")
        user.refresh_from_db()
        self.assertEqual(user.bio, "Updated Bio")

    def test_update_profile_duplicate_email_fails(self):
        User.objects.create_user(
            username="existing_user",
            email="taken@example.com",
            password="Password123!",
        )
        user = User.objects.create_user(
            username="updating_user",
            email="myemail@example.com",
            password="Password123!",
        )
        self.client.force_authenticate(user=user)

        patch_res = self.client.patch(
            "/api/auth/me/",
            {"email": "taken@example.com"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", patch_res.data)


class PostApiTests(APITestCase):
    def setUp(self):
        self.author1 = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="Password123!",
        )
        self.author2 = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="Password123!",
        )
        self.post1 = Post.objects.create(
            title="Django REST Framework Tips",
            content="Building APIs with DRF is fast and powerful.",
            author=self.author1,
        )
        self.post2 = Post.objects.create(
            title="Learning Python in 2026",
            content="Python continues to dominate web development and AI.",
            author=self.author2,
        )

    def test_list_posts_unauthenticated(self):
        response = self.client.get("/api/posts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 2)

    def test_create_post_authenticated(self):
        self.client.force_authenticate(user=self.author1)
        response = self.client.post(
            "/api/posts/",
            {
                "title": "New Awesome Post",
                "content": "Content of the awesome post.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Awesome Post")
        self.assertEqual(response.data["author"]["username"], "alice")
        self.assertTrue(response.data["slug"].startswith("new-awesome-post"))

    def test_create_post_unauthenticated_fails(self):
        response = self.client.post(
            "/api/posts/",
            {"title": "Unauth Post", "content": "Should fail"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_post_by_author(self):
        self.client.force_authenticate(user=self.author1)
        response = self.client.patch(
            f"/api/posts/{self.post1.id}/",
            {"title": "Updated DRF Tips"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated DRF Tips")

    def test_update_post_by_non_author_forbidden(self):
        self.client.force_authenticate(user=self.author2)
        response = self.client.patch(
            f"/api/posts/{self.post1.id}/",
            {"title": "Hacked Title"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_post_by_author(self):
        self.client.force_authenticate(user=self.author1)
        response = self.client.delete(f"/api/posts/{self.post1.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(id=self.post1.id).exists())

    def test_delete_post_by_non_author_forbidden(self):
        self.client.force_authenticate(user=self.author2)
        response = self.client.delete(f"/api/posts/{self.post1.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_search_posts(self):
        response = self.client.get("/api/posts/?search=Framework")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.post1.id)

    def test_filter_posts_by_author(self):
        response = self.client.get("/api/posts/?author=bob")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.post2.id)

    def test_pagination_custom_page_size(self):
        # Create 15 more posts
        for i in range(15):
            Post.objects.create(
                title=f"Batch Post {i}",
                content=f"Batch content {i}",
                author=self.author1,
            )
        response = self.client.get("/api/posts/?page=1&page_size=5")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertEqual(response.data["count"], 17)
        self.assertIsNotNone(response.data["next"])


class LikeAndCommentApiTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="john", email="john@example.com", password="Password123!"
        )
        self.user2 = User.objects.create_user(
            username="jane", email="jane@example.com", password="Password123!"
        )
        self.post = Post.objects.create(
            title="Interactive Post",
            content="Testing likes and nested comments.",
            author=self.user1,
        )

    def test_like_and_unlike_post(self):
        self.client.force_authenticate(user=self.user2)

        # Like
        like_res = self.client.post(f"/api/posts/{self.post.id}/like/")
        self.assertEqual(like_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(like_res.data["likes_count"], 1)
        self.assertTrue(like_res.data["is_liked"])

        # Check post detail reflects like
        detail_res = self.client.get(f"/api/posts/{self.post.id}/")
        self.assertEqual(detail_res.data["likes_count"], 1)
        self.assertTrue(detail_res.data["is_liked"])

        # Unlike
        unlike_res = self.client.post(f"/api/posts/{self.post.id}/unlike/")
        self.assertEqual(unlike_res.status_code, status.HTTP_200_OK)
        self.assertEqual(unlike_res.data["likes_count"], 0)
        self.assertFalse(unlike_res.data["is_liked"])

    def test_nested_comments_flow(self):
        self.client.force_authenticate(user=self.user2)

        # 1. Create root comment
        root_res = self.client.post(
            f"/api/posts/{self.post.id}/comments/",
            {"content": "This is a root comment."},
            format="json",
        )
        self.assertEqual(root_res.status_code, status.HTTP_201_CREATED)
        root_id = root_res.data["id"]
        self.assertEqual(root_res.data["author"]["username"], "jane")

        # 2. Reply to root comment (nested reply)
        self.client.force_authenticate(user=self.user1)
        reply_res = self.client.post(
            f"/api/posts/{self.post.id}/comments/",
            {"content": "Thank you for the comment!", "parent": root_id},
            format="json",
        )
        self.assertEqual(reply_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(reply_res.data["parent"], root_id)

        # 3. Retrieve post detail and verify nested comments structure
        detail_res = self.client.get(f"/api/posts/{self.post.id}/")
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail_res.data["comments"]), 1)
        root_comment_data = detail_res.data["comments"][0]
        self.assertEqual(root_comment_data["id"], root_id)
        self.assertEqual(len(root_comment_data["replies"]), 1)
        self.assertEqual(
            root_comment_data["replies"][0]["content"],
            "Thank you for the comment!",
        )

    def test_comment_edit_and_delete_permissions(self):
        comment = Comment.objects.create(
            post=self.post, author=self.user1, content="Original comment text."
        )

        # Non-author cannot edit
        self.client.force_authenticate(user=self.user2)
        edit_res = self.client.patch(
            f"/api/comments/{comment.id}/",
            {"content": "Unauthorized edit"},
            format="json",
        )
        self.assertEqual(edit_res.status_code, status.HTTP_403_FORBIDDEN)

        # Author can edit
        self.client.force_authenticate(user=self.user1)
        edit_res = self.client.patch(
            f"/api/comments/{comment.id}/",
            {"content": "Authorized edit"},
            format="json",
        )
        self.assertEqual(edit_res.status_code, status.HTTP_200_OK)
        self.assertEqual(edit_res.data["content"], "Authorized edit")

        # Author can delete
        del_res = self.client.delete(f"/api/comments/{comment.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())


class MicroPostApiTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="micro_user1", email="micro1@example.com", password="Password123!"
        )
        self.user2 = User.objects.create_user(
            username="micro_user2", email="micro2@example.com", password="Password123!"
        )
        self.micropost1 = MicroPost.objects.create(
            user=self.user1, content="Hello MicroPost world!"
        )

    def test_list_microposts(self):
        response = self.client.get("/api/microposts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["content"], "Hello MicroPost world!")

    def test_create_micropost_authenticated(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            "/api/microposts/",
            {"content": "Just setting up my micropost API!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], "Just setting up my micropost API!")
        self.assertEqual(response.data["author"]["username"], "micro_user1")

    def test_like_and_unlike_micropost(self):
        self.client.force_authenticate(user=self.user2)

        # Like micropost
        like_res = self.client.post(f"/api/microposts/{self.micropost1.id}/like/")
        self.assertEqual(like_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(like_res.data["likes_count"], 1)

        # Retrieve micropost detail to verify likes_count & is_liked
        detail_res = self.client.get(f"/api/microposts/{self.micropost1.id}/")
        self.assertEqual(detail_res.data["likes_count"], 1)
        self.assertTrue(detail_res.data["is_liked"])

        # Unlike micropost
        unlike_res = self.client.post(f"/api/microposts/{self.micropost1.id}/unlike/")
        self.assertEqual(unlike_res.status_code, status.HTTP_200_OK)
        self.assertEqual(unlike_res.data["likes_count"], 0)

    def test_repost_micropost(self):
        self.client.force_authenticate(user=self.user2)
        repost_res = self.client.post(
            f"/api/microposts/{self.micropost1.id}/repost/",
            {"content": "Check out this micropost!"},
            format="json",
        )
        self.assertEqual(repost_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(repost_res.data["type"], "repost")
        self.assertEqual(str(repost_res.data["parent_post"]), str(self.micropost1.id))

    def test_delete_micropost_by_non_author_forbidden(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(f"/api/microposts/{self.micropost1.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(MicroPost.objects.filter(id=self.micropost1.id).exists())

    def test_delete_micropost_by_author_succeeds(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f"/api/microposts/{self.micropost1.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MicroPost.objects.filter(id=self.micropost1.id).exists())

