"""Phase 1.2 — the chatbot/tool registry (WORKFLOW.md B2.1, B2.4, B0).

What these pin, in the order they matter:

1. A preset is data, not a branch (Part D rule 3a) — provisioning is idempotent
   and upgrading between presets inserts rows rather than rewriting anything.
2. Slugs are unique platform-wide, because the public URL `/chat/<slug>` is
   resolved before any tenant is known (B2.1).
3. `policy` degrades to the shipped defaults, so a bot created before a budget
   existed still runs (B5).
4. What the model sees carries no ids (B3) — the declaration is a business
   capability, never a table name.
"""

from django.db.utils import IntegrityError
from django.test import TestCase

from company.models import Company
from registry.models import Chatbot, Tool, default_policy
from registry.presets import (
    CATALOGUE,
    QNA,
    provision_chatbot,
    provision_tools,
    unique_slug,
)


def make_company(name="Acme Realty", email="acme@example.com"):
    return Company.objects.create(
        name=name, email=email, mobile="9999999999", address="Ahmedabad"
    )


class ProvisioningTests(TestCase):
    def test_qna_preset_creates_the_two_phase_one_tools(self):
        chatbot = provision_chatbot(make_company(), QNA)

        self.assertEqual(
            sorted(chatbot.tools.values_list("name", flat=True)),
            ["request_human_agent", "search_knowledge"],
        )
        self.assertEqual(
            chatbot.tools.get(name="search_knowledge").tool_type,
            Tool.ToolType.KNOWLEDGE_SEARCH,
        )
        self.assertEqual(
            chatbot.tools.get(name="request_human_agent").tool_type,
            Tool.ToolType.HANDOFF,
        )

    def test_provisioning_twice_does_not_duplicate_or_overwrite(self):
        """Re-running onboarding must not clobber a description a company edited."""
        chatbot = provision_chatbot(make_company(), QNA)
        tool = chatbot.tools.get(name="search_knowledge")
        tool.description = "Search our own price list."
        tool.save()

        created = provision_tools(chatbot, QNA)

        self.assertEqual(created, [])
        self.assertEqual(chatbot.tools.count(), 2)
        tool.refresh_from_db()
        self.assertEqual(tool.description, "Search our own price list.")

    def test_upgrading_preset_inserts_rows_and_needs_no_migration(self):
        """B0: preset 2 is a strict superset of preset 1."""
        chatbot = provision_chatbot(make_company(), QNA)
        before = set(chatbot.tools.values_list("name", flat=True))

        provision_tools(chatbot, CATALOGUE)

        after = set(chatbot.tools.values_list("name", flat=True))
        self.assertTrue(before <= after)

    def test_unknown_preset_is_rejected_loudly(self):
        chatbot = provision_chatbot(make_company(), QNA)
        with self.assertRaises(ValueError):
            provision_tools(chatbot, "real_estate")


class SlugTests(TestCase):
    def test_slug_is_derived_from_the_company_name(self):
        chatbot = provision_chatbot(make_company("Acme Realty"))
        self.assertEqual(chatbot.slug, "acme-realty")

    def test_colliding_names_across_tenants_get_distinct_slugs(self):
        """Slugs are global: `/chat/<slug>` resolves before a tenant is known."""
        first = provision_chatbot(make_company("Acme", "a@example.com"))
        second = provision_chatbot(make_company("Acme", "b@example.com"))

        self.assertEqual(first.slug, "acme")
        self.assertEqual(second.slug, "acme-2")

    def test_slug_uniqueness_is_enforced_by_the_database_too(self):
        provision_chatbot(make_company("Acme", "a@example.com"))
        with self.assertRaises(IntegrityError):
            Chatbot.objects.create(
                company=make_company("Other", "b@example.com"),
                slug="acme",
                name="Other",
            )

    def test_a_name_with_no_slug_characters_still_yields_a_url(self):
        self.assertEqual(unique_slug("!!!"), "chatbot")


class PolicyTests(TestCase):
    def test_new_chatbot_ships_with_the_b5_budgets(self):
        chatbot = provision_chatbot(make_company())
        self.assertEqual(chatbot.policy["tool_calls_per_turn"], 4)

    def test_accept_threshold_matches_the_measured_retrieval_constant(self):
        """Part D rule 2: 0.40 is measured, pinned by tests/test_retrieval.py."""
        self.assertEqual(default_policy()["accept_threshold"], 0.40)

    def test_missing_budget_falls_back_instead_of_raising(self):
        """Backfilled rows carry `policy={}` and still have to run."""
        chatbot = provision_chatbot(make_company())
        chatbot.policy = {}
        chatbot.save()

        self.assertEqual(chatbot.get_policy("wall_clock_ms"), 20000)

    def test_a_stored_budget_overrides_the_default(self):
        chatbot = provision_chatbot(make_company())
        chatbot.policy = {"tool_calls_per_turn": 1}
        chatbot.save()

        self.assertEqual(chatbot.get_policy("tool_calls_per_turn"), 1)
        self.assertEqual(chatbot.get_policy("model_round_trips"), 3)


class ToolTests(TestCase):
    def test_two_chatbots_may_share_a_tool_name(self):
        a = provision_chatbot(make_company("A", "a@example.com"))
        b = provision_chatbot(make_company("B", "b@example.com"))
        self.assertTrue(a.tools.filter(name="search_knowledge").exists())
        self.assertTrue(b.tools.filter(name="search_knowledge").exists())

    def test_one_chatbot_may_not_have_two_tools_of_the_same_name(self):
        chatbot = provision_chatbot(make_company())
        with self.assertRaises(IntegrityError):
            Tool.objects.create(
                chatbot=chatbot,
                name="search_knowledge",
                description="duplicate",
                tool_type=Tool.ToolType.KNOWLEDGE_SEARCH,
            )

    def test_declaration_leaks_no_ids_or_table_names(self):
        """B3: the model sees a capability, the backend keeps the mapping."""
        chatbot = provision_chatbot(make_company())
        tool = chatbot.tools.get(name="search_knowledge")
        tool.configuration = {"source_ids": [7]}
        tool.save()

        declaration = tool.declaration()

        self.assertEqual(set(declaration), {"name", "description", "parameters"})
        self.assertNotIn("source_ids", str(declaration))
        self.assertEqual(declaration["parameters"]["required"], ["query"])

    def test_a_tool_with_no_compiled_schema_still_declares_validly(self):
        """Phase 2 writes `input_schema` on publish; before that it is empty."""
        chatbot = provision_chatbot(make_company())
        tool = Tool.objects.create(
            chatbot=chatbot,
            name="search_listings",
            description="Search listings.",
            tool_type=Tool.ToolType.STRUCTURED_SEARCH,
            configuration={"data_source_id": 1},
        )

        self.assertEqual(
            tool.declaration()["parameters"],
            {"type": "object", "properties": {}},
        )


class BackfillMigrationTests(TestCase):
    """`registry.0002` — every company that works today keeps working.

    Runs the migration's own `forwards` against the current models rather than
    rewinding the schema, which is enough to pin the two things that can break
    it: a company that already has a bot, and two companies with the same name.
    """

    def _run_forwards(self):
        # The module name starts with a digit, so it cannot be imported with
        # `from ... import`.
        import importlib

        from django.apps import apps

        migration = importlib.import_module(
            "registry.migrations.0002_backfill_chatbots"
        )
        migration.forwards(apps, None)

    def test_backfill_gives_every_company_a_bot_with_the_preset_tools(self):
        make_company("Acme Realty", "a@example.com")
        make_company("Beta Shop", "b@example.com")

        self._run_forwards()

        self.assertEqual(Chatbot.objects.count(), 2)
        for chatbot in Chatbot.objects.all():
            self.assertEqual(
                sorted(chatbot.tools.values_list("name", flat=True)),
                ["request_human_agent", "search_knowledge"],
            )

    def test_backfill_skips_a_company_that_already_has_a_bot(self):
        company = make_company()
        provision_chatbot(company)

        self._run_forwards()

        self.assertEqual(Chatbot.objects.filter(company=company).count(), 1)

    def test_backfill_disambiguates_identically_named_companies(self):
        make_company("Acme", "a@example.com")
        make_company("Acme", "b@example.com")

        self._run_forwards()

        self.assertEqual(Chatbot.objects.count(), 2)
        self.assertEqual(Chatbot.objects.filter(slug="acme").count(), 1)

    def test_backfilled_policy_is_empty_so_new_budgets_are_inherited(self):
        make_company()

        self._run_forwards()

        chatbot = Chatbot.objects.get()
        self.assertEqual(chatbot.policy, {})
        self.assertEqual(chatbot.get_policy("tool_calls_per_turn"), 4)
