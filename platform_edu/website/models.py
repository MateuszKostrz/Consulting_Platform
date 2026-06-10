from django.db import models
import pytz
from datetime import timedelta, datetime
from django.utils import timezone
from ckeditor_uploader.fields import RichTextUploadingField


TIME_ZONE = 'Europe/Warsaw'

class Member(models.Model):

    uni_name = models.CharField(max_length = 200, default = 'None')
    duration = models.CharField(max_length = 200, default = 'None')
    language = models.CharField(max_length = 200, default = 'None')
    country = models.CharField(max_length = 200, default = 'None')
    city = models.CharField(max_length = 200, default = 'None')
    
class Last_User(models.Model):
    email = models.CharField(max_length = 200, default = 'marek.kowalczyk12@vp.pl')
    created_at = models.DateTimeField(auto_now_add=True)


class Users(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length = 100)
    email = models.EmailField(max_length = 200)
    password = models.CharField(max_length = 100, default = 'None')
    registration_date = models.DateTimeField(auto_now_add=True)
    curriculum = models.CharField(max_length = 200)
    occupation = models.CharField(max_length = 200)
    exam_session = models.CharField(max_length = 200, default = 'None')
    code = models.CharField(max_length = 200, default = 'null')
    customer_id = models.CharField(max_length = 20, default = 0)
    personal_code = models.CharField(max_length = 200, default = 'null')
    codes_used = models.FloatField(max_length = 200, default = 0)
    avatar = models.CharField(max_length = 200, default = 'avatar1.png')
    school_name = models.CharField(max_length = 200, default = 'No School Name Given')
    verified = models.BooleanField(default=True)  # Default True for existing users
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_created = models.DateTimeField(blank=True, null=True)
    referral_code = models.CharField(max_length=12, unique=True, blank=True, null=True, help_text="Unique referral code for this user")
    referral_code_used = models.CharField(max_length=12, blank=True, null=True, help_text="Referral code this user activated")

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class ApexUsers(models.Model):
    """Users registered through Apex Tutoring Australia or Top IB Tutors subdomain"""
    SOURCE_CHOICES = [
        ('apex', 'Apex Tuition Australia'),
        ('topibtutors', 'Top IB Tutors'),
    ]
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=200, unique=True)
    password = models.CharField(max_length=100, default='None')
    registration_date = models.DateTimeField(auto_now_add=True)
    curriculum = models.CharField(max_length=200, default='None')
    occupation = models.CharField(max_length=200, default='None')
    exam_session = models.CharField(max_length=200, default='None')
    customer_id = models.CharField(max_length=20, unique=True)
    school_name = models.CharField(max_length=200, default='No School Name Given')
    avatar = models.CharField(max_length=200, default='avatar1.png')
    verified = models.BooleanField(default=True)
    confirmed_teacher = models.BooleanField(default=False, help_text="Whether this teacher is confirmed as part of the company")
    source_domain = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='apex', help_text="Which subdomain the user registered from")
    
    class Meta:
        verbose_name = "Apex User"
        verbose_name_plural = "Apex Users"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class Newsletter(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length = 100)
    email = models.EmailField(max_length = 200)
    registration_date = models.DateTimeField(auto_now_add=True)
    curriculum = models.CharField(max_length = 200)
    occupation = models.CharField(max_length = 200)
    customer_id = models.CharField(max_length = 20, default = 0)
    

class Login(models.Model):
      email = models.CharField(max_length=50)
      type = models.CharField(max_length=50, default = "logging in")
      registration_date = models.DateTimeField(auto_now_add=True)


class Premium_Members(models.Model):
    #   email = models.CharField(max_length=50)
      customer_id = models.CharField(max_length = 20, default = 0)
      stripe_customer_id = models.CharField(max_length = 100, default = 0)
      first_name = models.CharField(max_length=100, blank=True, null=True)
      last_name = models.CharField(max_length=100, blank=True, null=True)
      email = models.EmailField(blank=True, null=True)
      registration_date = models.DateTimeField(auto_now_add=True)
      subscribed = models.CharField(max_length=50, default = "No")
      subscription_end_date = models.DateTimeField(null=True, blank=True)
      subscription_type = models.CharField(
          max_length=20,
          choices=[
              ('none', 'None'),
              ('free', 'Free'),
              ('free_trial', 'Free Trial'),
              ('monthly', 'Monthly'),
              ('yearly', 'Yearly'),
              ('apex_teacher', 'Apex Teacher'),
          ],
          default='none',
          blank=True,
          null=True
      )

class UserQuestionProgress(models.Model):
    """Track user's question completion and marking status for all subjects"""
    user_email = models.EmailField(max_length=200, unique=True)  # User's email as the key
    
    # Math AI SL
    math_ai_sl_completed = models.TextField(default='[]', blank=True)  # JSON list of completed question IDs
    math_ai_sl_marked = models.TextField(default='[]', blank=True)  # JSON list of marked question IDs
    
    # Math AA SL  
    math_aa_sl_completed = models.TextField(default='[]', blank=True)
    math_aa_sl_marked = models.TextField(default='[]', blank=True)
    
    # Math AI HL
    math_ai_hl_completed = models.TextField(default='[]', blank=True)
    math_ai_hl_marked = models.TextField(default='[]', blank=True)
    
    # Math AA HL
    math_aa_hl_completed = models.TextField(default='[]', blank=True)
    math_aa_hl_marked = models.TextField(default='[]', blank=True)
    
    # Physics SL
    physics_sl_completed = models.TextField(default='[]', blank=True)
    physics_sl_marked = models.TextField(default='[]', blank=True)
    
    # Physics HL
    physics_hl_completed = models.TextField(default='[]', blank=True)
    physics_hl_marked = models.TextField(default='[]', blank=True)
    
    # Chemistry SL
    chemistry_sl_completed = models.TextField(default='[]', blank=True)
    chemistry_sl_marked = models.TextField(default='[]', blank=True)
    
    # Chemistry HL
    chemistry_hl_completed = models.TextField(default='[]', blank=True)
    chemistry_hl_marked = models.TextField(default='[]', blank=True)
    
    # Biology SL
    biology_sl_completed = models.TextField(default='[]', blank=True)
    biology_sl_marked = models.TextField(default='[]', blank=True)
    
    # Biology HL
    biology_hl_completed = models.TextField(default='[]', blank=True)
    biology_hl_marked = models.TextField(default='[]', blank=True)
    
    # Computer Science SL
    comp_sci_sl_completed = models.TextField(default='[]', blank=True)
    comp_sci_sl_marked = models.TextField(default='[]', blank=True)
    
    # Computer Science HL
    comp_sci_hl_completed = models.TextField(default='[]', blank=True)
    comp_sci_hl_marked = models.TextField(default='[]', blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Question Progress"
        verbose_name_plural = "User Question Progress"


class Deleted_Premium_Users(models.Model):
    customer_id = models.CharField(max_length=20, default= 0)
    stripe_customer_id = models.CharField(max_length = 100, default = 0)
    subscribed = models.CharField(max_length=50, default="No")
    registration_date = models.DateTimeField(null=True, blank=True, default = 0)
    subscription_end_date = models.DateTimeField(null=True, blank=True, default = 0)
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.registration_date and not self.subscription_end_date:
            # Make sure registration_date is timezone-aware
            if timezone.is_naive(self.registration_date):
                self.registration_date = timezone.make_aware(self.registration_date)

            # Calculate the end_date by adding 30 days to the registration_date
            self.subscription_end_date = self.registration_date + timedelta(days=31)

        super(Deleted_Premium_Users, self).save(*args, **kwargs)
      


class Cricket_AI(models.Model):
      email = models.CharField(max_length = 50)
      sent_date = models.DateTimeField(auto_now_add=True)
      essay_type = models.CharField(max_length = 200)
      subject_level = models.CharField(max_length = 200)
      essay_length = models.CharField(max_length = 200)



class Uni_Database_Free2(models.Model):
      program_name = models.CharField(max_length = 200)
      uni_name = models.CharField(max_length = 200)
      tuition_fee_original = models.CharField(max_length = 200, default = "none")
      degree_type = models.CharField(max_length = 200, default = "none")
      study_mode = models.CharField(max_length = 200, default = "none")
      attendance = models.CharField(max_length = 200, default = "none")
      duration = models.CharField(max_length = 200)
      country = models.CharField(max_length = 200)
      city = models.CharField(max_length = 200)
      description = models.CharField(max_length = 20000, default = "none")
      ib_requirements = models.IntegerField(default = 0)
      ib_requirements_long = models.CharField(max_length = 500, default = "none")
      tuition_fee_euro = models.FloatField(max_length = 200, default = 0)
      link = models.CharField(max_length = 500, default = "none")
      discipline = models.CharField(max_length = 200, default = "none")
      blurred = models.CharField(max_length=3, null=True)


class Uni_Database(models.Model):
      program_name = models.CharField(max_length = 200)
      uni_name = models.CharField(max_length = 200)
      tuition_fee_original = models.CharField(max_length = 200, default = "none")
      degree_type = models.CharField(max_length = 200, default = "none")
      study_mode = models.CharField(max_length = 200, default = "none")
      attendance = models.CharField(max_length = 200, default = "none")
      duration = models.CharField(max_length = 200)
      country = models.CharField(max_length = 200)
      city = models.CharField(max_length = 200)
      description = models.CharField(max_length = 20000, default = "none")
      ib_requirements = models.IntegerField(default = 0)
      ib_requirements_long = models.CharField(max_length = 500, default = "none")
      tuition_fee_euro = models.FloatField(max_length = 200, default = 0)
      link = models.CharField(max_length = 500, default = "none")
      discipline = models.CharField(max_length = 200, default = "none")
      blurred = models.CharField(max_length=20, null=True)
      discipline_survey = models.CharField(max_length = 200, default = "none") 
      
      class Meta:
        verbose_name = "Uni Database"
        verbose_name_plural = "Uni Databases"




class Home_Visits(models.Model):
    #   email = models.CharField(max_length=50)
      entry_date = models.DateTimeField(auto_now_add=True)
      email = models.CharField(max_length=100, default = "No")
      ip_address = models.CharField(max_length=200, default = "null")
      country = models.CharField(max_length=200, default = "null")
      city = models.CharField(max_length=200, default = "null")
      


class Survey_Response(models.Model):
    email = models.EmailField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    subjects_1 = models.CharField(max_length=255)
    subjects_2 = models.CharField(max_length=255)
    subjects_3 = models.CharField(max_length=255)
    countries_1 = models.CharField(max_length=255)
    countries_2 = models.CharField(max_length=255)
    countries_3 = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20 , default = "null")
    
    def __str__(self):
        return f"SurveyResponse {self.id} - {self.email}"

class Survey_Response_Subjects(models.Model):
    date = models.DateTimeField(default=datetime.now)
    email = models.EmailField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    math = models.CharField(max_length=255)
    science = models.CharField(max_length=255)
    subject_3 = models.CharField(max_length=255)
    subject_4 = models.CharField(max_length=255)
    subject_5 = models.CharField(max_length=255)
    subject_6 = models.CharField(max_length=255)
    
    def __str__(self):
        return f"SurveyResponseSubjects {self.id} - {self.email}"


class User_Journey(models.Model):
    email = models.CharField(max_length=255, db_index=True)
    visitor_id = models.CharField(max_length=64, null=True, blank=True, default=None)
    ip_address = models.CharField(max_length=255, default="null", db_index=True)
    device = models.CharField(max_length=255, default="null")
    country = models.CharField(max_length=255, default="null")
    journey_path = models.JSONField()
    session_start = models.DateTimeField()
    session_end = models.DateTimeField(db_index=True)
    date_created = models.DateTimeField()

    def __str__(self):
        return f"{self.email} journey from {self.session_start} to {self.session_end}"


class User_Journey_Archive(models.Model):
    """Archive of old User_Journey rows, kept for historical reference."""
    email = models.CharField(max_length=255, db_index=True)
    visitor_id = models.CharField(max_length=64, null=True, blank=True, default=None)
    ip_address = models.CharField(max_length=255, default="null")
    device = models.CharField(max_length=255, default="null")
    country = models.CharField(max_length=255, default="null")
    journey_path = models.JSONField()
    session_start = models.DateTimeField()
    session_end = models.DateTimeField()
    date_created = models.DateTimeField()
    archived_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[Archive] {self.email} journey from {self.session_start} to {self.session_end}"


        
class Total_Entries(models.Model):
    date = models.DateTimeField()
    unique_cookies_all = models.CharField(max_length=100, default = "null")
    unique_cookies_no_unknown = models.CharField(max_length=100, default = "null")
    unique_cookies_no_db = models.CharField(max_length=100, default = "null")
    unique_cookies_logged_in = models.CharField(max_length=100, default = "null")
    full_journey = models.CharField(max_length=1000, default = "null")




class Past_Paper_Videos(models.Model):
    session = models.CharField(max_length=100, default = "null")
    month = models.CharField(max_length=100, default = "null")
    year = models.CharField(max_length=100, default = "null")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('null', 'null'),
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default='null')
    paper = models.CharField(max_length=100, default = "null")
    question = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('number_skills', 'Number Skills'),
        ('seq_series', 'Sequences & Series'),
        ('systems_of_equations', 'Systems of Linear Equations'),
        ('linear_equations_graphs', 'Linear Equations & Graphs'),
        ('application_of_functions', 'Application of Functions'),
        ('properties_of_functions', 'Properties of Functions'),
        ('trigonometry', 'Trigonometry'),
        ('voronoi_diagrams', 'Voronoi Diagrams'),
        ('descriptive_statistics', 'Descriptive Statistics'),
        ('bivariate_statistics', 'Bivariate Statistics'),
        ('probability', 'Probability'),
        ('distributions', 'Distributions'),
        ('geometry_shapes', 'Geometry of 3D Shapes'),
        ('hypothesis_testing', 'Hypothesis Testing'),
        ('differentiation', 'Differentiation'),
        ('integration', 'Integration'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")
    
    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium', help_text="Access level for this video")

    class Meta:
        verbose_name = "Math AI SL - Past Paper Video"
        verbose_name_plural = "Math AI SL - Past Paper Videos"



class Past_Paper_Videos_AI_HL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default = "May")
    year = models.CharField(max_length=10, default = "2024")
    session = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default = "1")

    PAPERS = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default = "1")
    question = models.CharField(max_length=100, default = "1")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('number_skills', 'Number Skills'),
        ('seq_series', 'Sequences & Series'),
        ('complex_numbers', 'Complex Numbers'),
        ('matrices', 'Matrices'),
        ('systems_of_equations', 'Systems of Linear Equations'),
        ('linear_equations_graphs', 'Linear Equations & Graphs'),
        ('application_of_functions', 'Application of Functions'),
        ('properties_of_functions', 'Properties of Functions'),
        ('function_transformations', 'Function Transformations'),
        ('trigonometry', 'Trigonometry'),
        ('trigonometric_functions', 'Trigonometric Functions'),
        ('gemoetric_transformations', 'Geometric Transformations'),
        ('voronoi_diagrams', 'Voronoi Diagrams'),
        ('vectors', 'Vectors'),
        ('graph_theory', 'Graph Theory'),
        ('descriptive_statistics', 'Descriptive Statistics'),
        ('bivariate_statistics', 'Bivariate Statistics'),
        ('probability', 'Probability'),
        ('distributions', 'Distributions'),
        ('geometry_shapes', 'Geometry of 3D Shapes'),
        ('hypothesis_testing', 'Hypothesis Testing'),
        ('confidence_intervals', 'Estimations & Confidence Intervals'),
        ('differentiation', 'Differentiation'),
        ('integration', 'Integration'),
        ('differential_equations', 'Differential Equations'),
        ('kinematics', 'Kinematics'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")
    
    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium', help_text="Access level for this video")

    def save(self, *args, **kwargs):
        # Set session to month + year
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        
        # Set abbreviation_month to first letter of month
        if self.month:
            self.abbreviation_month = self.month[0].upper()  # First letter, uppercase
        
        # Set abbreviation_year to last two digits of year
        if self.year:
            self.abbreviation_year = self.year[-2:]  # Last two digits
            
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "Math AI HL - Past Paper Video"
        verbose_name_plural = "Math AI HL - Past Paper Videos"

class Past_Paper_Videos_AA_SL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default = "May")
    year = models.CharField(max_length=10, default = "2024")
    session = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default = "1")

    PAPERS = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default = "1")
    question = models.CharField(max_length=100, default = "1")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('seq_series', 'Sequences & Series'),
        ('exp_and_logs', 'Exponentials and Logarithms'),
        ('binomial_expansion', 'Binomial Expansion'),
        ('proofs', 'Proofs'),
        ('properties_of_functions', 'Properties of Functions'),
        ('quadratic_functions', 'Quadratic Functions'),
        ('rational_functions', 'Rational Functions'),
        ('exp_and_logs_functions', 'Exponential and Logarithmic Functions'),
        ('function_transformations', 'Function Transformations'),
        ('geometry', 'Geometry'),
        ('trig_functions', 'Trigonometric Functions'),
        ('statistics', 'Statistics'),
        ('bivariate_stats', 'Bivariate Statistics'),
        ('probability', 'Probability'),
        ('distributions', 'Distributions'),
        ('integral_calculus', 'Integral Calculus'),
        ('differential_calculus', 'Differential Calculus'),
        ('kinematics', 'Kinematics'),

    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")
    
    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium', help_text="Access level for this video")

    def save(self, *args, **kwargs):
        # Set session to month + year
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        
        # Set abbreviation_month to first letter of month
        if self.month:
            self.abbreviation_month = self.month[0].upper()  # First letter, uppercase
        
        # Set abbreviation_year to last two digits of year
        if self.year:
            self.abbreviation_year = self.year[-2:]  # Last two digits
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Math AA SL - Past Paper Video"
        verbose_name_plural = "Math AA SL - Past Paper Videos"



class Past_Paper_Videos_Physics_SL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
        ('Specimen', 'Specimen'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default = "May")
    year = models.CharField(max_length=10, default = "2024")
    session = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default = "1")

    PAPERS = [
        ('1', 'Paper 1'),
        ('1A', 'Paper 1A'),
        ('1B', 'Paper 1B'),
        ('2', 'Paper 2'),
        ('3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default = "1")
    question = models.CharField(max_length=100, default = "1")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('kinematics', 'Kinematics'),
        ('forces_and_momentum', 'Forces and Momentum'),
        ('work_energy_power', 'Work, Energy, and Power'),
        ('thermal_energy', 'Thermal Energy'),
        ('greenhouse_effect', 'Greenhouse Effect'),
        ('ideal_gas_model', 'Ideal Gas Model'),
        ('electric_circuits', 'Electric Circuits'),
        ('simple_harmonic_motion', 'Simple Harmonic Motion'),
        ('wave_model', 'Wave Model'),
        ('wave_phenomena', 'Wave Phenomena'),
        ('standing_waves', 'Standing Wave and Resonance'),
        ('doppler_effect', 'Doppler Effect'),
        ('gravitational_fields', 'Gravitational Fields'),
        ('electric_magnetic_fields', 'Electric and Magnetic Fields'),
        ('motion_in_fields', 'Motion in Electromagnetic Fields'),
        ('structure_atom', 'Structure of the Atom'),
        ('radioactive_decay', 'Radioactive Decay'),
        ('fission', 'Fission'),
        ('fusion_and_stars', 'Fusion and Stars'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")

    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]
    correct_answer = models.CharField(
        max_length=10, choices=CORRECT_ANSWERS, null=True, blank=True,
        help_text="For Paper 1A multiple-choice questions only"
    )

    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium', help_text="Access level for this video")

    def save(self, *args, **kwargs):
        # Set session to month + year
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        
        # Set abbreviation_month to first letter of month
        if self.month:
            self.abbreviation_month = self.month[0].upper()  # First letter, uppercase
        
        # Set abbreviation_year to last two digits of year
        if self.year:
            self.abbreviation_year = self.year[-2:]  # Last two digits
            
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "Physics SL - Past Paper Video"
        verbose_name_plural = "Physics SL - Past Paper Videos"


class Past_Paper_Videos_Physics_HL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
        ('Specimen', 'Specimen'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default = "May")
    year = models.CharField(max_length=10, default = "2024")
    session = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default = "1")

    PAPERS = [
        ('1', 'Paper 1'),
        ('1A', 'Paper 1A'),
        ('1B', 'Paper 1B'),
        ('2', 'Paper 2'),
        ('3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default = "1")
    question = models.CharField(max_length=100, default = "1")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('kinematics', 'Kinematics'),
        ('forces_and_momentum', 'Forces and Momentum'),
        ('work_energy_power', 'Work, Energy, and Power'),
        ('rigid_body_mechanics', 'Rigid Body Mechanics'),
        ('galilean_and_special_relativity', 'Galilean and Special Relativity'),
        ('thermal_energy', 'Thermal Energy'),
        ('greenhouse_effect', 'Greenhouse Effect'),
        ('ideal_gas_model', 'Ideal Gas Model'),
        ('thermodynamics', 'Thermodynamics'),
        ('electric_circuits', 'Electric Circuits'),
        ('simple_harmonic_motion', 'Simple Harmonic Motion'),
        ('wave_model', 'Wave Model'),
        ('wave_phenomena', 'Wave Phenomena'),
        ('standing_waves', 'Standing Wave and Resonance'),
        ('doppler_effect', 'Doppler Effect'),
        ('gravitational_fields', 'Gravitational Fields'),
        ('electric_magnetic_fields', 'Electric and Magnetic Fields'),
        ('motion_in_fields', 'Motion in Electromagnetic Fields'),
        ('induction', 'Induction'),
        ('structure_atom', 'Structure of the Atom'),
        ('quantum_physics', 'Quantum Physics'),
        ('radioactive_decay', 'Radioactive Decay'),
        ('fission', 'Fission'),
        ('fusion_and_stars', 'Fusion and Stars'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")

    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]
    correct_answer = models.CharField(
        max_length=10, choices=CORRECT_ANSWERS, null=True, blank=True,
        help_text="For Paper 1A multiple-choice questions only"
    )

    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium', help_text="Access level for this video")

    def save(self, *args, **kwargs):
        # Set session to month + year
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        
        # Set abbreviation_month to first letter of month
        if self.month:
            self.abbreviation_month = self.month[0].upper()  # First letter, uppercase
        
        # Set abbreviation_year to last two digits of year
        if self.year:
            self.abbreviation_year = self.year[-2:]  # Last two digits
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Physics HL - Past Paper Video"
        verbose_name_plural = "Physics HL - Past Paper Videos"



class Past_Paper_Videos_Biology_SL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
        ('Specimen', 'Specimen'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default='May')
    year = models.CharField(max_length=10, default='2024')
    session = models.CharField(max_length=100, default='null')

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default='1')

    PAPERS = [
        ('1', 'Paper 1'),
        ('1A', 'Paper 1A'),
        ('1B', 'Paper 1B'),
        ('2', 'Paper 2'),
        ('3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default='1')
    question = models.CharField(max_length=100, default='1')
    abbreviation_month = models.CharField(max_length=100, default='null')
    abbreviation_year = models.CharField(max_length=100, default='null')

    CHAPTERS = [
        ('null', 'null'),
        ('water', 'Water'),
        ('nucleic_acids', 'Nucleic Acids'),
        ('cell_structure', 'Cell Structure'),
        ('diversity_of_organisms', 'Diversity of Organisms'),
        ('evolution_and_speciation', 'Evolution and Speciation'),
        ('conservation_of_biodiversity', 'Conservation of Biodiversity'),
        ('carbohydrates_and_lipids', 'Carbohydrates & Lipids'),
        ('proteins', 'Proteins'),
        ('membranes_and_membrane_transport', 'Membranes and Membrane Transport'),
        ('organelles_and_compartmentalization', 'Organelles and Compartmentalization'),
        ('cell_specialization', 'Cell Specialization'),
        ('gas_exchange', 'Gas Exchange'),
        ('transport', 'Transport'),
        ('adaptation_to_environment', 'Adaptation to Environment'),
        ('ecological_niches', 'Ecological Niches'),
        ('enzymes_metabolism', 'Enzymes and Metabolism'),
        ('cell_respiration', 'Cell Respiration'),
        ('photosynthesis', 'Photosynthesis'),
        ('neural_signaling', 'Neural Signaling'),
        ('integration_of_body_systems', 'Integration of Body Systems'),
        ('defence_against_disease', 'Defence Against Disease'),
        ('population_and_communities', 'Population and Communities'),
        ('transfer_of_energy', 'Transfer of Energy and Matter'),
        ('dna_replication', 'DNA Replication'),
        ('protein_synthesis', 'Protein Synthesis'),
        ('mutations_editing', 'Mutations and Gene Editing'),
        ('natural_selection', 'Natural Selection'),
        ('inheritance', 'Inheritance'),
        ('climate_change', 'Climate Change'),
        ('water_potential', 'Water Potential'),
        ('cell_division', 'Cell Division'),
        ('reproduction', 'Reproduction'),
        ('stability_change', 'Stability & Change'),
        ('homeostasis', 'Homeostasis'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default='null')
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default='null')
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default='null')
    link = models.CharField(max_length=200, default='null')

    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]
    correct_answer = models.CharField(
        max_length=10, choices=CORRECT_ANSWERS, null=True, blank=True,
        help_text="For Paper 1A multiple-choice questions only"
    )

    question_screenshots_url = models.TextField(
        null=True, blank=True,
        help_text="ImageKit URL for question screenshots (comma-separated if multiple)"
    )
    markscheme_screenshots_url = models.TextField(
        null=True, blank=True,
        help_text="ImageKit URL for markscheme screenshots. Leave blank for MCQ questions."
    )

    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium')

    def save(self, *args, **kwargs):
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        if self.month:
            self.abbreviation_month = self.month[0].upper()
        if self.year:
            self.abbreviation_year = self.year[-2:]
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Biology SL - Past Paper Video"
        verbose_name_plural = "Biology SL - Past Paper Videos"


class Past_Paper_Videos_Biology_HL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
        ('Specimen', 'Specimen'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default='May')
    year = models.CharField(max_length=10, default='2024')
    session = models.CharField(max_length=100, default='null')

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default='1')

    PAPERS = [
        ('1', 'Paper 1'),
        ('1A', 'Paper 1A'),
        ('1B', 'Paper 1B'),
        ('2', 'Paper 2'),
        ('3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default='1')
    question = models.CharField(max_length=100, default='1')
    abbreviation_month = models.CharField(max_length=100, default='null')
    abbreviation_year = models.CharField(max_length=100, default='null')

    CHAPTERS = [
        ('null', 'null'),
        ('water', 'Water'),
        ('nucleic_acids', 'Nucleic Acids'),
        ('origin_of_cells', 'Origin of Cells'),
        ('viruses', 'Viruses'),
        ('classification', 'Classification'),
        ('muscle_and_motility', 'Muscle and Motility'),
        ('chemical_signaling', 'Chemical Signaling'),
        ('cell_structure', 'Cell Structure'),
        ('diversity_of_organisms', 'Diversity of Organisms'),
        ('evolution_and_speciation', 'Evolution and Speciation'),
        ('conservation_of_biodiversity', 'Conservation of Biodiversity'),
        ('carbohydrates_and_lipids', 'Carbohydrates & Lipids'),
        ('proteins', 'Proteins'),
        ('membranes_and_membrane_transport', 'Membranes and Membrane Transport'),
        ('organelles_and_compartmentalization', 'Organelles and Compartmentalization'),
        ('cell_specialization', 'Cell Specialization'),
        ('gas_exchange', 'Gas Exchange'),
        ('transport', 'Transport'),
        ('adaptation_to_environment', 'Adaptation to Environment'),
        ('ecological_niches', 'Ecological Niches'),
        ('enzymes_metabolism', 'Enzymes and Metabolism'),
        ('cell_respiration', 'Cell Respiration'),
        ('photosynthesis', 'Photosynthesis'),
        ('neural_signaling', 'Neural Signaling'),
        ('integration_of_body_systems', 'Integration of Body Systems'),
        ('defence_against_disease', 'Defence Against Disease'),
        ('population_and_communities', 'Population and Communities'),
        ('transfer_of_energy', 'Transfer of Energy and Matter'),
        ('dna_replication', 'DNA Replication'),
        ('protein_synthesis', 'Protein Synthesis'),
        ('mutations_editing', 'Mutations and Gene Editing'),
        ('natural_selection', 'Natural Selection'),
        ('inheritance', 'Inheritance'),
        ('climate_change', 'Climate Change'),
        ('water_potential', 'Water Potential'),
        ('cell_division', 'Cell Division'),
        ('reproduction', 'Reproduction'),
        ('stability_change', 'Stability & Change'),
        ('homeostasis', 'Homeostasis'),
        ('gene_expression', 'Gene Expression'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default='null')
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default='null')
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default='null')
    link = models.CharField(max_length=200, default='null')

    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]
    correct_answer = models.CharField(
        max_length=10, choices=CORRECT_ANSWERS, null=True, blank=True,
        help_text="For Paper 1A multiple-choice questions only"
    )

    question_screenshots_url = models.TextField(
        null=True, blank=True,
        help_text="ImageKit URL for question screenshots (comma-separated if multiple)"
    )
    markscheme_screenshots_url = models.TextField(
        null=True, blank=True,
        help_text="ImageKit URL for markscheme screenshots. Leave blank for MCQ questions."
    )

    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium')

    def save(self, *args, **kwargs):
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        if self.month:
            self.abbreviation_month = self.month[0].upper()
        if self.year:
            self.abbreviation_year = self.year[-2:]
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Biology HL - Past Paper Video"
        verbose_name_plural = "Biology HL - Past Paper Videos"


class Past_Paper_Videos_AA_HL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default = "May")
    year = models.CharField(max_length=10, default = "2024")
    session = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default = "1")

    PAPERS = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default = "1")
    question = models.CharField(max_length=100, default = "1")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('seq_series', 'Sequences & Series'),
        ('exp_and_logs', 'Exponentials and Logarithms'),
        ('binomial_expansion', 'Binomial Expansion'),
        ('proofs', 'Proofs'),
        ('counting_principles', 'Counting Principles'),
        ('complex_numbers', 'Complex Numbers'),
        ('systems_of_equations', 'Systems of Equations'),
        ('properties_of_functions', 'Properties of Functions'),
        ('quadratic_functions', 'Quadratic Functions'),
        ('rational_functions', 'Rational Functions'),
        ('exp_and_logs_functions', 'Exponential and Logarithmic Functions'),
        ('function_transformations', 'Function Transformations'),
        ('polynomials', 'Polynomials'),
        ('mod_inequalities', 'Mod & Inequalities'),
        ('geometry', 'Geometry'),
        ('trig_functions', 'Trigonometric Functions'),
        ('vectors', 'Vectors'),
        ('statistics', 'Statistics'),
        ('bivariate_stats', 'Bivariate Statistics'),
        ('probability', 'Probability'),
        ('distributions', 'Distributions'),
        ('integral_calculus', 'Integral Calculus'),
        ('differential_calculus', 'Differential Calculus'),
        ('kinematics', 'Kinematics'),
        ('maclaurin_series', 'MacLaurin Series'),
        ('differential_equations', 'Differential Equations'),

    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")
    
    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium', help_text="Access level for this video")

    def save(self, *args, **kwargs):
        # Set session to month + year
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        
        # Set abbreviation_month to first letter of month
        if self.month:
            self.abbreviation_month = self.month[0].upper()  # First letter, uppercase
        
        # Set abbreviation_year to last two digits of year
        if self.year:
            self.abbreviation_year = self.year[-2:]  # Last two digits
            
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "Math AA HL - Past Paper Video"
        verbose_name_plural = "Math AA HL - Past Paper Videos"


class Past_Paper_Videos_Chemistry_SL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
        ('Specimen', 'Specimen'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default = "May")
    year = models.CharField(max_length=10, default = "2024")
    session = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default = "1")

    PAPERS = [
        ('1', 'Paper 1'),
        ('2', 'Paper 2'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default = "1")
    question = models.CharField(max_length=100, default = "1")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('introduction_particulate_nature', 'S1.1 Introduction to the particulate nature of matter'),
        ('nuclear_atom', 'S1.2 The nuclear atom'),
        ('electron_configurations', 'S1.3 Electron configurations'),
        ('counting_particles_mole', 'S1.4 Counting particles by mass: The mole'),
        ('ideal_gases', 'S1.5 Ideal gases'),
        ('ionic_model', 'S2.1 The ionic model'),
        ('covalent_model', 'S2.2 The covalent model'),
        ('metallic_model', 'S2.3 The metallic model'),
        ('models_to_materials', 'S2.4 From models to materials'),
        ('periodic_table', 'S3.1 The periodic table: Classification of elements'),
        ('functional_groups', 'S3.2 Functional groups: Classification of organic compounds'),
        ('measuring_enthalpy', 'R1.1 Measuring enthalpy changes'),
        ('energy_cycles', 'R1.2 Energy cycles in reactions'),
        ('energy_from_fuels', 'R1.3 Energy from fuels'),
        ('amount_chemical_change', 'R2.1 How much? The amount of chemical change'),
        ('rate_chemical_change', 'R2.2 How fast? The rate of chemical change'),
        ('extent_chemical_change', 'R2.3 How far? The extent of chemical change'),
        ('proton_transfer', 'R3.1 Proton transfer reactions'),
        ('electron_transfer', 'R3.2 Electron transfer reactions'),
        ('electron_sharing', 'R3.3 Electron sharing reactions'),
        ('electron_pair_sharing', 'R3.4 Electron-pair sharing reactions'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")

    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]
    correct_answer = models.CharField(
        max_length=10, choices=CORRECT_ANSWERS, null=True, blank=True,
        help_text="For Paper 1A multiple-choice questions only"
    )

    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium', help_text="Access level for this video")

    def save(self, *args, **kwargs):
        # Set session to month + year
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        
        # Set abbreviation_month to first letter of month
        if self.month:
            self.abbreviation_month = self.month[0].upper()  # First letter, uppercase
        
        # Set abbreviation_year to last two digits of year
        if self.year:
            self.abbreviation_year = self.year[-2:]  # Last two digits
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Chemistry SL - Past Paper Video"
        verbose_name_plural = "Chemistry SL - Past Paper Videos"


class Past_Paper_Videos_Chemistry_HL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
        ('Specimen', 'Specimen'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default = "May")
    year = models.CharField(max_length=10, default = "2024")
    session = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default = "1")

    PAPERS = [
        ('1', 'Paper 1'),
        ('2', 'Paper 2'),
        ('3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default = "1")
    question = models.CharField(max_length=100, default = "1")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('introduction_particulate_nature', 'S1.1 Introduction to the particulate nature of matter'),
        ('nuclear_atom', 'S1.2 The nuclear atom'),
        ('electron_configurations', 'S1.3 Electron configurations'),
        ('counting_particles_mole', 'S1.4 Counting particles by mass: The mole'),
        ('ideal_gases', 'S1.5 Ideal gases'),
        ('ionic_model', 'S2.1 The ionic model'),
        ('covalent_model', 'S2.2 The covalent model'),
        ('metallic_model', 'S2.3 The metallic model'),
        ('models_to_materials', 'S2.4 From models to materials'),
        ('periodic_table', 'S3.1 The periodic table: Classification of elements'),
        ('functional_groups', 'S3.2 Functional groups: Classification of organic compounds'),
        ('measuring_enthalpy', 'R1.1 Measuring enthalpy changes'),
        ('energy_cycles', 'R1.2 Energy cycles in reactions'),
        ('energy_from_fuels', 'R1.3 Energy from fuels'),
        ('entropy_spontaneity', 'R1.4 Entropy and spontaneity'),
        ('amount_chemical_change', 'R2.1 How much? The amount of chemical change'),
        ('rate_chemical_change', 'R2.2 How fast? The rate of chemical change'),
        ('extent_chemical_change', 'R2.3 How far? The extent of chemical change'),
        ('proton_transfer', 'R3.1 Proton transfer reactions'),
        ('electron_transfer', 'R3.2 Electron transfer reactions'),
        ('electron_sharing', 'R3.3 Electron sharing reactions'),
        ('electron_pair_sharing', 'R3.4 Electron-pair sharing reactions'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")

    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]
    correct_answer = models.CharField(
        max_length=10, choices=CORRECT_ANSWERS, null=True, blank=True,
        help_text="For Paper 1A multiple-choice questions only"
    )

    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered'),
        ('premium', 'Premium'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='premium', help_text="Access level for this video")

    def save(self, *args, **kwargs):
        # Set session to month + year
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        
        # Set abbreviation_month to first letter of month
        if self.month:
            self.abbreviation_month = self.month[0].upper()  # First letter, uppercase
        
        # Set abbreviation_year to last two digits of year
        if self.year:
            self.abbreviation_year = self.year[-2:]  # Last two digits
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Chemistry HL - Past Paper Video"
        verbose_name_plural = "Chemistry HL - Past Paper Videos"


class Generated_Number(models.Model):
    date = models.DateTimeField(default=datetime.now)
    number = models.CharField(max_length=255)



class QR_Code_Free_Call(models.Model):
    date = models.DateTimeField(default=datetime.now)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255) 
    phone = models.CharField(max_length=255)
    preferred_time = models.CharField(max_length=2000) 
    language = models.CharField(max_length=255) 
    topic = models.CharField(max_length=255) 
    year = models.CharField(max_length=255)
    date = models.DateTimeField()




class TutoringLead(models.Model):
    """Lead captured from the tutoring landing page survey."""
    created_at = models.DateTimeField(auto_now_add=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    ib_year = models.CharField(max_length=50, blank=True)
    subject = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"


class Fillout_Survey(models.Model):
    date = models.DateTimeField(default=datetime.now)
    first_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, default = "null")
    engineering_score = models.CharField(max_length=255, default = "null")
    law_score = models.CharField(max_length=255, default = "null")
    medicine_score = models.CharField(max_length=255, default = "null")
    economics_score = models.CharField(max_length=255, default = "null")
    architecture_score = models.CharField(max_length=255, default = "null")
    sciences_score = models.CharField(max_length=255, default = "null")
    humanities_score = models.CharField(max_length=255, default = "null")
    soc_sciences_score = models.CharField(max_length=255, default = "null")
    creative_score = models.CharField(max_length=255, default = "null")
    grades = models.CharField(max_length=255, default = "null")
    funding = models.CharField(max_length=255, default = "null")
    uni_cost = models.CharField(max_length=255, default = "null")
    uni_language = models.CharField(max_length=255, default = "null")
    uni_setting = models.CharField(max_length=255, default = "null")



class Math_AI_SL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    PAPERS = [
        ('paper1', 'Paper 1'),
        ('paper2', 'Paper 2'),
        ('paper3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS)
    video = models.TextField()
    sync_to_hl = models.BooleanField(default=True, help_text="Automatically sync this question to Math AI HL")
    hl_question_id = models.IntegerField(null=True, blank=True, help_text="ID of corresponding HL question")

    CHAPTERS = [
        ('', 'None'),  # Default empty option
        ('number_skills', 'Number Skills'),
        ('seq_series', 'Sequences & Series'),
        ('systems_lin_eq', 'Systems of Linear Equations'),
        ('lin_eq_graphs', 'Linear Equations & Graphs'),
        ('hypothesis_testing', 'Hypothesis Testing'),
        ('trigonometry', 'Trigonometry'),
        ('applications_of_functions', 'Applications of Functions'),
        ('voronoi_diagrams', 'Voronoi Diagrams'),
        ('probability', 'Probability'),
        ('properties_of_functions', 'Properties of Functions'),
        ('integration', 'Integration'),
        ('distributions', 'Distributions'),
        ('geometry_shapes', 'Geometry & Shapes'),
        ('descriptive_stats', 'Descriptive Statistics'),
        ('differentiation', 'Differentiation'),
        ('bivariate_statistics', 'Bivariate Statistics'),
    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS, default='', help_text="Primary chapter", db_index=True)
    chapter2 = models.CharField(max_length=200, choices=CHAPTERS, default='', blank=True, help_text="Secondary chapter (optional)", db_index=True)
    chapter3 = models.CharField(max_length=200, choices=CHAPTERS, default='', blank=True, help_text="Third chapter (optional)", db_index=True)
    marks = models.TextField(default = "null")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "free")
    def get_all_chapters(self):
        """Return list of all non-empty chapters"""
        chapters = []
        if self.chapter:
            chapters.append(self.chapter)
        if self.chapter2:
            chapters.append(self.chapter2)
        if self.chapter3:
            chapters.append(self.chapter3)
        return chapters
    
    def get_chapter_names(self):
        """Return human-readable names for all chapters"""
        chapter_dict = dict(self.CHAPTERS)
        return [chapter_dict.get(chapter, chapter) for chapter in self.get_all_chapters()]
    
    def has_chapter(self, chapter_key):
        """Check if question belongs to a specific chapter"""
        return chapter_key in [self.chapter, self.chapter2, self.chapter3]

    class Meta:
        verbose_name = "Math AI SL - Questionbank"
        verbose_name_plural = "Math AI SL - Questionbanks"


class Math_AI_HL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    PAPERS = [
        ('paper1', 'Paper 1'),
        ('paper2', 'Paper 2'),
        ('paper3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS)
    video = models.TextField()
   

    CHAPTERS = [
        ('', 'None'),  # Default empty option
        ('number_skills', 'Number Skills'),
        ('seq_series', 'Sequences & Series'),
        ('complex_numbers', 'Complex Numbers'),
        ('matrices', 'Matrices'),
        ('systems_lin_eq', 'Systems of Linear Equations'),
        ('lin_eq_graphs', 'Linear Equations & Graphs'),
        ('applications_of_functions', 'Applications of Functions'),
        ('properties_of_functions', 'Properties of Functions'),
        ('function_transformations', 'Function Transformations'),
        ('geometry_shapes', 'Geometry & Shapes'),
        ('trigonometry', 'Trigonometry'),
        ('trigonometric_functions', 'Trigonometric Functions'),
        ('geometric_transformations', 'Geometric Transformations'),
        ('voronoi_diagrams', 'Voronoi Diagrams'),
        ('graph_theory', 'Graph Theory'),
        ('vectors', 'Vectors'),
        ('descriptive_stats', 'Descriptive Statistics'),
        ('bivariate_statistics', 'Bivariate Statistics'),
        ('hypothesis_testing', 'Hypothesis Testing'),
        ('probability', 'Probability'),
        ('estimations_and_confidence_intervals', 'Estimation & Confidence Intervals'),
        ('distributions', 'Distributions'),
        ('integration', 'Integration'),
        ('differentiation', 'Differentiation'),
        ('kinematics', 'Kinematics'),
        ('differential_equations', 'Differential Equations'),

    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS, default='', help_text="Primary chapter")
    chapter2 = models.CharField(max_length=200, choices=CHAPTERS, default='', blank=True, help_text="Secondary chapter (optional)")
    chapter3 = models.CharField(max_length=200, choices=CHAPTERS, default='', blank=True, help_text="Third chapter (optional)")
    marks = models.TextField(default = "null")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")
    
    def get_all_chapters(self):
        """Return list of all non-empty chapters"""
        chapters = []
        if self.chapter:
            chapters.append(self.chapter)
        if self.chapter2:
            chapters.append(self.chapter2)
        if self.chapter3:
            chapters.append(self.chapter3)
        return chapters
    
    def get_chapter_names(self):
        """Return human-readable names for all chapters"""
        chapter_dict = dict(self.CHAPTERS)
        return [chapter_dict.get(chapter, chapter) for chapter in self.get_all_chapters()]
    
    def has_chapter(self, chapter_key):
        """Check if question belongs to a specific chapter"""
        return chapter_key in [self.chapter, self.chapter2, self.chapter3]

    class Meta:
        verbose_name = "Math AI HL - Questionbank"
        verbose_name_plural = "Math AI HL - Questionbanks"


class Math_AA_SL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    PAPERS = [
        ('paper1', 'Paper 1'),
        ('paper2', 'Paper 2'),
        ('paper3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS)
    video = models.TextField()
    sync_to_hl = models.BooleanField(default=True, help_text="Automatically sync this question to Math AA HL")
    hl_question_id = models.IntegerField(null=True, blank=True, help_text="ID of corresponding HL question")

    CHAPTERS = [
        ('', 'None'),  # Default empty option
        ('seq_series', 'Sequences & Series'),
        ('exp_and_logs', 'Exponentials and Logarithms'),
        ('binomial_expansion', 'Binomial Expansion'),
        ('proofs', 'Proofs'),
        ('properties_of_functions', 'Properties of Functions'),
        ('quadratic_functions', 'Quadratic Functions'),
        ('rational_functions', 'Rational Functions'),
        ('exp_and_logs_functions', 'Exponential and Logarithmic Functions'),
        ('function_transformations', 'Function Transformations'),
        ('geometry', 'Geometry'),
        ('trig_functions', 'Trigonometric Functions'),
        ('statistics', 'Statistics'),
        ('bivariate_stats', 'Bivariate Statistics'),
        ('probability', 'Probability'),
        ('distributions', 'Distributions'),
        ('integration', 'Integration'),
        ('differentiation', 'Differentiation'),
        ('kinematics', 'Kinematics')

    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS, default='', help_text="Primary chapter")
    chapter2 = models.CharField(max_length=200, choices=CHAPTERS, default='', blank=True, help_text="Secondary chapter (optional)")
    chapter3 = models.CharField(max_length=200, choices=CHAPTERS, default='', blank=True, help_text="Third chapter (optional)")
    marks = models.TextField(default = "null")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")
    
    def get_all_chapters(self):
        """Return list of all non-empty chapters"""
        chapters = []
        if self.chapter:
            chapters.append(self.chapter)
        if self.chapter2:
            chapters.append(self.chapter2)
        if self.chapter3:
            chapters.append(self.chapter3)
        return chapters
    
    def get_chapter_names(self):
        """Return human-readable names for all chapters"""
        chapter_dict = dict(self.CHAPTERS)
        return [chapter_dict.get(chapter, chapter) for chapter in self.get_all_chapters()]
    
    def has_chapter(self, chapter_key):
        """Check if question belongs to a specific chapter"""
        return chapter_key in [self.chapter, self.chapter2, self.chapter3]

    class Meta:
        verbose_name = "Math AA SL - Questionbank"
        verbose_name_plural = "Math AA SL - Questionbanks"



class Math_AA_HL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    PAPERS = [
        ('paper1', 'Paper 1'),
        ('paper2', 'Paper 2'),
        ('paper3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS)
    video = models.TextField()
   

    CHAPTERS = [
        ('', 'None'),  # Default empty option
        ('seq_series', 'Sequences & Series'),
        ('exp_and_logs', 'Exponentials and Logarithms'),
        ('binomial_expansion', 'Binomial Expansion'),
        ('proofs', 'Proofs'),
        ('counting_principles', 'Counting Principles'),
        ('complex_numbers', 'Complex Numbers'),
        ('systems_of_equations', 'Systems of Equations'),
        ('properties_of_functions', 'Properties of Functions'),
        ('quadratic_functions', 'Quadratic Functions'),
        ('rational_functions', 'Rational Functions'),
        ('exp_and_logs_functions', 'Exponential and Logarithmic Functions'),
        ('function_transformations', 'Function Transformations'),
        ('polynomials', 'Polynomials'),
        ('mod_inequalities', 'Mod & Inequalities'),
        ('geometry', 'Geometry'),
        ('trig_functions', 'Trigonometric Functions'),
        ('vectors', 'Vectors'),
        ('statistics', 'Statistics'),
        ('bivariate_stats', 'Bivariate Statistics'),
        ('probability', 'Probability'),
        ('distributions', 'Distributions'),
        ('integration', 'Integration'),
        ('differentiation', 'Differentiation'),
        ('kinematics', 'Kinematics'),
        ('maclaurin_series', 'MacLaurin Series'),
        ('differential_equations', 'Differential Equations'),

    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS, default='', help_text="Primary chapter")
    chapter2 = models.CharField(max_length=200, choices=CHAPTERS, default='', blank=True, help_text="Secondary chapter (optional)")
    chapter3 = models.CharField(max_length=200, choices=CHAPTERS, default='', blank=True, help_text="Third chapter (optional)")
    marks = models.TextField(default = "null")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")
    
    def get_all_chapters(self):
        """Return list of all non-empty chapters"""
        chapters = []
        if self.chapter:
            chapters.append(self.chapter)
        if self.chapter2:
            chapters.append(self.chapter2)
        if self.chapter3:
            chapters.append(self.chapter3)
        return chapters
    
    def get_chapter_names(self):
        """Return human-readable names for all chapters"""
        chapter_dict = dict(self.CHAPTERS)
        return [chapter_dict.get(chapter, chapter) for chapter in self.get_all_chapters()]
    
    def has_chapter(self, chapter_key):
        """Check if question belongs to a specific chapter"""
        return chapter_key in [self.chapter, self.chapter2, self.chapter3]

    class Meta:
        verbose_name = "Math AA HL - Questionbank"
        verbose_name_plural = "Math AA HL - Questionbanks"


class Math_AA_HL_Questionbank_Backup(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    PAPERS = [
        ('paper1', 'Paper 1'),
        ('paper2', 'Paper 2'),
        ('paper3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS)
    video = models.TextField()
   

    CHAPTERS = [
  
        ('seq_series', 'Sequences & Series'),
        ('exp_and_logs', 'Exponentials and Logarithms'),
        ('binomial_expansion', 'Binomial Expansion'),
        ('proofs', 'Proofs'),
        ('counting_principles', 'Counting Principles'),
        ('complex_numbers', 'Complex Numbers'),
        ('systems_of_equations', 'Systems of Equations'),
        ('properties_of_functions', 'Properties of Functions'),
        ('quadratic_functions', 'Quadratic Functions'),
        ('rational_functions', 'Rational Functions'),
        ('exp_and_logs_functions', 'Exponential and Logarithmic Functions'),
        ('function_transformations', 'Function Transformations'),
        ('polynomials', 'Polynomials'),
        ('mod_inequalities', 'Mod & Inequalities'),
        ('geometry', 'Geometry'),
        ('trig_functions', 'Trigonometric Functions'),
        ('vectors', 'Vectors'),
        ('statistics', 'Statistics'),
        ('bivariate_stats', 'Bivariate Statistics'),
        ('probability', 'Probability'),
        ('distributions', 'Distributions'),
        ('integral_calculus', 'Integral Calculus'),
        ('differential_calculus', 'Differential Calculus'),
        ('kinematics', 'Kinematics'),
        ('maclaurin_series', 'MacLaurin Series'),
        ('differential_equations', 'Differential Equations'),

    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    marks = models.TextField(default = "null")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")






class Biology_SL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default = "Easy")
    PAPERS = [
        ('paper1A', 'Paper 1A'),
        ('paper1B', 'Paper 1B'),
        ('paper2', 'Paper 2'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default = "paper1A")
    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D')
    ]
    correct_answer = models.CharField(max_length=10, choices=CORRECT_ANSWERS, default = "A")
    video = models.TextField(default = "none")
    sync_to_hl = models.BooleanField(default=True, help_text="Automatically sync this question to Biology HL")
    hl_question_id = models.IntegerField(null=True, blank=True, help_text="ID of corresponding HL question")
    CHAPTERS = [
        ('water', 'Water'),
        ('nucleic_acids', 'Nucleic Acids'),
        ('cell_structure', 'Cell Structure'),
        ('diversity_of_organisms', 'Diversity of Organisms'),
        ('evolution_and_speciation', 'Evolution and Speciation'),
        ('conservation_of_biodiversity', 'Conservation of Biodiversity'),
        ('carbohydrates_and_lipids', 'Carbohydrates & Lipids'),
        ('proteins', 'Proteins'),
        ('membranes_and_membrane_transport', 'Membranes and Membrane Transport'),
        ('organelles_and_compartmentalization', 'Organelles and Compartmentalization'),
        ('cell_specialization', 'Cell Specialization'),
        ('gas_exchange', 'Gas Exchange'),
        ('transport', 'Transport'),
        ('adaptation_to_environment', 'Adaptation to Environment'),
        ('ecological_niches', 'Ecological Niches'),
        ('enzymes_metabolism', 'Enzymes and Metabolism'),
        ('cell_respiration', 'Cell Respiration'),
        ('photosynthesis', 'Photosynthesis'),
        ('neural_signaling', 'Neural Signaling'),
        ('integration_of_body_systems', 'Integration of Body Systems'),
        ('defence_against_disease', 'Defence Against Disease'),
        ('population_and_communities', 'Population and Communities'),
        ('transfer_of_energy', 'Transfer of Energy and Matter'),
        ('dna_replication', 'DNA Replication'),
        ('protein_synthesis', 'Protein Synthesis'),
        ('mutations_editing', 'Mutations and Gene Editing'),
        ('natural_selection', 'Natural Selection'),
        ('inheritance', 'Inheritance'),
        ('climate_change', 'Climate Change'),
        ('water_potential', 'Water Potential'),
        ('cell_division', 'Cell Division'),
        ('reproduction', 'Reproduction'),
        ('stability_change', 'Stability & Change'),
        ('homeostasis', 'Homeostasis'),

    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    marks = models.TextField(default = "1")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")


    VERIFIED_CHOICES = [
        ('yes', 'yes'),
        ('no', 'no'),
    ]
    verified = models.CharField(max_length=10, choices=VERIFIED_CHOICES, default = "yes")

    class Meta:
        verbose_name = "Biology SL - Questionbank"
        verbose_name_plural = "Biology SL - Questionbanks"


class Biology_HL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default = "Easy")
    PAPERS = [
        ('paper1A', 'Paper 1A'),
        ('paper1B', 'Paper 1B'),
        ('paper2', 'Paper 2'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default = "paper1A")
    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D')
    ]
    correct_answer = models.CharField(max_length=10, choices=CORRECT_ANSWERS, default = "A")
    video = models.TextField(default = "none")
    CHAPTERS = [
        ('water', 'Water'),
        ('nucleic_acids', 'Nucleic Acids'),
        ('origin_of_cells', 'Origin of Cells'),
        ('viruses', 'Viruses'),
        ('classification', 'Classification'),
        ('muscle_and_motility', 'Muscle and Motility'),
        ('chemical_signaling', 'Chemical Signaling'),
        ('cell_structure', 'Cell Structure'),
        ('diversity_of_organisms', 'Diversity of Organisms'),
        ('evolution_and_speciation', 'Evolution and Speciation'),
        ('conservation_of_biodiversity', 'Conservation of Biodiversity'),
        ('carbohydrates_and_lipids', 'Carbohydrates & Lipids'),
        ('proteins', 'Proteins'),
        ('membranes_and_membrane_transport', 'Membranes and Membrane Transport'),
        ('organelles_and_compartmentalization', 'Organelles and Compartmentalization'),
        ('cell_specialization', 'Cell Specialization'),
        ('gas_exchange', 'Gas Exchange'),
        ('transport', 'Transport'),
        ('adaptation_to_environment', 'Adaptation to Environment'),
        ('ecological_niches', 'Ecological Niches'),
        ('enzymes_metabolism', 'Enzymes and Metabolism'),
        ('cell_respiration', 'Cell Respiration'),
        ('photosynthesis', 'Photosynthesis'),
        ('neural_signaling', 'Neural Signaling'),
        ('integration_of_body_systems', 'Integration of Body Systems'),
        ('defence_against_disease', 'Defence Against Disease'),
        ('population_and_communities', 'Population and Communities'),
        ('transfer_of_energy', 'Transfer of Energy and Matter'),
        ('dna_replication', 'DNA Replication'),
        ('protein_synthesis', 'Protein Synthesis'),
        ('mutations_editing', 'Mutations and Gene Editing'),
        ('natural_selection', 'Natural Selection'),
        ('inheritance', 'Inheritance'),
        ('climate_change', 'Climate Change'),
        ('water_potential', 'Water Potential'),
        ('cell_division', 'Cell Division'),
        ('reproduction', 'Reproduction'),
        ('stability_change', 'Stability & Change'),
        ('homeostasis', 'Homeostasis'),
        ('gene_expression', 'Gene Expression'),

    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    marks = models.TextField(default = "1")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")

    VERIFIED_CHOICES = [
        ('yes', 'yes'),
        ('no', 'no'),
    ]
    verified = models.CharField(max_length=10, choices=VERIFIED_CHOICES, default = "yes")

    class Meta:
        verbose_name = "Biology HL - Questionbank"
        verbose_name_plural = "Biology HL - Questionbanks"


class History_SL_Questionbank(models.Model):
    PAPERS = [
        ('paper1', 'Paper 1'),
        ('paper2', 'Paper 2'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default='paper2')
    
    CHAPTERS = [
        ('emergence_democratic_states', 'Emergence and Development of Democratic States'),
        ('authoritarian_states', 'Authoritarian States'),
        ('causes_effects_wars', 'Causes and Effects of 20th Century Wars'),
        ('cold_war', 'The Cold War: Superpower Tensions and Rivalries'),
        ('rights_protest', 'Rights and Protest'),
        ('conflict_intervention', 'Conflict and Intervention'),
        ('move_global_war', 'The Move to Global War'),
        ('independence_movements', 'Independence Movements'),
    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    
    title = models.TextField(help_text="The essay question/prompt")
    
    COMMAND_TERMS = [
        ('evaluate', 'Evaluate'),
        ('discuss', 'Discuss'),
        ('analyze', 'Analyze'),
        ('compare', 'Compare'),
        ('compare_contrast', 'Compare and Contrast'),
        ('examine', 'Examine'),
        ('to_what_extent', 'To What Extent'),
        ('assess', 'Assess'),
        ('explain', 'Explain'),
    ]
    command_term = models.CharField(max_length=50, choices=COMMAND_TERMS, default='evaluate')
    explanation = models.TextField(help_text="Command term explanation")
    
    intro = models.TextField(help_text="Introduction paragraph")
    body = models.TextField(help_text="Body paragraphs (can include multiple paragraphs with headings)")
    conclusion = models.TextField(help_text="Conclusion paragraph", blank=True, null=True)
    
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    
    marks = models.CharField(max_length=10, default='15')
    
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='premium')
    
    VERIFIED_CHOICES = [
        ('yes', 'yes'),
        ('no', 'no'),
    ]
    verified = models.CharField(max_length=10, choices=VERIFIED_CHOICES, default='yes')

    sync_to_hl = models.BooleanField(default=True, help_text="Automatically sync this question to History HL")
    hl_question_id = models.IntegerField(null=True, blank=True, help_text="ID of corresponding HL question")
    
    class Meta:
        verbose_name = "History SL - Questionbank"
        verbose_name_plural = "History SL - Questionbanks"


class History_HL_Questionbank(models.Model):
    PAPERS = [
        ('paper1', 'Paper 1'),
        ('paper2', 'Paper 2'),
        ('paper3', 'Paper 3'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default='paper2')
    
    CHAPTERS = [
        ('emergence_democratic_states', 'Emergence and Development of Democratic States'),
        ('authoritarian_states', 'Authoritarian States'),
        ('causes_effects_wars', 'Causes and Effects of 20th Century Wars'),
        ('cold_war', 'The Cold War: Superpower Tensions and Rivalries'),
        ('rights_protest', 'Rights and Protest'),
        ('conflict_intervention', 'Conflict and Intervention'),
        ('move_global_war', 'The Move to Global War'),
        ('independence_movements', 'Independence Movements'),
        ('history_europe', 'History of Europe'),
        ('history_americas', 'History of the Americas'),
        ('history_asia_oceania', 'History of Asia and Oceania'),
        ('history_africa_middle_east', 'History of Africa and the Middle East'),
    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    
    title = models.TextField(help_text="The essay question/prompt")
    
    COMMAND_TERMS = [
        ('evaluate', 'Evaluate'),
        ('discuss', 'Discuss'),
        ('analyze', 'Analyze'),
        ('compare', 'Compare'),
        ('compare_contrast', 'Compare and Contrast'),
        ('examine', 'Examine'),
        ('to_what_extent', 'To What Extent'),
        ('assess', 'Assess'),
        ('explain', 'Explain'),
    ]
    command_term = models.CharField(max_length=50, choices=COMMAND_TERMS, default='evaluate')
    explanation = models.TextField(help_text="Command term explanation")
    
    intro = models.TextField(help_text="Introduction paragraph")
    body = models.TextField(help_text="Body paragraphs (can include multiple paragraphs with headings)")
    conclusion = models.TextField(help_text="Conclusion paragraph", blank=True, null=True)
    
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    
    marks = models.CharField(max_length=10, default='15')
    
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='premium')
    
    VERIFIED_CHOICES = [
        ('yes', 'yes'),
        ('no', 'no'),
    ]
    verified = models.CharField(max_length=10, choices=VERIFIED_CHOICES, default='yes')
    
    class Meta:
        verbose_name = "History HL - Questionbank"
        verbose_name_plural = "History HL - Questionbanks"


class Webinars_Live(models.Model):
    date_created = models.DateTimeField(default=datetime.now)
    first_name = models.CharField(max_length=255, default = "John")
    last_name = models.CharField(max_length=255, default = "Smith")
    title = models.CharField(max_length=2000, default = "Studying in the UK")
    description = models.CharField(max_length=2000, default = "In this webinar we will described what it is like to study in the UK.")
    webinar_date = models.DateTimeField()
    IMAGE_CHOICES = [
    ('fiorella2.jpg', 'Fiorella'),
    ('mateusz.jpg', 'Mateusz'),
    ('mike2.jpg', 'Michal'),
    ('anubha.png', 'Anubha'),
]
    image_mentor = models.CharField(max_length=100, choices=IMAGE_CHOICES, default = "mateusz2.png")
    image_main = models.CharField(max_length=1000, default = "https://ik.imagekit.io/zwtwkrbaj/Webinars%20Live/Thumbnail-2.png?updatedAt=1750690040092")
    link = models.CharField(max_length=2000, default = "meet.google.com/cpp-whaa-xgi")

    class Meta:
        verbose_name = "Webinar Live"
        verbose_name_plural = "Webinars Live"



class Physics_SL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default = "Easy")
    PAPERS = [
        ('paper1A', 'Paper 1A'),
        ('paper1B', 'Paper 1B'),
        ('paper2', 'Paper 2'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default = "paper1A")
    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D')
    ]
    correct_answer = models.CharField(max_length=10, choices=CORRECT_ANSWERS, default = "A")
    video = models.TextField(default = "none")
    sync_to_hl = models.BooleanField(default=True, help_text="Automatically sync this question to Physics HL")
    hl_question_id = models.IntegerField(null=True, blank=True, help_text="ID of corresponding HL question")
    CHAPTERS = [
        ('kinematics', 'Kinematics'),
        ('forces_and_momentum', 'Forces and Momentum'),
        ('work_energy_power', 'Work, Energy, and Power'),
        ('thermal_energy', 'Thermal Energy'),
        ('greenhouse_effect', 'Greenhouse Effect'),
        ('ideal_gas_model', 'Ideal Gas Model'),
        ('electric_circuits', 'Electric Circuits'),
        ('simple_harmonic_motion', 'Simple Harmonic Motion'),
        ('wave_model', 'Wave Model'),
        ('wave_phenomena', 'Wave Phenomena'),
        ('standing_waves', 'Standing Wave and Resonance'),
        ('doppler_effect', 'Doppler Effect'),
        ('gravitational_fields', 'Gravitational Fields'),
        ('electric_magnetic_fields', 'Electric and Magnetic Fields'),
        ('motion_in_fields', 'Motion in Electromagnetic Fields'),
        ('structure_atom', 'Structure of the Atom'),
        ('radioactive_decay', 'Radioactive Decay'),
        ('fission', 'Fission'),
        ('fusion_and_stars', 'Fusion and Stars')

    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    marks = models.TextField(default = "1")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")

    def __str__(self):
        # Strip HTML tags and limit length for cleaner admin display
        import re
        clean_text = re.sub('<[^<]+?>', '', self.question)
        return clean_text[:100] + '...' if len(clean_text) > 100 else clean_text

    class Meta:
        verbose_name = "Physics SL - Questionbank"
        verbose_name_plural = "Physics SL - Questionbanks"



class Physics_HL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default = "Easy")
    PAPERS = [
        ('paper1A', 'Paper 1A'),
        ('paper1B', 'Paper 1B'),
        ('paper2', 'Paper 2'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default = "paper1A")
    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D')
    ]
    correct_answer = models.CharField(max_length=10, choices=CORRECT_ANSWERS, default = "A")
    video = models.TextField(default = "none")
    CHAPTERS = [
        ('kinematics', 'Kinematics'),
        ('forces_and_momentum', 'Forces and Momentum'),
        ('work_energy_power', 'Work, Energy, and Power'),
        ('rigid_body_mechanics', 'Rigid Body Mechanics'),
        ('galilean_and_special_relativity', 'Galilean and Special Relativity'),
        ('thermal_energy', 'Thermal Energy'),
        ('greenhouse_effect', 'Greenhouse Effect'),
        ('ideal_gas_model', 'Ideal Gas Model'),
        ('thermodynamics', 'Thermodynamics'),
        ('electric_circuits', 'Electric Circuits'),
        ('simple_harmonic_motion', 'Simple Harmonic Motion'),
        ('wave_model', 'Wave Model'),
        ('wave_phenomena', 'Wave Phenomena'),
        ('standing_waves', 'Standing Wave and Resonance'),
        ('doppler_effect', 'Doppler Effect'),
        ('gravitational_fields', 'Gravitational Fields'),
        ('electric_magnetic_fields', 'Electric and Magnetic Fields'),
        ('motion_in_fields', 'Motion in Electromagnetic Fields'),
        ('induction', 'Induction'),
        ('structure_atom', 'Structure of the Atom'),
        ('quantum_physics', 'Quantum Physics'),
        ('radioactive_decay', 'Radioactive Decay'),
        ('fission', 'Fission'),
        ('fusion_and_stars', 'Fusion and Stars')

    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    marks = models.TextField(default = "1")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")

    def __str__(self):
        # Strip HTML tags and limit length for cleaner admin display
        import re
        clean_text = re.sub('<[^<]+?>', '', self.question)
        return clean_text[:100] + '...' if len(clean_text) > 100 else clean_text

    class Meta:
        verbose_name = "Physics HL - Questionbank"
        verbose_name_plural = "Physics HL - Questionbanks"


class Chemistry_SL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default = "Easy")
    PAPERS = [
        ('paper1A', 'Paper 1A'),
        ('paper1B', 'Paper 1B'),
        ('paper2', 'Paper 2'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default = "paper1")
    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D')
    ]
    correct_answer = models.CharField(max_length=10, choices=CORRECT_ANSWERS, default = "A")
    video = models.TextField(default = "none")
    sync_to_hl = models.BooleanField(default=True, help_text="Automatically sync this question to Chemistry HL")
    hl_question_id = models.IntegerField(null=True, blank=True, help_text="ID of corresponding HL question")
    CHAPTERS = [
        ('introduction_particulate_nature', 'S1.1 Introduction to the particulate nature of matter'),
        ('nuclear_atom', 'S1.2 The nuclear atom'),
        ('electron_configurations', 'S1.3 Electron configurations'),
        ('counting_particles_mole', 'S1.4 Counting particles by mass: The mole'),
        ('ideal_gases', 'S1.5 Ideal gases'),
        ('ionic_model', 'S2.1 The ionic model'),
        ('covalent_model', 'S2.2 The covalent model'),
        ('metallic_model', 'S2.3 The metallic model'),
        ('models_to_materials', 'S2.4 From models to materials'),
        ('periodic_table', 'S3.1 The periodic table: Classification of elements'),
        ('functional_groups', 'S3.2 Functional groups: Classification of organic compounds'),
        ('measuring_enthalpy', 'R1.1 Measuring enthalpy changes'),
        ('energy_cycles', 'R1.2 Energy cycles in reactions'),
        ('energy_from_fuels', 'R1.3 Energy from fuels'),
        ('amount_chemical_change', 'R2.1 How much? The amount of chemical change'),
        ('rate_chemical_change', 'R2.2 How fast? The rate of chemical change'),
        ('extent_chemical_change', 'R2.3 How far? The extent of chemical change'),
        ('proton_transfer', 'R3.1 Proton transfer reactions'),
        ('electron_transfer', 'R3.2 Electron transfer reactions'),
        ('electron_sharing', 'R3.3 Electron sharing reactions'),
        ('electron_pair_sharing', 'R3.4 Electron-pair sharing reactions'),
    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    marks = models.TextField(default = "1")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")

    def __str__(self):
        # Strip HTML tags and limit length for cleaner admin display
        import re
        clean_text = re.sub('<[^<]+?>', '', self.question)
        return clean_text[:100] + '...' if len(clean_text) > 100 else clean_text

    class Meta:
        verbose_name = "Chemistry SL - Questionbank"
        verbose_name_plural = "Chemistry SL - Questionbanks"


class Chemistry_HL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default = "Easy")
    PAPERS = [
        ('paper1A', 'Paper 1A'),
        ('paper1B', 'Paper 1B'),
        ('paper2', 'Paper 2'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default = "paper1")
    CORRECT_ANSWERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D')
    ]
    correct_answer = models.CharField(max_length=10, choices=CORRECT_ANSWERS, default = "A")
    video = models.TextField(default = "none")
    CHAPTERS = [
        ('introduction_particulate_nature', 'S1.1 Introduction to the particulate nature of matter'),
        ('nuclear_atom', 'S1.2 The nuclear atom'),
        ('electron_configurations', 'S1.3 Electron configurations'),
        ('counting_particles_mole', 'S1.4 Counting particles by mass: The mole'),
        ('ideal_gases', 'S1.5 Ideal gases'),
        ('ionic_model', 'S2.1 The ionic model'),
        ('covalent_model', 'S2.2 The covalent model'),
        ('metallic_model', 'S2.3 The metallic model'),
        ('models_to_materials', 'S2.4 From models to materials'),
        ('periodic_table', 'S3.1 The periodic table: Classification of elements'),
        ('functional_groups', 'S3.2 Functional groups: Classification of organic compounds'),
        ('measuring_enthalpy', 'R1.1 Measuring enthalpy changes'),
        ('energy_cycles', 'R1.2 Energy cycles in reactions'),
        ('energy_from_fuels', 'R1.3 Energy from fuels'),
        ('entropy_spontaneity', 'R1.4 Entropy and spontaneity'),
        ('amount_chemical_change', 'R2.1 How much? The amount of chemical change'),
        ('rate_chemical_change', 'R2.2 How fast? The rate of chemical change'),
        ('extent_chemical_change', 'R2.3 How far? The extent of chemical change'),
        ('proton_transfer', 'R3.1 Proton transfer reactions'),
        ('electron_transfer', 'R3.2 Electron transfer reactions'),
        ('electron_sharing', 'R3.3 Electron sharing reactions'),
        ('electron_pair_sharing', 'R3.4 Electron-pair sharing reactions'),
    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    marks = models.TextField(default = "1")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")

    def __str__(self):
        # Strip HTML tags and limit length for cleaner admin display
        import re
        clean_text = re.sub('<[^<]+?>', '', self.question)
        return clean_text[:100] + '...' if len(clean_text) > 100 else clean_text

    class Meta:
        verbose_name = "Chemistry HL - Questionbank"
        verbose_name_plural = "Chemistry HL - Questionbanks"


class Comp_Sci_SL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default = "Easy")
    PAPERS = [

        ('paper1', 'Paper 1'),
        ('paper2', 'Paper 2'),
        ('practice', 'Practice'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default = "paper1")
    # CORRECT_ANSWERS = [
    #     ('A', 'A'),
    #     ('B', 'B'),
    #     ('C', 'C'),
    #     ('D', 'D')
    # ]
    # correct_answer = models.CharField(max_length=10, choices=CORRECT_ANSWERS, default = "A")
    video = models.TextField(default = "none")
    sync_to_hl = models.BooleanField(default=False, help_text="Automatically sync this question to Computer Science HL")
    hl_question_id = models.IntegerField(null=True, blank=True, help_text="ID of corresponding HL question")
    CHAPTERS = [
        ('system_fundamentals', 'System Fundamentals'),
        ('computer_organisation', 'Computer Organisation'),
        ('networks', 'Networks'),
        ('computational_thinking', 'Computational Thinking'),
        ('variables_input', 'Variables and Input'),
        ('if_statements', 'If Statements'),
        ('loops', 'Loops'),
        ('arrays', 'Arrays'),
        ('methods', 'Methods'),
        ('constructors', 'Constructors'),
        ('oop', 'OOP'),
    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    marks = models.TextField(default = "1")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")

    def __str__(self):
        # Strip HTML tags and limit length for cleaner admin display
        import re
        clean_text = re.sub('<[^<]+?>', '', self.question)
        return clean_text[:100] + '...' if len(clean_text) > 100 else clean_text

    class Meta:
        verbose_name = "Comp Sci SL - Questionbank"
        verbose_name_plural = "Comp Sci SL - Questionbanks"



class Past_Paper_Videos_Comp_Sci_SL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default = "May")
    year = models.CharField(max_length=10, default = "2024")
    session = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default = "1")

    PAPERS = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default = "1")
    question = models.CharField(max_length=100, default = "1")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('system_fundamentals', 'System Fundamentals'),
        ('computer_organisation', 'Computer Organisation'),
        ('networks', 'Networks'),
        ('computational_thinking', 'Computational Thinking'),
        ('variables_input', 'Variables and Input'),
        ('if_statements', 'If Statements'),
        ('loops', 'Loops'),
        ('arrays', 'Arrays'),
        ('methods', 'Methods'),
        ('constructors', 'Constructors'),
        ('oop', 'OOP'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    text_answer = models.TextField(default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")

    def save(self, *args, **kwargs):
        # Set session to month + year
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        
        # Set abbreviation_month to first letter of month
        if self.month:
            self.abbreviation_month = self.month[0].upper()  # First letter, uppercase
        
        # Set abbreviation_year to last two digits of year
        if self.year:
            self.abbreviation_year = self.year[-2:]  # Last two digits
            
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "Comp Sci SL - Past Paper Video"
        verbose_name_plural = "Comp Sci SL - Past Paper Videos"


class Comp_Sci_HL_Questionbank(models.Model):
    question = models.TextField()
    answer = models.TextField()
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default = "Easy")
    PAPERS = [

        ('paper1', 'Paper 1'),
        ('paper2', 'Paper 2'),
        ('practice', 'Practice'),
    ]
    paper = models.CharField(max_length=20, choices=PAPERS, default = "paper1")
    # CORRECT_ANSWERS = [
    #     ('A', 'A'),
    #     ('B', 'B'),
    #     ('C', 'C'),
    #     ('D', 'D')
    # ]
    # correct_answer = models.CharField(max_length=10, choices=CORRECT_ANSWERS, default = "A")
    video = models.TextField(default = "none")
    CHAPTERS = [
        ('system_fundamentals', 'System Fundamentals'),
        ('computer_organisation', 'Computer Organisation'),
        ('networks', 'Networks'),
        ('computational_thinking', 'Computational Thinking'),
        ('resource_management', 'Resource Management'),
        ('abstract_data_structures', 'Abstract Data Structures'),
        ('variables_input', 'Variables and Input'),
        ('if_statements', 'If Statements'),
        ('loops', 'Loops'),
        ('arrays', 'Arrays'),
        ('methods', 'Methods'),
        ('constructors', 'Constructors'),
        ('oop', 'OOP'),
    ]
    chapter = models.CharField(max_length=200, choices=CHAPTERS)
    marks = models.TextField(default = "1")
    TYPE_CHOICES = [
        ('free', 'free'),
        ('registered', 'registered'),
        ('premium', 'premium'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default = "registered")

    def __str__(self):
        # Strip HTML tags and limit length for cleaner admin display
        import re
        clean_text = re.sub('<[^<]+?>', '', self.question)
        return clean_text[:100] + '...' if len(clean_text) > 100 else clean_text

    class Meta:
        verbose_name = "Comp Sci HL - Questionbank"
        verbose_name_plural = "Comp Sci HL - Questionbanks"



class Past_Paper_Videos_Comp_Sci_HL(models.Model):
    MONTHS = [
        ('May', 'May'),
        ('November', 'November'),
    ]
    month = models.CharField(max_length=10, choices=MONTHS, default = "May")
    year = models.CharField(max_length=10, default = "2024")
    session = models.CharField(max_length=100, default = "null")

    ZONES = [
        ('0', '0'),
        ('1', '1'),
        ('2', '2'),
    ]
    time_zone = models.CharField(max_length=10, choices=ZONES, default = "1")

    PAPERS = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ]
    paper = models.CharField(max_length=10, choices=PAPERS, default = "1")
    question = models.CharField(max_length=100, default = "1")
    abbreviation_month = models.CharField(max_length=100, default = "null")
    abbreviation_year = models.CharField(max_length=100, default = "null")

    CHAPTERS = [
        ('null', 'null'),
        ('system_fundamentals', 'System Fundamentals'),
        ('computer_organisation', 'Computer Organisation'),
        ('networks', 'Networks'),
        ('computational_thinking', 'Computational Thinking'),
        ('resource_management', 'Resource Management'),
        ('abstract_data_structures', 'Abstract Data Structures'),
        ('variables_input', 'Variables and Input'),
        ('if_statements', 'If Statements'),
        ('loops', 'Loops'),
        ('arrays', 'Arrays'),
        ('methods', 'Methods'),
        ('constructors', 'Constructors'),
        ('oop', 'OOP'),
    ]
    topic1 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic2 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    topic3 = models.CharField(max_length=100, choices=CHAPTERS, default = "null")
    link = models.CharField(max_length=200, default = "null")
    text_answer = models.TextField(default = "null")
    question_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for question screenshots (comma-separated if multiple)")
    markscheme_screenshots_url = models.TextField(null=True, blank=True, help_text="ImageKit URL for markscheme screenshots (comma-separated if multiple)")

    def save(self, *args, **kwargs):
        # Set session to month + year
        if self.month and self.year:
            self.session = f"{self.month} {self.year}"
        
        # Set abbreviation_month to first letter of month
        if self.month:
            self.abbreviation_month = self.month[0].upper()  # First letter, uppercase
        
        # Set abbreviation_year to last two digits of year
        if self.year:
            self.abbreviation_year = self.year[-2:]  # Last two digits
            
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "Comp Sci HL - Past Paper Video"
        verbose_name_plural = "Comp Sci HL - Past Paper Videos"



class NewsAnnouncement(models.Model):
    """Model for news/announcements displayed on home page"""
    COLOR_CHOICES = [
        ('purple', '🟣 Purple'),
        ('pink', '🩷 Pink'),
        ('blue', '🔵 Blue'),
        ('green', '🟢 Green'),
        ('orange', '🟠 Orange'),
        ('red', '🔴 Red'),
        ('teal', '🩵 Teal'),
        ('yellow', '🟡 Yellow'),
    ]
    
    emoji = models.CharField(max_length=10, help_text="Enter an emoji (e.g., 🎉, 📢, 🚀)")
    label = models.CharField(max_length=50, default="News", help_text="Text shown below the circle (e.g., 'New Feature')")
    popup_title = models.CharField(max_length=100, default="Announcement", help_text="Title shown in the popup")
    popup_content = models.TextField(default="", help_text="Full announcement content - you can use HTML for buttons, links, formatting, etc.")
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='purple', help_text="Border color of the circle")
    is_active = models.BooleanField(default=True, help_text="Show this announcement on home page")
    created_date = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    
    class Meta:
        ordering = ['order', '-created_date']
        verbose_name = "News Announcement"
        verbose_name_plural = "News Announcements"
    
    def __str__(self):
        return f"{self.emoji} {self.label}"
    
    def get_gradient(self):
        """Return CSS color based on color choice - pastel colors"""
        colors = {
            'purple': '#b8a9d4',   # Soft lavender purple
            'pink': '#f7c3d7',     # Soft pink
            'blue': '#a8d8ea',     # Soft sky blue
            'green': '#b4e7b4',    # Soft mint green
            'orange': '#ffd4a3',   # Soft peach orange
            'red': '#ffb3b3',      # Soft coral red
            'teal': '#a3d9d9',     # Soft teal
            'yellow': '#fff4b3',   # Soft butter yellow
        }
        return colors.get(self.color, colors['purple'])


class TutorSession(models.Model):
    """Model to store tutor-student sessions"""
    tutor = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='tutor_sessions')
    student = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='student_sessions')
    
    # Link to StudentManagement for managed students (optional)
    managed_student = models.ForeignKey('StudentManagement', on_delete=models.CASCADE, related_name='sessions', null=True, blank=True, help_text="Link to managed student record if applicable")
    
    # Store tutor and student information directly in the session record
    tutor_first_name = models.CharField(max_length=100, blank=True)
    tutor_last_name = models.CharField(max_length=100, blank=True)
    student_first_name = models.CharField(max_length=100, blank=True)
    student_last_name = models.CharField(max_length=100, blank=True)
    student_email = models.EmailField(blank=True, null=True, help_text="Student's email for easy lookup")


    SUBJECTS = [
        ('physics_sl', 'Physics SL'),
        ('physics_hl', 'Physics HL'),
        ('biology_sl', 'Biology SL'),
        ('biology_hl', 'Biology HL'),
        ('chemistry_sl', 'Chemistry SL'),
        ('chemistry_hl', 'Chemistry HL'),
        ('math_ai_sl', 'Math AI SL'),
        ('math_ai_hl', 'Math AI HL'),
        ('math_aa_sl', 'Math AA SL'),
        ('math_aa_hl', 'Math AA HL'),
        ('comp_sci_sl', 'Comp Sci SL'),
        ('comp_sci_hl', 'Comp Sci HL'),
        ('geography_sl', 'Geography SL'),
        ('geography_hl', 'Geography HL'),
        ('economics_sl', 'Economics SL'),
        ('economics_hl', 'Economics HL'),
        ('history_sl', 'History SL'),
        ('history_hl', 'History HL'),
        ('business_sl', 'Business SL'),
        ('business_hl', 'Business HL'),
    ]
    subject = models.CharField(max_length=200, choices=SUBJECTS, default='physics_sl')
    
    session_time = models.DateTimeField()
    topic = models.CharField(max_length=500)
    notes = models.TextField(blank=True, null=True)  # Optional notes field for preparation
    
    # New fields for completed sessions
    hours_taught = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, help_text="Number of hours taught")
    homework_comments = models.TextField(blank=True, null=True, help_text="Homework assignments and comments")
    
    # Session materials
    session_pdf = models.FileField(
        upload_to='session_pdfs/%Y/%m/%d/', 
        blank=True, 
        null=True,
        help_text="Upload session materials (PDF format recommended)"
    )

    # Session transcript (PDF or TXT)
    session_transcript = models.FileField(
        upload_to='session_transcripts/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Upload session transcript (PDF or TXT)"
    )

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    STATUS_CHOICES = [
        ('Upcoming', 'Upcoming'),
        ('Completed', 'Completed'),
        ('Missed', 'Missed'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Completed')  # Default to completed since most entries will be for past classes
    
    class Meta:
        ordering = ['-session_time']
    
    def save(self, *args, **kwargs):
        # Automatically populate name fields from the related User objects only if not already set
        if self.tutor and not self.tutor_first_name:
            self.tutor_first_name = self.tutor.first_name
        if self.tutor and not self.tutor_last_name:
            self.tutor_last_name = self.tutor.last_name
        if self.student and not self.student_first_name:
            self.student_first_name = self.student.first_name
        if self.student and not self.student_last_name:
            self.student_last_name = self.student.last_name
        super().save(*args, **kwargs)
    
    def __str__(self):
        hours_str = f" ({self.hours_taught}h)" if self.hours_taught else ""
        tutor_name = f"{self.tutor_first_name} {self.tutor_last_name}".strip() or self.tutor.first_name
        student_name = f"{self.student_first_name} {self.student_last_name}".strip() or self.student.first_name
        return f"{tutor_name} tutoring {student_name} - {self.topic}{hours_str} ({self.session_time.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def pdf_filename(self):
        """Get just the filename of the uploaded PDF"""
        if self.session_pdf:
            return self.session_pdf.name.split('/')[-1]
        return None
    
    @property
    def has_pdf(self):
        """Check if session has an uploaded PDF"""
        return bool(self.session_pdf)


class StudentManagement(models.Model):
    """Model to manage students with pricing and tutor assignment"""
    # Link to existing User account (optional)
    linked_user = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_management_profile', limit_choices_to={'occupation': 'Student'}, help_text="Link to existing student account in Users database")
    
    # Student Information
    student_first_name = models.CharField(max_length=100)
    student_last_name = models.CharField(max_length=100)
    student_email = models.EmailField(blank=True, null=True)
    
    # Parent Information
    parent_email = models.EmailField()
    parent_phone = models.CharField(max_length=20, blank=True)
    
    # Address
    address = models.TextField()
    
    # Tutor Assignment
    assigned_tutor = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='assigned_students', limit_choices_to={'occupation': 'Tutor'})
    
    # Pricing
    CURRENCY_CHOICES = [
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)'),
        ('USD', 'US Dollar ($)'),
        ('PLN', 'Polish Złoty (zł)'),
    ]
    
    price_charged_to_parents = models.DecimalField(max_digits=8, decimal_places=2, help_text="Price charged to parents per hour")
    price_charged_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='EUR', help_text="Currency for price charged to parents")
    
    price_given_to_tutor = models.DecimalField(max_digits=8, decimal_places=2, help_text="Price given to tutor per hour")
    price_given_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='EUR', help_text="Currency for price given to tutor")
    
    # Additional Information
    curriculum = models.CharField(max_length=100, blank=True)
    subjects = models.CharField(max_length=200, blank=True, help_text="Subjects being tutored")
    notes = models.TextField(blank=True, help_text="Additional notes about the student")
    
    # Status
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('On Hold', 'On Hold'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    
    # Timestamps
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    # Rules Acceptance - Separate tracking for student and parent
    student_rules_accepted = models.BooleanField(default=False, help_text="Whether student has accepted the tutoring rules")
    student_rules_accepted_date = models.DateTimeField(null=True, blank=True, help_text="Date when student accepted rules")
    parent_rules_accepted = models.BooleanField(default=False, help_text="Whether parent has accepted the tutoring rules")
    parent_rules_accepted_date = models.DateTimeField(null=True, blank=True, help_text="Date when parent accepted rules")
    
    class Meta:
        ordering = ['student_first_name', 'student_last_name']
        # Removed unique_together constraint to allow same student with multiple tutors
        # The constraint was preventing the same student from being assigned to different tutors
    
    def save(self, *args, **kwargs):
        # Auto-sync data from linked user if available
        if self.linked_user:
            self.student_first_name = self.linked_user.first_name
            self.student_last_name = self.linked_user.last_name
            self.student_email = self.linked_user.email
            if not self.curriculum:  # Only update if not already set
                self.curriculum = self.linked_user.curriculum
        super().save(*args, **kwargs)
    
    def __str__(self):
        linked_status = " (Linked)" if self.linked_user else ""
        return f"{self.student_first_name} {self.student_last_name}{linked_status} (assigned to {self.assigned_tutor.first_name} {self.assigned_tutor.last_name})"
    
    @property
    def full_name(self):
        return f"{self.student_first_name} {self.student_last_name}"
    
    @property
    def profit_margin(self):
        return self.price_charged_to_parents - self.price_given_to_tutor
    
    @property
    def is_linked(self):
        return self.linked_user is not None
    
    def get_currency_symbol(self, currency_code):
        """Get currency symbol for display"""
        currency_symbols = {
            'EUR': '€',
            'GBP': '£',
            'USD': '$',
            'PLN': 'zł',
        }
        return currency_symbols.get(currency_code, currency_code)
    
    @property
    def price_charged_display(self):
        """Display price charged with currency"""
        symbol = self.get_currency_symbol(self.price_charged_currency)
        return f"{self.price_charged_to_parents} ({symbol})"
    
    @property
    def price_given_display(self):
        """Display price given with currency"""
        symbol = self.get_currency_symbol(self.price_given_currency)
        return f"{self.price_given_to_tutor} ({symbol})"
    
    @property
    def price_given_with_symbol(self):
        """Display price given with currency symbol (no brackets)"""
        symbol = self.get_currency_symbol(self.price_given_currency)
        return f"{symbol}{self.price_given_to_tutor}"


class GeneratedExamsPastPapers(models.Model):
    """Model to store generated past paper exams for users"""
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='generated_past_paper_exams', null=True, blank=True)
    apex_user = models.ForeignKey(ApexUsers, on_delete=models.CASCADE, related_name='generated_past_paper_exams', null=True, blank=True)
    
    SUBJECT_CHOICES = [
        ('ai_sl', 'Math AI SL'),
        ('ai_hl', 'Math AI HL'),
        ('aa_sl', 'Math AA SL'),
        ('aa_hl', 'Math AA HL'),
        ('physics_sl', 'Physics SL'),
        ('physics_hl', 'Physics HL'),
    ]
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    chapters = models.JSONField(help_text="List of chapter codes selected")
    paper = models.CharField(max_length=10, help_text="Paper number: 1, 2, all, 1A, 1B")
    question_limit = models.IntegerField(default=50)
    question_ids = models.JSONField(help_text="List of video IDs that were included in the PDF")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Generated Exam (Past Papers)"
        verbose_name_plural = "Generated Exams (Past Papers)"
        
    def __str__(self):
        return f"{self.user.email} - {self.get_subject_display()} - {self.created_at.strftime('%b %d, %Y %I:%M %p')}"
    
    @property
    def display_name(self):
        """Generate a display name for the exam"""
        return self.created_at.strftime('%b %d, %Y %I:%M %p')
    
    @property
    def question_count(self):
        """Get the number of questions in this exam"""
        return len(self.question_ids)


# ---------------------------------------------------------------------------
# Revision Engine
# ---------------------------------------------------------------------------

class RevisionChapter(models.Model):
    """Top-level grouping, e.g. 'Number & Algebra' for Math AI SL."""
    slug = models.SlugField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    subject = models.CharField(max_length=100, default='Math AI SL')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.subject} – {self.display_name}"


class RevisionTopic(models.Model):
    """A syllabus topic within a chapter, e.g. 'SL 1.2 – Arithmetic Sequences'."""
    chapter = models.ForeignKey(RevisionChapter, on_delete=models.CASCADE, related_name='topics')
    slug = models.SlugField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.display_name


class RevisionSkill(models.Model):
    """A single backend skill within a topic, e.g. 'arithmetic_nth_term'."""
    topic = models.ForeignKey(RevisionTopic, on_delete=models.CASCADE, related_name='skills')
    slug = models.SlugField(max_length=100, unique=True)
    display_name = models.CharField(max_length=300)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.topic.slug} › {self.slug}"


class QuestionSkillTag(models.Model):
    """Links a Math AI SL question to one or more revision skills with a weight."""
    question = models.ForeignKey(
        Math_AI_SL_Questionbank, on_delete=models.CASCADE, related_name='skill_tags'
    )
    skill = models.ForeignKey(RevisionSkill, on_delete=models.CASCADE, related_name='question_tags')
    weight = models.FloatField(
        default=1.0,
        help_text="Skill weight for this question (1.0 = primary, lower = secondary)"
    )

    class Meta:
        unique_together = ('question', 'skill')

    def __str__(self):
        return f"Q{self.question_id} → {self.skill.slug} (w={self.weight})"


class StudentSkillMastery(models.Model):
    """Tracks a student's mastery score for each revision skill."""
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='skill_masteries')
    skill = models.ForeignKey(RevisionSkill, on_delete=models.CASCADE, related_name='masteries')
    mastery_score = models.FloatField(default=0.3, help_text="Clamped between 0.05 and 0.95")
    confidence_score = models.FloatField(default=0.0, help_text="Grows with each attempt, capped at 1.0")
    attempts_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    last_practiced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'skill')

    def __str__(self):
        return f"{self.user.email} | {self.skill.slug} | {self.mastery_score:.2f}"

    @property
    def mastery_percent(self):
        return round(self.mastery_score * 100)

    @property
    def mastery_label(self):
        if self.mastery_score >= 0.75:
            return 'Mastered'
        elif self.mastery_score >= 0.5:
            return 'Developing'
        elif self.mastery_score >= 0.3:
            return 'Learning'
        return 'Struggling'


class RevisionAttempt(models.Model):
    """Records each time a student answers a sub-question in the revision engine."""
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='revision_attempts')
    question = models.ForeignKey(
        Math_AI_SL_Questionbank, on_delete=models.CASCADE, related_name='revision_attempts'
    )
    subquestion = models.ForeignKey(
        'RevisionSubQuestion', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='attempts', help_text="The specific sub-part that was answered"
    )
    skill = models.ForeignKey(
        RevisionSkill, on_delete=models.CASCADE, related_name='attempts',
        help_text="Skill being practiced when this question was served"
    )
    selected_label = models.CharField(
        max_length=1, blank=True, help_text="Which MCQ option was chosen (A/B/C/D)"
    )
    is_correct = models.BooleanField()
    hint_viewed = models.BooleanField(default=False)
    explanation_viewed = models.BooleanField(default=False)
    video_viewed = models.BooleanField(default=False)
    time_spent = models.PositiveIntegerField(null=True, blank=True, help_text="Seconds spent on question")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        part = f"({self.subquestion.part_label})" if self.subquestion_id else ""
        result = 'correct' if self.is_correct else 'incorrect'
        return f"{self.user.email} | Q{self.question_id}{part} [{self.selected_label}] | {result}"


class RevisionSubQuestion(models.Model):
    """A sub-part (a, b, c …) of a Math AI SL question for the MCQ practice flow."""
    question = models.ForeignKey(
        Math_AI_SL_Questionbank, on_delete=models.CASCADE, related_name='subquestions'
    )
    part_label = models.CharField(
        max_length=10, blank=True,
        help_text="e.g. 'a', 'b', 'c'. Leave blank for single-part questions."
    )
    question_text = models.TextField(help_text="Sub-question text (LaTeX/HTML supported)")
    skills = models.ManyToManyField(
        'RevisionSkill', blank=True, related_name='subquestions',
        help_text="Skill(s) this specific sub-part tests."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ('question', 'part_label')

    def __str__(self):
        label = f" ({self.part_label})" if self.part_label else ""
        return f"Q{self.question_id}{label} — {self.question.chapter}"


class RevisionMCQOption(models.Model):
    """One of four A/B/C/D answer choices for a RevisionSubQuestion."""
    LABELS = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]

    subquestion = models.ForeignKey(
        RevisionSubQuestion, on_delete=models.CASCADE, related_name='options'
    )
    label = models.CharField(max_length=1, choices=LABELS)
    option_text = models.TextField(help_text="Answer option text (LaTeX/HTML supported)")
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ['label']
        unique_together = ('subquestion', 'label')

    def __str__(self):
        correct = ' ✓' if self.is_correct else ''
        return f"Q{self.subquestion.question_id}({self.subquestion.part_label or '—'}) [{self.label}]{correct}"


class ClassTranscriptAnalysis(models.Model):
    """AI-generated analysis of a tutoring session transcript."""
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('analysed', 'Analysed'),
        ('applied',  'Applied'),
        ('rejected', 'Rejected'),
    ]

    class_session  = models.ForeignKey('TutorSession', on_delete=models.CASCADE, related_name='transcript_analyses')
    student        = models.ForeignKey('Users', on_delete=models.CASCADE, related_name='transcript_analyses')
    analysed_by    = models.ForeignKey('Users', on_delete=models.SET_NULL, null=True, blank=True, related_name='triggered_analyses')
    ai_json        = models.JSONField(null=True, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Analysis for session {self.class_session_id} | {self.student.email} | {self.status}"


class LearningPathProgress(models.Model):
    """Records which skills a student has completed in a learning path session."""
    student      = models.ForeignKey('Users', on_delete=models.CASCADE, related_name='lp_progress')
    analysis     = models.ForeignKey('ClassTranscriptAnalysis', on_delete=models.CASCADE, related_name='lp_progress')
    skill        = models.ForeignKey('RevisionSkill', on_delete=models.CASCADE, related_name='lp_progress')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'analysis', 'skill')
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.student.email} | {self.skill.slug} | analysis {self.analysis_id}"

