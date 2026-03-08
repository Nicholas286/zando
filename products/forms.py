from django import forms
from .models import Address, Town, County


class AddressForm(forms.ModelForm):
    # Keep these for filtering/selection
    county = forms.ModelChoiceField(queryset=County.objects.all(), empty_label="Select a county", required=False)

    class Meta:
        model = Address
        # Add the new name fields here
        fields = ['first_name', 'last_name', 'street', 'town', 'phone', 'county', 'is_default']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'street': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'town': forms.Select(attrs={'class': 'form-control'}),
            'county': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-select logic
        if self.instance and self.instance.pk and self.instance.town:
            self.fields['county'].initial = self.instance.town.county
            self.fields['town'].queryset = Town.objects.filter(county=self.instance.town.county)
        # Pre-select logic if editing an existing address
        if self.instance and self.instance.pk and self.instance.town:
            self.fields['county'].initial = self.instance.town.county
            # Optional: Filter towns based on the initial county
            self.fields['town'].queryset = Town.objects.filter(county=self.instance.town.county)