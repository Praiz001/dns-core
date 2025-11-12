"""
Serializers for users app
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, UserPreference


class UserPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user preferences"""
    
    class Meta:
        model = UserPreference
        fields = ['email', 'push']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    push_token = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    preferences = UserPreferenceSerializer(required=False)
    
    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'push_token', 'preferences']
    
    def create(self, validated_data):
        """Create user with preferences"""
        preferences_data = validated_data.pop('preferences', None)
        
        # Create preferences if provided
        if preferences_data:
            preferences = UserPreference.objects.create(**preferences_data)
            validated_data['preferences'] = preferences
        
        # Create user
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details"""
    
    preferences = UserPreferenceSerializer(read_only=True)
    user_id = serializers.UUIDField(source='id', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'user_id',
            'name',
            'email',
            'push_token',
            'preferences',
            'email_verified',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['user_id', 'email', 'email_verified', 'created_at', 'updated_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = ['name', 'push_token']


class UserPreferenceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user preferences"""
    
    class Meta:
        model = UserPreference
        fields = ['email', 'push']


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    
    token = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate passwords match"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification"""
    
    token = serializers.CharField(required=True)


class NotificationTestRequestSerializer(serializers.Serializer):
    """Optional request payload for test notification publish endpoint"""

    template_code = serializers.CharField(required=False, allow_blank=False, default='WELCOME_TEST')
    variables = serializers.DictField(required=False, default=dict)
    priority = serializers.IntegerField(required=False, min_value=0, max_value=10, default=1)
    metadata = serializers.DictField(required=False, default=dict)
    user_id = serializers.UUIDField(required=False)

