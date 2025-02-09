from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from pyngrok import conf, ngrok


class Command(BaseCommand):
    help = "Launches ngrok tunnel with configured domain"

    def handle(self, *args, **options):
        # Load environment variables
        load_dotenv()

        # Get preferred and fallback domains
        PREFERRED_DOMAIN = "msm-workflow.ngrok-free.app"
        FALLBACK_DOMAIN = "measured-enormously-man.ngrok-free.app"

        try:
            # Try preferred domain first
            self.stdout.write("Attempting to start ngrok tunnel...")
            try:
                tunnel = ngrok.connect(8000, domain=PREFERRED_DOMAIN)
                self.stdout.write(
                    self.style.SUCCESS(f"Tunnel established at: {tunnel.public_url}")
                )
            except Exception as e:
                if "failed to start tunnel" in str(e):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not use preferred domain ({PREFERRED_DOMAIN}), "
                            f"falling back to: {FALLBACK_DOMAIN}"
                        )
                    )
                    tunnel = ngrok.connect(8000, domain=FALLBACK_DOMAIN)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Tunnel established at: {tunnel.public_url}"
                        )
                    )
                else:
                    raise e

            # Keep the tunnel open
            ngrok_process = ngrok.get_ngrok_process()
            try:
                # Block until CTRL-C
                ngrok_process.proc.wait()
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\nShutting down ngrok tunnel..."))
                ngrok.kill()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to establish ngrok tunnel: {e}")
            )
            ngrok.kill()
