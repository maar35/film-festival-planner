from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View


class SharedTemplateReferrerView(LoginRequiredMixin, View):
    """
    Base view class to refer different views to a shared template.
    """
    template_name = None
    list_view = None
    form_view = None

    def get(self, request, *args, **kwargs):
        view = self.list_view.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = self.form_view.as_view()
        return view(request, *args, **kwargs)
