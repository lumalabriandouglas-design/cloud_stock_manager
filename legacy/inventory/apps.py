from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = "inventory"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in
        from .features import apply_invite

        def on_login(sender, request, user, **kwargs):
            apply_invite(user)

        user_logged_in.connect(on_login, dispatch_uid="inventory_apply_invite")
