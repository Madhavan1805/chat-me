from django import forms
from django.contrib.auth.models import User
from .models import Post, Comment, Profile, Message
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
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    image = forms.ImageField(required=False)
    
    bio = forms.CharField(
        widget=Textarea(attrs={'rows': 3, 'placeholder': 'Tell us about yourself...', 'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = Profile
        fields = ['image', 'bio']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

# MESSAGING

class MessageForm(forms.ModelForm):
    content = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={'placeholder': 'Type a message...', 'class': 'form-control'}),
        required=True
    )
    class Meta:
        model = Message
        fields = ['content']