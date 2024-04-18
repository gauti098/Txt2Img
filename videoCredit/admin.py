from django.contrib import admin
from django.utils.html import format_html
from videoCredit.models import (
        UserCredit, UserCurrentSubscription, VideoCreditInfo,
		CreditType
)


class UserCurrentSubscriptionAdmin(admin.ModelAdmin):
	model = UserCurrentSubscription
	readonly_fields = ('timestamp',)
	list_display = ['userName', 'userEmail', 'currentSubscription','subscriptionEnd', 'timestamp', ]

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

	def currentSubscription(self, obj):
		message = "<table>"
		_allSubscriptions = obj.subscription.all()
		if _allSubscriptions:
			for _sub in _allSubscriptions:
				message += f"""<tr><td style="text-align: center;padding: 1px;"><span style="color: #640de3;">{CreditType(_sub.creditType).name}</span></td><td style="text-align: center;padding: 1px;">{_sub.usedCredit}</td><td style="text-align: center;padding: 1px;">{_sub.totalCredit}</td></tr>""" #<td style="text-align: center;padding: 1px;">{_sub.subscriptionEnd.strftime('%Y/%m/%d, %H:%M:%S')}</td>
		message += "</table>"
		return format_html(message)

	userName.admin_order_field = 'user__first_name'
	userEmail.admin_order_field = 'user__email'
    

class VideoCreditInfoAdmin(admin.ModelAdmin):
	model = VideoCreditInfo
	readonly_fields = ('timestamp',)
	list_display = ['userEmail', 'credit_type','usedCredit','meta', 'timestamp', ]

	def credit_type(self, obj):
		return CreditType(obj.creditType).name

	def userEmail(self, obj):
		if obj.user:
			return obj.user.email
		else:
			return ""

	userEmail.admin_order_field = 'user__email'
    
admin.site.register(UserCurrentSubscription,UserCurrentSubscriptionAdmin)
admin.site.register(VideoCreditInfo,VideoCreditInfoAdmin)
admin.site.register(UserCredit)
