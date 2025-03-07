from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Marks all users to require password reset on next login'

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()
        count = 0
        
        for user in users:
            user.password_needs_reset = True
            user.save()
            count += 1
            self.stdout.write(f"Usuário {user.email} marcado para redefinição de senha")
        
        self.stdout.write(self.style.SUCCESS(f"{count} usuários marcados para redefinir suas senhas"))
