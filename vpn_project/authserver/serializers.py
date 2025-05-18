from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'phone_number', 'two_fa_method')
        read_only_fields = ('id',)

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'password', 'password_confirm', 'phone_number', 'two_fa_method')
        read_only_fields = ('id',)

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        if 'phone_number' in validated_data:
            user.phone_number = validated_data['phone_number']
        
        if 'two_fa_method' in validated_data:
            user.two_fa_method = validated_data['two_fa_method']
            
            # Validate phone number if SMS is selected
            if user.two_fa_method == 'SMS' and not user.phone_number:
                raise serializers.ValidationError(
                    {"phone_number": "Phone number is required for SMS authentication."}
                )
        
        user.save()
        return user 