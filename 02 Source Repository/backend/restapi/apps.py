from django.apps import AppConfig


class RestApiConfig(AppConfig):
    name = "restapi"
    verbose_name = "AssureX Claim Engine REST API"

    def ready(self) -> None:
        # Import side-effect free: only the registry is touched here.
        from django.conf import settings

        from .services.models import registry

        if getattr(settings, "PRELOAD_MODELS", True):
            registry.start_in_background()
