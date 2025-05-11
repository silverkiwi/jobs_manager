from accounts.models import Staff as AccountsStaff
from accounts.managers import StaffManager

class Staff(AccountsStaff):
    """
    Proxy model for Staff to maintain compatibility with existing code.
    This allows the code to continue referencing workflow.Staff while
    the actual model is now in accounts.Staff.
    """
    class Meta:
        proxy = True
        app_label = 'workflow'
