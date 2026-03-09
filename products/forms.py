from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Address, Town, County


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class AddressForm(forms.ModelForm):
    # Keep these for filtering/selection
    county = forms.ModelChoiceField(queryset=County.objects.all(), empty_label="Select a county", required=False)

    class Meta:
        model = Address
        # Add the new name fields here
        # include postal_code now so it can be validated/entered
        fields = ['first_name', 'last_name', 'street', 'town', 'postal_code', 'phone', 'is_default']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'street': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'town': forms.Select(attrs={'class': 'form-control'}),
            'county': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # For new addresses, allow all towns (JavaScript will filter them)
        if not self.instance or not self.instance.pk:
            self.fields['town'].queryset = Town.objects.all()
        # Pre-select logic if editing an existing address
        if self.instance and self.instance.pk and self.instance.town:
            self.fields['county'].initial = self.instance.town.county
            self.fields['town'].queryset = Town.objects.filter(county=self.instance.town.county)

    def clean(self):
        """Custom validation for postal code and phone number."""
        cleaned = super().clean()
        postal = cleaned.get('postal_code', '')
        phone = cleaned.get('phone', '')

        # basic zip/postal code pattern: allow 5 digits or 5-4 format or alphanumeric
        if postal:
            import re
            # Accepts patterns like 12345 or 12345-6789 or alphanumeric with spaces
            if not re.match(r"^[A-Za-z0-9\s\-]{3,20}$", postal):
                self.add_error('postal_code', 'Enter a valid postal/zip code.')

        # phone: ensure it's digits or starts with + and digits
        if phone:
            import re
            if not re.match(r"^\+?\d{7,15}$", phone):
                self.add_error('phone', 'Enter a valid phone number (digits, optionally starting with +).')

        return cleaned