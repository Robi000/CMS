

class GetOnlySameAssociateData():
    look_up_field = 'association'

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        print(user)
        association = user.association
        lookup_data = {}
        lookup_data[self.look_up_field] = association
        print(self.look_up_field)

        qs = super().get_queryset(*args, **kwargs)
        final = qs.filter(**lookup_data)
        return final


class GetOnlyUserHouseholdMemberData():

    look_up_field = "household__Association"

    def get_queryset(self, *args, **kwargs):
        # user = self.request.user
        # association = user.association
        # lookup_data = {}
        # lookup_data[self.look_up_field] = association
        print(self.look_up_field)

        qs = super().get_queryset(*args, **kwargs)
        # final = qs.objects.filter(**lookup_data)
        return qs
