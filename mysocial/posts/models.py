# posts/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
# CORE MODELS

class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.user.username} on {self.created_at.date()}"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on Post ID {self.post.id}"


# SOCIAL MODELS (Follow & Profile)


class Follow(models.Model):
    follower = models.ForeignKey(
        User,
        related_name='following', 
        on_delete=models.CASCADE
    )
    followed = models.ForeignKey(
        User,
        related_name='followers', 
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed')
        
    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    image = models.ImageField(
        upload_to='profile_pics/', 
        default='profile_pics/default.png', 
        blank=True
    )
    
    def __str__(self):
        return f'{self.user.username} Profile'

# Signal functions to automatically create/save Profile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
    
# Conversation Model
class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    last_message_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-last_message_at']
        
    def __str__(self):
        return f"Conversation ID {self.id}"

# Message Model (Represents a single message)
class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, 
        related_name='messages', 
        on_delete=models.CASCADE
    )
    sender = models.ForeignKey(
        User, 
        related_name='sent_messages', 
        on_delete=models.CASCADE
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.username} in Conversation {self.conversation.id}"