from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.contrib import messages

class SecurityPasswordChangeView(PasswordChangeView):
    success_url = reverse_lazy('password_change_done')
    template_name = 'registration/password_change_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        self.request.user.password_needs_reset = False
        self.request.user.save()
        
        messages.success(self.request, "Your password has been successfully updated!")
        
        return response
