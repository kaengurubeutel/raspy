from django.apps import AppConfig

class WishesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wishes'

    def ready(self):
        import wishes.signals  # Importiere die Signals nach der App-Initialisierung