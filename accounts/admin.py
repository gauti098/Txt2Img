from django.contrib import admin
from django.contrib.auth import get_user_model
from authemail.admin import EmailUserAdmin
from accounts.models import (
        Organization, ContactUs, FAQuestions,
        EmailGrab, IpLocationInfo
)


class MyUserAdmin(EmailUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
            ('Personal Info', {'fields': ('first_name', 'last_name')}),
            ('Permissions', {'fields': ('is_active', 'is_staff',
                                                                       'is_superuser', 'is_verified',
                                                                       'groups', 'user_permissions')}),
            ('Important dates', {'fields': ('last_login', 'date_joined')}),
            ('Custom info', {'fields': ('profile_image', 'phone_number', 'calendar_url', 'facebook_url', 'twitter_url',
             'linkedin_url', 'organization', 'org_is_admin', 'usedVideoCredit', 'totalVideoCredit', 'subs_start', 'subs_end')}),
    )


class EmailGrabAdmin(admin.ModelAdmin):
	model = EmailGrab
	readonly_fields = ('timestamp',)
	list_filter = ('clientSource',)
	list_display = ['email', 'userIp','timestamp', 'origin', 'clientDevice', 'clientCountry','clientRegion', 'clientCity', 'browser', 'userAgent', ]
	
	def clientCountry(self, obj):
		if obj.location:
			return obj.location.country
		else:
			return ""

	def clientRegion(self, obj):
		if obj.location:
			return obj.location.regionName
		else:
			return ""

	def clientCity(self, obj):
		if obj.location:
			return obj.location.city
		else:
			return ""

	clientCountry.admin_order_field = 'location__country'
	clientRegion.admin_order_field = 'location__regionName'
	clientCity.admin_order_field = 'location__city'


class IpLocationInfoAdmin(admin.ModelAdmin):
    model = IpLocationInfo
    readonly_fields = ('timestamp',)
    list_display = ['userIp', 'country', 'regionName','city','postalCode', 'timestamp']



class ContactUsAdmin(admin.ModelAdmin):
	model = ContactUs
	readonly_fields = ('timestamp','message',)
	list_display = ['userName','userEmail', 'status', 'problemCategory', 'shortMessage', 'timestamp',]
	
	def userName(self, obj):
		if obj.user:
			return f"{obj.user.first_name} {obj.user.last_name}"
		else:
			return ""

	def userEmail(self, obj):
		if obj.user:
			return obj.user.email
		else:
			return ""

	def shortMessage(self, obj):
		if len(obj.message)>50:
			return f"{obj.message[:50]}..."
		return obj.message

	userName.admin_order_field = 'user__first_name'
	userEmail.admin_order_field = 'user__email'
	shortMessage.admin_order_field = 'message'


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), MyUserAdmin)
admin.site.register(EmailGrab, EmailGrabAdmin)
admin.site.register(IpLocationInfo, IpLocationInfoAdmin)
admin.site.register(Organization)
admin.site.register(ContactUs,ContactUsAdmin)
admin.site.register(FAQuestions)
