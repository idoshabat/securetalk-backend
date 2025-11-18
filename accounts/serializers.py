from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile , Message

class SignupSerializer(serializers.ModelSerializer):
    public_key = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'public_key']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        public_key = validated_data.pop('public_key')
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user, public_key=public_key)
        return user
    
class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = Profile
        fields = ['username', 'email', 'public_key', 'created_at']

    def update(self, instance, validated_data):
        # Update the related user fields (like email)
        user_data = validated_data.pop('user', {})
        user = instance.user
        if 'email' in user_data:
            user.email = user_data['email']
            user.save()

        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
    
class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.username")
    receiver = serializers.CharField(source="receiver.username")

    class Meta:
        model = Message
        fields = ["id", "sender", "receiver", "content", "timestamp"]
