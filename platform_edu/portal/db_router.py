"""Route Donna operational tables to the test_don Postgres database."""

DONNA_DB = 'donna'

DONNA_PORTAL_MODELS = frozenset(
    {
        'whatsappdonnacontact',
        'whatsappdonnamessage',
    }
)


class DonnaDatabaseRouter:
    def db_for_read(self, model, **hints):
        if model._meta.model_name in DONNA_PORTAL_MODELS:
            return DONNA_DB
        return None

    def db_for_write(self, model, **hints):
        if model._meta.model_name in DONNA_PORTAL_MODELS:
            return DONNA_DB
        return None

    def allow_relation(self, obj1, obj2, **hints):
        names = {obj1._meta.model_name, obj2._meta.model_name}
        if names <= DONNA_PORTAL_MODELS:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == DONNA_DB:
            return app_label == 'portal' and model_name in DONNA_PORTAL_MODELS

        if app_label == 'portal' and model_name in DONNA_PORTAL_MODELS:
            return False

        return None
