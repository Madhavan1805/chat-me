# posts/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q # For Search
from django.utils import timezone # For updating last_message_at
from .forms import PostForm, CommentForm, ProfileUpdateForm, UserUpdateForm, MessageForm # MessageForm added
from .models import Post, Comment, Follow, Profile, Conversation, Message 
from django.contrib.auth.models import User

def is_admin(user):
    return user.is_active and user.is_staff 


# HOME / FEED / SEARCH

@login_required 
def home_view(request):
    all_posts = Post.objects.all().select_related('user').prefetch_related('user__profile', 'likes', 'comment_set').order_by('-created_at')
    
    for post in all_posts:
        post.comment_form = CommentForm()
        post.is_liked = post.likes.filter(id=request.user.id).exists() 
    
    context = {'posts': all_posts}
    return render(request, 'posts/home.html', context)

@login_required
def search_view(request):
    query = request.GET.get('q')
    results = {'users': [], 'posts': []}
    
    if query:
        user_results = User.objects.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).exclude(id=request.user.id).select_related('profile')
        
        post_results = Post.objects.filter(
            content__icontains=query
        ).select_related('user').prefetch_related('user__profile').order_by('-created_at')
        
        results['users'] = user_results
        results['posts'] = post_results
        
    context = {'query': query, 'results': results}
    return render(request, 'posts/search_results.html', context)



# AUTHENTICATION / POSTS


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Registration successful! You can now login.")
            return redirect('login')
    else:
        form = UserCreationForm()

    for field in form.fields.values():
        existing = field.widget.attrs.get('class', '')
        field.widget.attrs['class'] = (existing + ' form-control').strip()
        
    context = {'form': form}
    return render(request, 'posts/register.html', context)

@login_required
def create_post_view(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.user = request.user
            new_post.save()
            messages.success(request, "Post created successfully!")
            return redirect('home')
    else:
        form = PostForm()

    context = {'form': form}
    return render(request, 'posts/create_post.html', context)


# PROFILE & FOLLOW VIEWS


@login_required
def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    user_posts = Post.objects.filter(user=profile_user).order_by('-created_at')

    is_following = (
        request.user.is_authenticated
        and profile_user != request.user 
        and Follow.objects.filter(follower=request.user, followed=profile_user).exists()
    )

    context = {
        'profile_user': profile_user,
        'posts': user_posts,
        'is_following': is_following,
        'following_count': profile_user.following.count(), 
        'followers_count': profile_user.followers.count(),
    }
    return render(request, 'posts/profile.html', context)

# posts/views.py

@login_required
def update_profile_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile) 
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile', username=request.user.username)
            
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
        
    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'posts/update_profile.html', context)

@login_required
def toggle_follow_view(request, user_id):
    followed_user = get_object_or_404(User, id=user_id)
    follower_user = request.user

    if follower_user == followed_user:
        messages.error(request, "You cannot follow yourself.")
        return redirect('profile', username=followed_user.username)

    follow_obj, created = Follow.objects.get_or_create(
        follower=follower_user,
        followed=followed_user
    )

    if not created:
        follow_obj.delete()
        messages.info(request, f"You unfollowed {followed_user.username}.")
    else:
        messages.success(request, f"You followed {followed_user.username}!") 
        return redirect('start_chat', user_id=followed_user.id) # Redirect to start chat

    return redirect('profile', username=followed_user.username)

# NEW: DIRECT MESSAGING VIEWS


@login_required
def inbox_view(request):
    # Only show conversations where the user is a participant
    conversations = Conversation.objects.filter(participants=request.user).order_by('-last_message_at')
    
    # Get the other user and last message for display
    for convo in conversations:
        # Get the other participant
        other_user = convo.participants.exclude(id=request.user.id).first()
        convo.other_user = other_user
        convo.last_message = convo.messages.last()
        
    context = {'conversations': conversations}
    return render(request, 'posts/inbox.html', context)


@login_required
def chat_detail_view(request, convo_id):
    conversation = get_object_or_404(Conversation, id=convo_id)
    
    # Check if the user is a participant in this conversation
    if not conversation.participants.filter(id=request.user.id).exists():
        messages.error(request, "You are not a participant in this chat.")
        return redirect('inbox')
        
    messages_list = conversation.messages.all()
    other_user = conversation.participants.exclude(id=request.user.id).first()
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            new_message = form.save(commit=False)
            new_message.conversation = conversation
            new_message.sender = request.user
            new_message.save()
            
            # Update the last message time for ordering in the inbox
            conversation.last_message_at = timezone.now()
            conversation.save()
            
            # Use HTTPResponse to redirect back to the same page (to clear form)
            return redirect('chat_detail', convo_id=convo_id)
    else:
        form = MessageForm()
        
    context = {
        'conversation': conversation,
        'messages_list': messages_list,
        'other_user': other_user,
        'form': form
    }
    return render(request, 'posts/chat_detail.html', context)


@login_required
def start_chat_view(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    current_user = request.user

    if current_user == target_user:
        messages.error(request, "You cannot chat with yourself.")
        return redirect('profile', username=current_user.username)

    # Check if a conversation already exists between these two users
    conversation = Conversation.objects.filter(
        participants=current_user
    ).filter(
        participants=target_user
    ).first()

    if not conversation:
        # If no conversation exists, create a new one
        conversation = Conversation.objects.create()
        conversation.participants.add(current_user, target_user)
        messages.success(request, f"New chat started with {target_user.username}.")

    return redirect('chat_detail', convo_id=conversation.id)

# LIKES / COMMENTS / ADMIN VIEWS

@login_required
def like_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        user = request.user
        
        is_liked = False
        if post.likes.filter(id=user.id).exists():
            post.likes.remove(user)
        else:
            post.likes.add(user)
            is_liked = True
            
        return JsonResponse({
            'is_liked': is_liked,
            'likes_count': post.likes.count()
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.post = post
            new_comment.user = request.user
            new_comment.save()
            messages.success(request, "Comment added successfully!")
            return redirect('home') 
            
    return redirect('home')

@login_required
@user_passes_test(is_admin) 
def admin_dashboard_view(request):
    all_posts = Post.objects.all().order_by('-created_at')
    context = {'posts': all_posts}
    return render(request, 'posts/admin_dashboard.html', context)

@login_required
def update_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if post.user != request.user and not request.user.is_staff:
         messages.error(request, "You are not authorized to edit this post.")
         return redirect('home')
         
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, f'Post by {post.user.username} successfully updated.')
            return redirect('admin_dashboard') if request.user.is_staff else redirect('home')
    else:
        form = PostForm(instance=post)
        
    context = {'form': form, 'post': post}
    return render(request, 'posts/update_post.html', context)

@login_required
def delete_post_view(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.user != request.user and not request.user.is_staff:
         messages.error(request, "You are not authorized to delete this post.")
         return redirect('home')
         
    if request.method == 'POST':
        post.delete()
        messages.warning(request, f'Post by {post.user.username} deleted.')
        return redirect('admin_dashboard') if request.user.is_staff else redirect('home')
        
    context = {'post': post}
    return render(request, 'posts/delete_post.html', context)
