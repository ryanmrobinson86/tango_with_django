from django.contrib import admin
from rango.models import Category, Page, UserProfile

class PageAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,{'fields':['category','title','url']})
    ]
    list_display = ('category','title','url')

admin.site.register(Category)
admin.site.register(Page, PageAdmin)
admin.site.register(UserProfile)
