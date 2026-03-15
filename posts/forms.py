from django import forms
from django.contrib.auth.models import User
from .models import Post, Comment, Profile, Message, Story
from django.forms import Textarea

# POSTS & COMMENTS

class PostForm(forms.ModelForm):
    content = forms.CharField(
        widget=Textarea(attrs={'rows': 4, 'placeholder': 'What is on your mind?', 'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = Post
        fields = ['content', 'image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        
class CommentForm(forms.ModelForm):
    text = forms.CharField(
        label='',
        widget=Textarea(attrs={'rows': 2, 'placeholder': 'Write a comment...', 'class': 'form-control'}),
        required=True
    )
    class Meta:
        model = Comment
        fields = ['text']

# PROFILE UPDATE
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    image = forms.ImageField(required=False)
    
    bio = forms.CharField(
        widget=Textarea(attrs={'rows': 3, 'placeholder': 'Tell us about yourself...', 'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = Profile
        fields = ['image', 'nickname', 'bio', 'theme', 'is_private', 'instagram_url', 'twitter_url', 'facebook_url']
        widgets = {
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'nickname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nickname'}),
            'instagram_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://instagram.com/yourprofile'}),
            'twitter_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://twitter.com/yourprofile'}),
            'facebook_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://facebook.com/yourprofile'}),
            'theme': forms.Select(attrs={'class': 'form-select'}),
        }

# MESSAGING

class MessageForm(forms.ModelForm):
    content = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={'placeholder': 'Type a message...', 'class': 'form-control'}),
        required=False
    )
    class Meta:
        model = Message
        fields = ['content', 'image']

class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['image', 'audio', 'caption']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional caption...'}),
        }
