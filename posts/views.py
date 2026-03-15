# posts/views.py
import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q # For Search
from datetime import timedelta
from django.utils import timezone # For updating last_message_at
from .forms import PostForm, CommentForm, ProfileUpdateForm, UserUpdateForm, MessageForm, StoryForm
from .models import Post, Comment, Follow, Profile, Conversation, Message, Story, StoryReaction, Notification
from django.contrib.auth.models import User

def is_admin(user):
    return user.is_active and user.is_staff 

# HOME / FEED / SEARCH

@login_required 
def home_view(request):
    all_posts = Post.objects.all().select_related('user').prefetch_related('user__profile', 'likes', 'comments').order_by('-created_at')
    
    for post in all_posts:
        post.comment_form = CommentForm()
        post.is_liked = post.likes.filter(id=request.user.id).exists() 
    
    # Get users who have active stories and are: (Self OR Followed OR Public)
    story_users = User.objects.filter(
        stories__created_at__gte=timezone.now() - timedelta(hours=24)
    ).filter(
        Q(id=request.user.id) | 
        Q(followers__follower=request.user) | 
        Q(profile__is_private=False)
    ).distinct().prefetch_related('profile')

    context = {
        'posts': all_posts,
        'story_users': story_users
    }
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
    
    is_following = (
        request.user.is_authenticated
        and profile_user != request.user 
        and Follow.objects.filter(follower=request.user, followed=profile_user).exists()
    )
    
    # Check if accessible (Public OR Following OR Self)
    is_accessible = not profile_user.profile.is_private or is_following or request.user == profile_user
    
    if is_accessible:
        user_posts = Post.objects.filter(user=profile_user).order_by('-created_at')
    else:
        user_posts = Post.objects.none()

    context = {
        'profile_user': profile_user,
        'posts': user_posts,
        'is_following': is_following,
        'following_count': profile_user.following.count(), 
        'followers_count': profile_user.followers.count(),
        'is_accessible': is_accessible,
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
        # NOTIFICATION for follow
        Notification.objects.create(
            sender=follower_user,
            receiver=followed_user,
            notification_type='follow'
        )
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
        
        # Calculate unread messages from that specific user
        convo.unread_count = convo.messages.filter(sender=other_user, is_read=False).count()
        
    context = {'conversations': conversations}
    return render(request, 'posts/inbox.html', context)


@login_required
def chat_detail_view(request, convo_id):
    conversation = get_object_or_404(Conversation, id=convo_id)
    
    # Check if the user is a participant in this conversation
    if not conversation.participants.filter(id=request.user.id).exists():
        messages.error(request, "You are not a participant in this Secret Chat.")
        return redirect('inbox')
        
    other_user = conversation.participants.exclude(id=request.user.id).first()
    
    # Mark messages sent by the other user as read
    unread_messages = conversation.messages.filter(sender=other_user, is_read=False)
    if unread_messages.exists():
        unread_messages.update(is_read=True)

    messages_list = conversation.messages.all()
    
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            new_message = form.save(commit=False)
            new_message.conversation = conversation
            new_message.sender = request.user
            new_message.save()
            
            # Send notification for new message
            if other_user != request.user:
                Notification.objects.create(
                    sender=request.user,
                    receiver=other_user,
                    notification_type='message',
                    message=new_message
                )
            
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
        messages.success(request, f"New Secret Chat started with {target_user.username}.")

    return redirect('chat_detail', convo_id=conversation.id)

@login_required
def edit_message_view(request, message_id):
    if request.method == 'POST':
        message = get_object_or_404(Message, id=message_id, sender=request.user)
        new_content = request.POST.get('content')
        if new_content and new_content.strip():
            message.content = new_content.strip()
            message.save()
            return JsonResponse({'status': 'success', 'content': message.content})
        return JsonResponse({'status': 'error', 'message': 'Content cannot be empty'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def delete_message_view(request, message_id):
    if request.method == 'POST':
        message = get_object_or_404(Message, id=message_id, sender=request.user)
        message.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

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
            
            # NOTIFICATION for like
            if post.user != user:
                Notification.objects.create(
                    sender=user,
                    receiver=post.user,
                    notification_type='like',
                    post=post
                )
            
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
            
            # NOTIFICATION for comment
            if post.user != request.user:
                Notification.objects.create(
                    sender=request.user,
                    receiver=post.user,
                    notification_type='comment',
                    post=post
                )

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

@login_required
def create_story_view(request):
    if request.method == 'POST':
        form = StoryForm(request.POST, request.FILES)
        if form.is_valid():
            story = form.save(commit=False)
            story.user = request.user
            story.save()
            messages.success(request, "Story posted successfully!")
            return redirect('home')
    else:
        form = StoryForm()
    return render(request, 'posts/create_story.html', {'form': form})

@login_required
def story_detail_view(request, user_id):
    story_user = get_object_or_404(User, id=user_id)
    stories = Story.objects.filter(
        user=story_user,
        created_at__gte=timezone.now() - timezone.timedelta(hours=24)
    ).order_by('created_at')
    
    if not stories.exists():
        messages.info(request, "No active stories.")
        return redirect('home')
        
    return render(request, 'posts/story_detail.html', {
        'story_user': story_user,
        'stories': stories
    })

@login_required
def delete_story_view(request, story_id):
    story = get_object_or_404(Story, id=story_id, user=request.user)
    if request.method == 'POST':
        story.delete()
        messages.success(request, "Story deleted successfully!")
        return redirect('home')
    return redirect('home')

@login_required
def react_to_story(request, story_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        emoji = data.get('emoji')
        story = get_object_or_404(Story, id=story_id)
        
        StoryReaction.objects.update_or_create(
            story=story, user=request.user,
            defaults={'emoji': emoji}
        )
        
        if story.user != request.user:
            Notification.objects.get_or_create(
                sender=request.user,
                receiver=story.user,
                notification_type='reaction',
                story=story,
                is_read=False
            )
            
        return JsonResponse({'status': 'success', 'emoji': emoji})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def mark_story_viewed(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    if request.user != story.user:
        story.viewers.add(request.user)
    
    viewers_data = []
    if request.user == story.user:
        viewers_data = [{'username': v.username, 'image': v.profile.image.url} for v in story.viewers.all()]
        
    return JsonResponse({
        'status': 'success', 
        'viewers_count': story.viewers.count(),
        'viewers': viewers_data
    })

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(receiver=request.user).order_by('-created_at')
    # Mark all as read when viewing
    notifications.filter(is_read=False).update(is_read=True)
    
    context = {'notifications': notifications}
    return render(request, 'posts/notifications.html', context)
