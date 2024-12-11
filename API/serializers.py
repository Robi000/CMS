from rest_framework import serializers
import models as api_model


class AssociationSerializer (serializers.ModelSerializer):
    class Meta:
        model = api_model.Association
        fields = '__all__'

    def create(self, validated_data):
        return super().create(validated_data)
