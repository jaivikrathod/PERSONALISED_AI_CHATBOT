import json

from django.core.management.base import BaseCommand, CommandError

from knowledge.evaluation import evaluate
from knowledge.evaluation import tune as tune_gate
from registry.models import Chatbot


class Command(BaseCommand):
    help = "Measure (and optionally tune) a chatbot's knowledge gate against labelled questions (B4)."

    def add_arguments(self, parser):
        parser.add_argument("--chatbot", required=True, help="Chatbot slug.")
        parser.add_argument("--fixture", required=True, help='JSON file: {"cases": [{question, answerable, expect?}]}')
        parser.add_argument("--tune", action="store_true", help="Search accept_threshold × margin_rule.")
        parser.add_argument("--target", type=float, default=0.95, help="Required precision on the not-answerable set.")
        parser.add_argument("--write", action="store_true", help="Store the tuned values in the chatbot's policy.")

    def handle(self, *args, chatbot, fixture, tune=False, target=0.95, write=False, **options):
        bot = Chatbot.objects.filter(slug=chatbot).first()
        if bot is None:
            raise CommandError(f"No chatbot with slug {chatbot!r}.")
        try:
            with open(fixture) as handle:
                cases = json.load(handle)["cases"]
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read fixture: {exc}") from None

        report = tune_report = None
        if tune:
            tune_report = tune_gate(bot, cases, target_precision=target)
            if tune_report is None:
                raise CommandError(f"No setting reaches {target:.0%} precision on the not-answerable set.")
            report = tune_report
        else:
            report = evaluate(bot, cases)

        self.stdout.write(json.dumps(report.as_dict(), indent=2))

        if write:
            if tune_report is None:
                raise CommandError("--write needs --tune.")
            bot.policy = {**(bot.policy or {}), **{k: tune_report.settings[k] for k in ("accept_threshold", "margin_rule")}}
            bot.save(update_fields=["policy", "updated_at"])
            self.stdout.write(self.style.SUCCESS(f"Stored {tune_report.settings} on {bot.slug}."))
