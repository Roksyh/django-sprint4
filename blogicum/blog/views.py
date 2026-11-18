from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm, ProfileForm
from .models import Category, Comment, Post


def visible_posts(user=None):
    visible = Q(is_published=True, category__is_published=True,
                pub_date__lte=timezone.now())
    if user is not None and user.is_authenticated:
        visible |= Q(author=user)
    return Post.objects.select_related(
        'category', 'location', 'author',
    ).filter(visible)


def post_page(request, posts):
    posts = posts.annotate(comment_count=Count('comments')).order_by(
        '-pub_date', '-pk',
    )
    return Paginator(posts, 10).get_page(request.GET.get('page'))


def index(request):
    return render(request, 'blog/index.html', {
        'page_obj': post_page(request, visible_posts()),
    })


def category_posts(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug,
                                 is_published=True)
    posts = visible_posts().filter(category=category)
    return render(request, 'blog/category.html', {
        'category': category, 'page_obj': post_page(request, posts),
    })


def profile(request, username):
    author = get_object_or_404(get_user_model(), username=username)
    posts = visible_posts(request.user).filter(author=author)
    return render(request, 'blog/profile.html', {
        'profile': author, 'page_obj': post_page(request, posts),
    })


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST if request.method == 'POST' else None,
                       instance=request.user)
    if form.is_valid():
        user = form.save()
        return redirect('blog:profile', username=user.username)
    return render(request, 'blog/user.html', {'form': form})


def detail_response(request, post, form):
    return render(request, 'blog/detail.html', {
        'post': post, 'form': form,
        'comments': post.comments.select_related('author'),
    })


def post_detail(request, post_id):
    post = get_object_or_404(visible_posts(request.user), pk=post_id)
    return detail_response(request, post, CommentForm())


@login_required
def create_post(request):
    form = PostForm(request.POST if request.method == 'POST' else None,
                    request.FILES or None)
    if form.is_valid():
        form.instance.author = request.user
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author_id != request.user.pk:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(request.POST if request.method == 'POST' else None,
                    request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author_id != request.user.pk:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form})


@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(visible_posts(request.user), pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        form.instance.author = request.user
        form.instance.post = post
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return detail_response(request, post, form)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id,
                                author=request.user)
    form = CommentForm(request.POST if request.method == 'POST' else None,
                       instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {
        'form': form, 'comment': comment,
    })


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id,
                                author=request.user)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {'comment': comment})
