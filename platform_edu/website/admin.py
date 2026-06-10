from django.contrib import admin
from django import forms
import re
from .models import Past_Paper_Videos
from .models import (
    RevisionChapter, RevisionTopic, RevisionSkill,
    QuestionSkillTag, StudentSkillMastery, RevisionAttempt,
    RevisionSubQuestion, RevisionMCQOption,
)
from .models import Math_AI_SL_Questionbank
from .models import Math_AI_HL_Questionbank
from .models import Math_AA_SL_Questionbank
from .models import Math_AA_HL_Questionbank
from .models import Biology_SL_Questionbank
from .models import Webinars_Live
from .models import Physics_SL_Questionbank
from .models import Physics_HL_Questionbank
from .models import Past_Paper_Videos_AA_HL
from .models import Past_Paper_Videos_AA_SL
from .models import Past_Paper_Videos_AI_HL
from .models import Comp_Sci_SL_Questionbank
from .models import Biology_HL_Questionbank
from .models import Comp_Sci_HL_Questionbank
from .models import Uni_Database
from .models import Math_AA_HL_Questionbank_Backup
from .models import Users, TutorSession, StudentManagement, NewsAnnouncement, GeneratedExamsPastPapers
from .models import Past_Paper_Videos_Physics_HL
from .models import Past_Paper_Videos_Physics_SL
from .models import Past_Paper_Videos_Biology_SL, Past_Paper_Videos_Biology_HL
from .models import Past_Paper_Videos_Comp_Sci_SL
from .models import Past_Paper_Videos_Chemistry_SL
from .models import Past_Paper_Videos_Chemistry_HL
from .models import Chemistry_SL_Questionbank
from .models import Chemistry_HL_Questionbank
from .models import Past_Paper_Videos_Comp_Sci_HL
from .models import History_SL_Questionbank
from .models import History_HL_Questionbank
from .models import ApexUsers
# admin.site.register(Math_AI_SL_Questionbank)


class QuestionSkillTagInline(admin.TabularInline):
    model = QuestionSkillTag
    extra = 1
    fields = ('skill', 'weight')
    autocomplete_fields = []

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'skill':
            kwargs['queryset'] = RevisionSkill.objects.select_related('topic__chapter').order_by(
                'topic__chapter__order', 'topic__order', 'order'
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class MathAISLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'chapter2', 'chapter3', 'difficulty', 'sync_to_hl', 'tagged_skills')
    list_display_links = ('id', 'question', 'difficulty')
    list_filter = ('chapter', 'chapter2', 'chapter3', 'difficulty', 'sync_to_hl')
    list_editable = ('sync_to_hl',)
    readonly_fields = ('hl_question_id',)
    inlines = [QuestionSkillTagInline]

    @admin.display(description='Skills tagged')
    def tagged_skills(self, obj):
        tags = obj.skill_tags.select_related('skill').all()
        if not tags:
            return '—'
        return ', '.join(t.skill.slug for t in tags)

admin.site.register(Math_AI_SL_Questionbank, MathAISLQuestionbankAdmin)


class MathAIHLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'chapter2', 'chapter3', 'difficulty')
    list_display_links = ('id', 'question', 'difficulty')
    list_filter = ('chapter', 'chapter2', 'chapter3', 'difficulty')

admin.site.register(Math_AI_HL_Questionbank, MathAIHLQuestionbankAdmin)

class MathAASLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'chapter2', 'chapter3', 'difficulty', 'sync_to_hl')
    list_display_links = ('id', 'question', 'difficulty')
    list_filter = ('chapter', 'chapter2', 'chapter3', 'difficulty', 'sync_to_hl')
    list_editable = ('sync_to_hl',)
    readonly_fields = ('hl_question_id',)

admin.site.register(Math_AA_SL_Questionbank, MathAASLQuestionbankAdmin)


class MathAAHLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'chapter2', 'chapter3', 'difficulty')
    list_display_links = ('id', 'question', 'difficulty')
    list_filter = ('chapter', 'chapter2', 'chapter3', 'difficulty')

admin.site.register(Math_AA_HL_Questionbank, MathAAHLQuestionbankAdmin)

class MathAAHLQuestionbankBackupAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'difficulty')
    list_display_links = ('id', 'question',  'chapter', 'difficulty')

admin.site.register(Math_AA_HL_Questionbank_Backup, MathAAHLQuestionbankBackupAdmin)


class PhysicsSLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'answer', 'chapter', 'difficulty', 'sync_to_hl')
    list_display_links = ('id', 'question',  'chapter', 'difficulty')
    list_filter = ('chapter', 'difficulty', 'sync_to_hl')
    list_editable = ('sync_to_hl',)
    readonly_fields = ('hl_question_id',)

admin.site.register(Physics_SL_Questionbank, PhysicsSLQuestionbankAdmin)

class PhysicsHLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'difficulty')
    list_display_links = ('id', 'question',  'chapter', 'difficulty')

admin.site.register(Physics_HL_Questionbank, PhysicsHLQuestionbankAdmin)


class BiologySLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'answer', 'chapter', 'difficulty', 'sync_to_hl')
    list_display_links = ('id', 'question',  'chapter', 'difficulty')
    list_filter = ('chapter', 'difficulty', 'sync_to_hl')
    list_editable = ('sync_to_hl',)
    readonly_fields = ('hl_question_id',)
    fields = ('question', 'answer', 'chapter', 'difficulty', 'paper', 'correct_answer', 'video', 'marks', 'type', 'verified', 'sync_to_hl', 'hl_question_id')

admin.site.register(Biology_SL_Questionbank, BiologySLQuestionbankAdmin)

class BiologyHLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'difficulty')
    list_display_links = ('id', 'question', 'chapter', 'difficulty')
    list_filter = ('chapter', 'difficulty')
    fields = ('question', 'answer', 'chapter', 'difficulty', 'paper', 'correct_answer', 'video', 'marks', 'type', 'verified')

admin.site.register(Biology_HL_Questionbank, BiologyHLQuestionbankAdmin)

class CompSciSLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'difficulty')
    list_display_links = ('id', 'question',  'chapter', 'difficulty')

admin.site.register(Comp_Sci_SL_Questionbank, CompSciSLQuestionbankAdmin)

class ChemistrySLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'answer', 'chapter', 'difficulty', 'sync_to_hl')
    list_display_links = ('id', 'question', 'chapter', 'difficulty')
    list_filter = ('chapter', 'difficulty', 'sync_to_hl')
    list_editable = ('sync_to_hl',)
    readonly_fields = ('hl_question_id',)

admin.site.register(Chemistry_SL_Questionbank, ChemistrySLQuestionbankAdmin)

class ChemistryHLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'difficulty')
    list_display_links = ('id', 'question', 'chapter', 'difficulty')

admin.site.register(Chemistry_HL_Questionbank, ChemistryHLQuestionbankAdmin)

class HistorySLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'chapter', 'command_term', 'difficulty', 'paper', 'sync_to_hl')
    list_display_links = ('id', 'title', 'chapter', 'difficulty')
    list_filter = ('chapter', 'difficulty', 'paper', 'command_term', 'sync_to_hl')
    list_editable = ('sync_to_hl',)
    search_fields = ('title', 'intro', 'body')
    readonly_fields = ('hl_question_id',)
    fields = ('paper', 'chapter', 'title', 'command_term', 'explanation', 'intro', 'body', 'conclusion', 'difficulty', 'marks', 'type', 'verified', 'sync_to_hl', 'hl_question_id')

admin.site.register(History_SL_Questionbank, HistorySLQuestionbankAdmin)

class HistoryHLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'chapter', 'command_term', 'difficulty', 'paper')
    list_display_links = ('id', 'title', 'chapter', 'difficulty')
    list_filter = ('chapter', 'difficulty', 'paper', 'command_term')
    search_fields = ('title', 'intro', 'body')
    fields = ('paper', 'chapter', 'title', 'command_term', 'explanation', 'intro', 'body', 'conclusion', 'difficulty', 'marks', 'type', 'verified')

admin.site.register(History_HL_Questionbank, HistoryHLQuestionbankAdmin)

class PastPaperVideosCompSciSLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link', 'has_text_answer')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('id', 'month', 'year', 'time_zone', 'paper', 'topic1')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    # ordering = ('month', 'year', 'time_zone', 'paper', 'question')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')
    
    def has_text_answer(self, obj):
        """Show if question has text answer instead of video"""
        if obj.text_answer and obj.text_answer != 'null':
            return '✅ Text'
        return '🎥 Video'
    has_text_answer.short_description = 'Type'

admin.site.register(Past_Paper_Videos_Comp_Sci_SL, PastPaperVideosCompSciSLAdmin)

class CompSciHLQuestionbankAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'chapter', 'difficulty')
    list_display_links = ('id', 'question',  'chapter', 'difficulty')

admin.site.register(Comp_Sci_HL_Questionbank, CompSciHLQuestionbankAdmin)

class PastPaperVideosCompSciHLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('id', 'month', 'year', 'time_zone', 'paper', 'topic1')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    # ordering = ('month', 'year', 'time_zone', 'paper', 'question')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')

admin.site.register(Past_Paper_Videos_Comp_Sci_HL, PastPaperVideosCompSciHLAdmin)


class WebinarsLiveAdminForm(forms.ModelForm):
    class Meta:
        model = Webinars_Live
        fields = '__all__'
        labels = {
            'webinar_date': 'Webinar Date (Polish timezone)',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6, 'cols': 80}),
        }

class WebinarsLiveAdmin(admin.ModelAdmin):
    form = WebinarsLiveAdminForm
    list_display = ('id', 'first_name', 'last_name', 'description', 'webinar_date', 'image_mentor', 'image_main', 'link')
    list_display_links = ('id', 'first_name', 'last_name', 'description', 'webinar_date', 'image_mentor', 'image_main', 'link')
    exclude = ('date_created',)  # Exclude date_created from admin form - it will be auto-set

admin.site.register(Webinars_Live, WebinarsLiveAdmin)


@admin.register(Past_Paper_Videos)
class PastPaperVideosAdmin(admin.ModelAdmin):
    list_display = ('session', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('session', 'time_zone', 'paper', 'topic1')
    search_fields = ('session', 'question', 'topic1', 'topic2', 'topic3')
    ordering = ('session', 'time_zone', 'paper', 'question')


@admin.register(Past_Paper_Videos_AA_HL)
class PastPaperVideosAAHLAdmin(admin.ModelAdmin):
    list_display = ('month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_display_links = ('month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('month', 'year', 'time_zone', 'paper', 'topic1')
    search_fields = ('month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    ordering = ('month', 'year', 'time_zone', 'paper', 'question')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')


@admin.register(Past_Paper_Videos_AA_SL)
class PastPaperVideosAASLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('id', 'month', 'year', 'time_zone', 'paper', 'topic1')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    # ordering = ('month', 'year', 'time_zone', 'paper', 'question')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')


@admin.register(Past_Paper_Videos_AI_HL)
class PastPaperVideosAIHLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('id', 'month', 'year', 'time_zone', 'paper', 'topic1')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    # ordering = ('month', 'year', 'time_zone', 'paper', 'question')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')



@admin.register(Past_Paper_Videos_Physics_HL)
class PastPaperVideosPhysicsHLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'correct_answer', 'link')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('month', 'year', 'time_zone', 'paper', 'topic1', 'access_level')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')


@admin.register(Past_Paper_Videos_Biology_SL)
class PastPaperVideosBiologySLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'correct_answer', 'link')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('month', 'year', 'time_zone', 'paper', 'topic1', 'access_level')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')


@admin.register(Past_Paper_Videos_Biology_HL)
class PastPaperVideosBiologyHLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'correct_answer', 'link')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('month', 'year', 'time_zone', 'paper', 'topic1', 'access_level')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')


@admin.register(Past_Paper_Videos_Physics_SL)
class PastPaperVideosPhysicsSLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'correct_answer', 'link')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('month', 'year', 'time_zone', 'paper', 'topic1', 'access_level')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')


@admin.register(Past_Paper_Videos_Chemistry_SL)
class PastPaperVideosChemistrySLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'correct_answer', 'link')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('month', 'year', 'time_zone', 'paper', 'topic1', 'access_level')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')


@admin.register(Past_Paper_Videos_Chemistry_HL)
class PastPaperVideosChemistryHLAdmin(admin.ModelAdmin):
    list_display = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'correct_answer', 'link')
    list_display_links = ('id', 'month', 'year', 'time_zone', 'paper', 'question', 'topic1', 'topic2', 'topic3', 'link')
    list_filter = ('month', 'year', 'time_zone', 'paper', 'topic1', 'access_level')
    search_fields = ('id', 'month', 'year', 'question', 'topic1', 'topic2', 'topic3')
    exclude = ('session', 'abbreviation_month', 'abbreviation_year')


@admin.register(Uni_Database)
class UniDatabaseAdmin(admin.ModelAdmin):
    list_display = ('program_name', 'uni_name', 'tuition_fee_original', 'degree_type', 'study_mode', 'attendance', 'duration', 'country', 'city', 'ib_requirements', 'tuition_fee_euro', 'link', 'discipline', 'blurred')
    list_display_links = ('program_name', 'uni_name', 'tuition_fee_original', 'degree_type', 'study_mode', 'attendance', 'duration', 'country', 'city', 'ib_requirements', 'tuition_fee_euro', 'link', 'discipline', 'blurred')
    list_filter = ('program_name', 'uni_name', 'tuition_fee_original', 'degree_type', 'study_mode', 'attendance', 'duration', 'country', 'city', 'description', 'ib_requirements', 'ib_requirements_long', 'tuition_fee_euro', 'link', 'discipline', 'blurred')
    search_fields = ('program_name', 'uni_name', 'tuition_fee_original', 'degree_type', 'study_mode', 'attendance', 'duration', 'country', 'city', 'description', 'ib_requirements', 'ib_requirements_long', 'tuition_fee_euro', 'link', 'discipline', 'blurred')
    # ordering = ('month', 'year', 'time_zone', 'paper', 'question')


# Custom Users Model Admin (to distinguish from Django's built-in User model)
@admin.register(Users)
class CustomUsersAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'occupation', 'curriculum', 'school_name', 'registration_date')
    list_display_links = ('id', 'first_name', 'last_name', 'email')
    list_filter = ('occupation', 'curriculum', 'registration_date', 'exam_session')
    search_fields = ('first_name', 'last_name', 'email', 'school_name', 'occupation')
    list_editable = ('occupation',)  # Makes occupation directly editable from the list view
    ordering = ('-registration_date',)
    readonly_fields = ('registration_date', 'customer_id', 'personal_code', 'codes_used')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'avatar', 'school_name')
        }),
        ('Academic Information', {
            'fields': ('curriculum', 'occupation', 'exam_session')
        }),
        ('System Information', {
            'fields': ('registration_date', 'customer_id', 'personal_code', 'code', 'codes_used'),
            'classes': ('collapse',)  # Makes this section collapsible
        }),
    )
    
    # Add some custom actions
    actions = ['make_tutor', 'make_student', 'make_teacher']
    
    def make_tutor(self, request, queryset):
        queryset.update(occupation='Tutor')
        self.message_user(request, f'{queryset.count()} users were successfully marked as Tutors.')
    make_tutor.short_description = "Mark selected users as Tutors"
    
    def make_student(self, request, queryset):
        queryset.update(occupation='Student')
        self.message_user(request, f'{queryset.count()} users were successfully marked as Students.')
    make_student.short_description = "Mark selected users as Students"
    
    def make_teacher(self, request, queryset):
        queryset.update(occupation='Teacher')
        self.message_user(request, f'{queryset.count()} users were successfully marked as Teachers.')
    make_teacher.short_description = "Mark selected users as Teachers"


# TutorSession Model Admin
@admin.register(TutorSession)
class TutorSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_tutor_full_name', 'get_student_full_name', 'session_time', 'topic', 'hours_taught', 'status', 'created_date')
    list_display_links = ('id', 'get_tutor_full_name', 'get_student_full_name', 'topic')
    list_filter = ('status', 'session_time', 'created_date', 'tutor__occupation')
    search_fields = ('tutor_first_name', 'tutor_last_name', 'student_first_name', 'student_last_name', 'topic')
    list_editable = ('status',)
    ordering = ('-session_time',)
    readonly_fields = ('created_date', 'updated_date', 'tutor_first_name', 'tutor_last_name', 'student_first_name', 'student_last_name')
    
    def get_tutor_full_name(self, obj):
        return f"{obj.tutor_first_name} {obj.tutor_last_name}".strip() or f"{obj.tutor.first_name} {obj.tutor.last_name}"
    get_tutor_full_name.short_description = 'Tutor Name (DB)'
    get_tutor_full_name.admin_order_field = 'tutor_first_name'
    
    def get_student_full_name(self, obj):
        return f"{obj.student_first_name} {obj.student_last_name}".strip() or f"{obj.student.first_name} {obj.student.last_name}"
    get_student_full_name.short_description = 'Student Name (DB)'
    get_student_full_name.admin_order_field = 'student_first_name'
    
    # Filter students to only show those with occupation 'Student' and tutors with occupation 'Tutor'
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "student":
            kwargs["queryset"] = Users.objects.filter(occupation='Student')
        if db_field.name == "tutor":
            kwargs["queryset"] = Users.objects.filter(occupation='Tutor')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    fieldsets = (
        ('Session Details', {
            'fields': ('tutor', 'student', 'session_time', 'topic', 'status')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'updated_date'),
            'classes': ('collapse',)
        }),
    )
    
    # Custom actions
    actions = ['mark_completed', 'mark_cancelled', 'mark_scheduled']
    
    def mark_completed(self, request, queryset):
        queryset.update(status='Completed')
        self.message_user(request, f'{queryset.count()} sessions were marked as completed.')
    mark_completed.short_description = "Mark selected sessions as Completed"
    
    def mark_cancelled(self, request, queryset):
        queryset.update(status='Cancelled')
        self.message_user(request, f'{queryset.count()} sessions were marked as cancelled.')
    mark_cancelled.short_description = "Mark selected sessions as Cancelled"
    
    def mark_scheduled(self, request, queryset):
        queryset.update(status='Scheduled')
        self.message_user(request, f'{queryset.count()} sessions were marked as scheduled.')
    mark_scheduled.short_description = "Mark selected sessions as Scheduled"


# StudentManagement Model Admin
@admin.register(StudentManagement)
class StudentManagementAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_student_name', 'get_linked_status', 'get_assigned_tutor', 'parent_email', 'price_charged_to_parents', 'price_given_to_tutor', 'get_profit_margin', 'status', 'created_date')
    list_display_links = ('id', 'get_student_name')
    list_filter = ('status', 'assigned_tutor', 'curriculum', 'created_date')
    search_fields = ('student_first_name', 'student_last_name', 'parent_email', 'assigned_tutor__first_name', 'assigned_tutor__last_name', 'linked_user__first_name', 'linked_user__last_name')
    list_editable = ('status',)
    ordering = ('student_first_name', 'student_last_name')
    readonly_fields = ('created_date', 'updated_date', 'get_profit_margin')
    
    def get_student_name(self, obj):
        return f"{obj.student_first_name} {obj.student_last_name}"
    get_student_name.short_description = 'Student Name'
    get_student_name.admin_order_field = 'student_first_name'
    
    def get_assigned_tutor(self, obj):
        return f"{obj.assigned_tutor.first_name} {obj.assigned_tutor.last_name}"
    get_assigned_tutor.short_description = 'Assigned Tutor'
    get_assigned_tutor.admin_order_field = 'assigned_tutor__first_name'
    
    def get_profit_margin(self, obj):
        margin = obj.profit_margin
        return f"${margin:.2f}"
    get_profit_margin.short_description = 'Profit Margin'
    
    def get_linked_status(self, obj):
        if obj.linked_user:
            return f"✅ {obj.linked_user.email}"
        return "❌ Not Linked"
    get_linked_status.short_description = 'Linked User'
    get_linked_status.admin_order_field = 'linked_user'
    
    def get_multiple_tutors(self, obj):
        """Show if this student has multiple tutors"""
        from .models import StudentManagement
        same_student_count = StudentManagement.objects.filter(
            student_first_name=obj.student_first_name,
            student_last_name=obj.student_last_name,
            parent_email=obj.parent_email
        ).count()
        if same_student_count > 1:
            return f"👥 {same_student_count} tutors"
        return "👤 1 tutor"
    get_multiple_tutors.short_description = 'Tutor Count'
    
    # Filter tutors and students
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assigned_tutor":
            kwargs["queryset"] = Users.objects.filter(occupation='Tutor')
        elif db_field.name == "linked_user":
            kwargs["queryset"] = Users.objects.filter(occupation='Student').order_by('first_name', 'last_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    fieldsets = (
        ('User Account Link', {
            'fields': ('linked_user',),
            'description': 'Link this managed student to an existing User account. This will automatically sync name and email. Note: The same student can be assigned to multiple tutors.'
        }),
        ('Student Information', {
            'fields': ('student_first_name', 'student_last_name', 'student_email')
        }),
        ('Parent Information', {
            'fields': ('parent_email', 'parent_phone', 'address')
        }),
        ('Tutor Assignment', {
            'fields': ('assigned_tutor',)
        }),
        ('Pricing', {
            'fields': ('price_charged_to_parents', 'price_given_to_tutor', 'get_profit_margin')
        }),
        ('Academic Information', {
            'fields': ('curriculum', 'subjects', 'notes')
        }),
        ('Status & Timestamps', {
            'fields': ('status', 'created_date', 'updated_date')
        }),
    )
    
    # Bulk actions
    def make_active(self, request, queryset):
        queryset.update(status='Active')
        self.message_user(request, f'{queryset.count()} students were successfully marked as Active.')
    make_active.short_description = "Mark selected students as Active"
    
    def make_inactive(self, request, queryset):
        queryset.update(status='Inactive')
        self.message_user(request, f'{queryset.count()} students were successfully marked as Inactive.')
    make_inactive.short_description = "Mark selected students as Inactive"
    
    actions = ['make_active', 'make_inactive']


class NewsAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('emoji', 'label', 'color_display', 'is_active', 'order', 'created_date')
    list_display_links = ('emoji', 'label', 'color_display', 'is_active', 'order', 'created_date')
    list_filter = ('is_active', 'color', 'created_date')
    search_fields = ('label', 'popup_title', 'popup_content')
    ordering = ('order', '-created_date')
    
    fieldsets = (
        ('Circle Display', {
            'fields': ('emoji', 'label', 'color'),
            'description': 'These settings control how the circle appears on the home page'
        }),
        ('Popup Content', {
            'fields': ('popup_title', 'popup_content'),
            'description': 'Content shown when users click on the circle. You can use HTML for formatting, buttons, links, etc.'
        }),
        ('Display Settings', {
            'fields': ('is_active', 'order'),
            'description': 'Control visibility and order of announcements'
        }),
    )
    
    def color_display(self, obj):
        """Show colored indicator in admin list"""
        color_map = {
            'purple': '🟣',
            'pink': '🩷',
            'blue': '🔵',
            'green': '🟢',
            'orange': '🟠',
            'red': '🔴',
            'teal': '🩵',
            'yellow': '🟡',
        }
        return f"{color_map.get(obj.color, '⚪')} {obj.get_color_display()}"
    color_display.short_description = 'Color'

admin.site.register(NewsAnnouncement, NewsAnnouncementAdmin)


@admin.register(GeneratedExamsPastPapers)
class GeneratedExamsPastPapersAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'subject', 'paper', 'question_count', 'created_at')
    list_display_links = ('id', 'user')
    list_filter = ('subject', 'paper', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'question_ids', 'chapters')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Exam Details', {
            'fields': ('subject', 'chapters', 'paper', 'question_limit')
        }),
        ('Generated Content', {
            'fields': ('question_ids',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )


@admin.register(ApexUsers)
class ApexUsersAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_id', 'first_name', 'last_name', 'email', 'curriculum', 'occupation', 'confirmed_teacher', 'registration_date')
    list_display_links = ('id', 'email')
    list_filter = ('curriculum', 'occupation', 'confirmed_teacher', 'registration_date')
    search_fields = ('first_name', 'last_name', 'email', 'school_name', 'customer_id')
    readonly_fields = ('registration_date', 'customer_id')
    ordering = ('-registration_date',)
    list_editable = ('confirmed_teacher',)

    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'avatar')
        }),
        ('Account', {
            'fields': ('customer_id',)
        }),
        ('Academic Details', {
            'fields': ('curriculum', 'occupation', 'exam_session', 'school_name')
        }),
        ('Status', {
            'fields': ('confirmed_teacher', 'verified')
        }),
        ('Metadata', {
            'fields': ('registration_date',)
        }),
    )


# ---------------------------------------------------------------------------
# Revision Engine Admin
# ---------------------------------------------------------------------------

@admin.register(RevisionChapter)
class RevisionChapterAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'display_name', 'subject', 'order')
    list_editable = ('order',)
    search_fields = ('slug', 'display_name', 'subject')


@admin.register(RevisionTopic)
class RevisionTopicAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'display_name', 'chapter', 'order')
    list_filter = ('chapter',)
    list_editable = ('order',)
    search_fields = ('slug', 'display_name')


@admin.register(RevisionSkill)
class RevisionSkillAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'display_name', 'topic', 'order')
    list_filter = ('topic', 'topic__chapter')
    list_editable = ('order',)
    search_fields = ('slug', 'display_name')


@admin.register(QuestionSkillTag)
class QuestionSkillTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_id', 'skill', 'weight')
    list_filter = ('skill', 'skill__topic')
    search_fields = ('skill__slug', 'skill__display_name')
    raw_id_fields = ('question',)


@admin.register(StudentSkillMastery)
class StudentSkillMasteryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'skill', 'mastery_score', 'confidence_score', 'attempts_count', 'correct_count', 'last_practiced_at')
    list_filter = ('skill', 'skill__topic')
    search_fields = ('user__email', 'skill__slug')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RevisionAttempt)
class RevisionAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'question_id', 'subquestion', 'selected_label', 'skill', 'is_correct', 'created_at')
    list_filter = ('is_correct', 'skill', 'selected_label')
    search_fields = ('user__email', 'question__id', 'skill__slug')
    readonly_fields = ('created_at',)


class RevisionMCQOptionInline(admin.TabularInline):
    model = RevisionMCQOption
    extra = 4
    max_num = 4
    fields = ('label', 'option_text', 'is_correct')


@admin.register(RevisionSubQuestion)
class RevisionSubQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_id', 'chapter', 'part_label', 'order', 'option_count')
    list_filter = ('question__chapter',)
    search_fields = ('question__question', 'question_text')
    inlines = [RevisionMCQOptionInline]
    raw_id_fields = ('question',)

    @admin.display(description='Chapter')
    def chapter(self, obj):
        return obj.question.chapter

    @admin.display(description='Options')
    def option_count(self, obj):
        return obj.options.count()


@admin.register(RevisionMCQOption)
class RevisionMCQOptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subquestion', 'label', 'option_text', 'is_correct')
    list_filter = ('is_correct', 'label')
    search_fields = ('option_text',)