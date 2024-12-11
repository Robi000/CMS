

class GetOnlySameAssociateData():
    look_up_field = 'association'

    def get_queryset(self, *args, **kwargs):
        # user = self.request.user
        # association = user.association
        # lookup_data = {}
        # lookup_data[self.look_up_field] = association
        print(self.look_up_field)

        qs = super().get_queryset(*args, **kwargs)
        # final = qs.objects.filter(owner=user)
        return qs
