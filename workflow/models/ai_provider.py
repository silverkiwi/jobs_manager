from django.db import models

from workflow.enums import AIProviderTypes

class AIProvider(models.Model):
    name = models.CharField(max_length=100, help_text="Friendly name for this provider")
    api_key = models.CharField(max_length=255, null=True, blank=True, help_text="API Key for this AI Provider")
    active = models.BooleanField(default=False)
    company = models.ForeignKey("CompanyDefaults", on_delete=models.CASCADE, related_name="ai_providers")    
    provider_type = models.CharField(
        max_length=20,
        choices=AIProviderTypes,
        help_text="Type of AI provider"
    )

    def __str__(self):
        return f"{self.name} ({self.provider_type})"

    class Meta:
        verbose_name = "AI Provider"
        verbose_name_plural = "AI Providers"
