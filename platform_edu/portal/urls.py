from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('home/', views.home, name='home'),
    path('', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('logistics-dashboard/', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('personal-information/', views.personal_information, name='personal-information'),
    path('academic-profile/', views.academic_profile, name='academic-profile'),
    path('diagnostics/', views.diagnostics, name='diagnostics'),
    path('portfolio-design/', views.portfolio_design, name='portfolio-design'),
    path('strategic-application/', views.strategic_application, name='strategic-application'),
    path('profile-narrative/', views.profile_narrative, name='profile-narrative'),
    path(
        'interview-preparation/feedback/<int:session_id>/preview/',
        views.preview_interview_feedback,
        name='preview-interview-feedback',
    ),
    path('interview-preparation/', views.interview_preparation, name='interview-preparation'),
    path('offers/', views.offers, name='offers'),
    path('faq/', views.faq, name='faq'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('select-student/<int:student_id>/', views.select_student_profile, name='select-student'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.personal_information, name='account'),
]
