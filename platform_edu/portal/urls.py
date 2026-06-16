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
    path('faq/', views.faq, name='faq'),
    path('login/', views.login_view, name='login'),
    path('select-student/<int:student_id>/', views.select_student_profile, name='select-student'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.personal_information, name='account'),
]
