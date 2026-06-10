from django import forms


class TutoringLandingForm(forms.Form):
    IB_YEAR_CHOICES = [
        ('', 'Select your IB year'),
        ('pre_ib', 'Pre-IB'),
        ('year_1', 'IB Year 1'),
        ('year_2', 'IB Year 2'),
        ('graduate', 'Graduated / Other'),
    ]
    SUBJECT_CHOICES = [
        ('', 'Primary subject you need help with'),
        ('math', 'Mathematics'),
        ('physics', 'Physics'),
        ('chemistry', 'Chemistry'),
        ('biology', 'Biology'),
        ('economics', 'Economics'),
        ('english', 'English'),
        ('other', 'Other / Multiple subjects'),
    ]

    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control border-radius-4px',
            'placeholder': 'First name',
            'autocomplete': 'given-name',
        }),
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control border-radius-4px',
            'placeholder': 'Last name',
            'autocomplete': 'family-name',
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control border-radius-4px',
            'placeholder': 'Email address',
            'autocomplete': 'email',
        }),
    )
    phone = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control border-radius-4px',
            'placeholder': 'Phone (optional)',
            'autocomplete': 'tel',
        }),
    )
    ib_year = forms.ChoiceField(
        choices=IB_YEAR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control border-radius-4px'}),
    )
    subject = forms.ChoiceField(
        choices=SUBJECT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control border-radius-4px'}),
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control border-radius-4px',
            'placeholder': 'Tell us about your goals or what you struggle with (optional)',
            'rows': 4,
        }),
    )
