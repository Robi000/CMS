from rest_framework import serializers
from API import models as api_model
from django.shortcuts import render
from django.http import JsonResponse


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_model.Household
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(HouseholdSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1

    def update(self, instance, validated_data):
        # Allow only specific fields to be updated
        allowed_fields = ["head_of_household", "contact_number",
                          "is_rented", "is_empty_daytime", "documents"]
        for field in allowed_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance


class HouseholdMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_model.HouseholdMember
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(HouseholdMemberSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1
