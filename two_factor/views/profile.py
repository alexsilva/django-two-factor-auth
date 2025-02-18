from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, resolve_url
from django.utils.functional import lazy
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, TemplateView
from django_otp import devices_for_user

from two_factor.plugins.phonenumber.utils import (
    backup_phones, get_available_phone_methods,
)

from ..forms import DisableForm
from ..utils import default_device
from .utils import class_view_decorator, otp_required_decorator


@class_view_decorator(never_cache)
@class_view_decorator(login_required)
class ProfileView(TemplateView):
    """
    View used by users for managing two-factor configuration.

    This view shows whether two-factor has been configured for the user's
    account. If two-factor is enabled, it also lists the primary verification
    method and backup verification methods.
    """
    template_name = 'two_factor/profile/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            backup_tokens = self.request.user.staticdevice_set.all()[0].token_set.count()
        except Exception:
            backup_tokens = 0
        context.update({
            'default_device': default_device(self.request.user),
            'default_device_type': default_device(self.request.user).__class__.__name__,
            'backup_phones': backup_phones(self.request.user),
            'backup_tokens': backup_tokens,
            'available_phone_methods': get_available_phone_methods()
        })
        return context


@class_view_decorator(never_cache)
class DisableView(FormView):
    """
    View for disabling two-factor for a user's account.
    """
    template_name = 'two_factor/profile/disable.html'
    success_url = opt_login_url = lazy(resolve_url, str)(settings.LOGIN_REDIRECT_URL)
    form_class = DisableForm

    @otp_required_decorator
    def dispatch(self, *args, **kwargs):
        # We call otp_required here because we want to use self.success_url as
        # the login_url. Using it as a class decorator would make it difficult
        # for users who wish to override this property
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        for device in devices_for_user(self.request.user):
            device.delete()
        return redirect(self.success_url)
