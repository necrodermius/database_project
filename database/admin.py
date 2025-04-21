from django.contrib import admin
from django.apps import apps

app_config = apps.get_app_config('database')

for model_name, model in app_config.models.items():
    admin.site.register(model)
