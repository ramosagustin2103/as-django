from django.contrib import admin
from adminsmart.operative.models import Taxon


class TaxonAdmin(admin.ModelAdmin):
	list_display = ['nombre']
	list_filter = ['naturaleza']

admin.site.register(Taxon, TaxonAdmin)
