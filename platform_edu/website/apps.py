from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'website'
    
    def ready(self):
        import website.signals
        import website.biology_sync_signals
        import website.physics_sync_signals
        import website.chemistry_sync_signals
        import website.math_ai_sync_signals
        import website.math_aa_sync_signals
        import website.comp_sci_sync_signals
        import website.history_sync_signals
        import website.student_management_signals