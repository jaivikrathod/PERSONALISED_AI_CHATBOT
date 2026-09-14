"""Phase 1 — the loop (WORKFLOW.md B5, B6, B7; TASKS.md 1.2b–1.7).

The model is replaced by a scripted `FakeProvider`, so every test here is about
what the *server* guarantees regardless of what the model does: budgets end,
tenancy holds, a looping model still reaches a person, and the log is the
state. Retrieval itself runs for real against pgvector, as in
`test_retrieval.py`.
"""

import importlib
import re
import time
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from chat.models import ChatMessage, ChatSession, ToolExecution
from company.models import Company
from orchestration import executors
from orchestration.executors import ExecutorResult
from orchestration.orchestrator import (
    AGENT_HANDOFF_MESSAGE,
    SLOW_TURN_MESSAGE,
    resolve_session,
    run_turn,
)
from orchestration.providers import ChatProvider, ModelResponse, ToolCall
from orchestration.validation import ValidationFailed, validate_arguments
from questions.models import Question, UnansweredMessage
from registry.models import Chatbot, Tool
from registry.presets import SEARCH_KNOWLEDGE_SCHEMA, provision_chatbot
from tests.test_auth_and_tenancy import make_user
from users.models import User
from vector_question.services import build_retrieval_text, generate_embedding

SHIPPING_Q = "Do you ship internationally?"
SHIPPING_A = "Yes, we ship to 40 countries."


class FakeProvider(ChatProvider):
    """Plays a script of responses; `fallback` answers every call after it."""

    def __init__(self, *script, fallback=None):
        self.script = list(script)
        self.fallback = fallback
        self.calls = []

    def generate(self, *, system, history, tools, model, temperature):
        self.calls.append({"system": system, "history": history, "tools": tools})
        step = self.script.pop(0) if self.script else self.fallback
        if step is None:
            raise AssertionError("The model was called when it should not have been.")
        return step(history, tools) if callable(step) else step


def said(text):
    return ModelResponse(text=text)


def calls(*pairs):
    return ModelResponse(
        tool_calls=[ToolCall(name=name, args=args, id=f"call{i}") for i, (name, args) in enumerate(pairs)]
    )


def make_company(name, email):
    return Company.objects.create(name=name, email=email, mobile="1", address="a")


def add_faq(company, question, answer):
    row = Question.objects.create(company=company, question=question, answer=answer)
    row.embedding = generate_embedding(build_retrieval_text(question))
    row.is_vectorized = True
    row.save(update_fields=["embedding", "is_vectorized"])
    return row


@override_settings(ORCHESTRATION_TOOL_THREADS=False)
class LoopTestCase(TestCase):
    def setUp(self):
        self.company = make_company("Acme", "acme@example.com")
        self.chatbot = provision_chatbot(self.company)
        self.session = resolve_session(self.company.id)

    def turn(self, message, provider, **kwargs):
        result = run_turn(self.session, message, provider=provider, **kwargs)
        self.session.refresh_from_db()
        return result.frames[-1]


# --- 1.7 Prove it ------------------------------------------------------------
class GreetingTests(LoopTestCase):
    def test_a_greeting_produces_no_knowledge_search(self):
        """L1 dying: today a greeting triggers a vector scan and can escalate."""
        provider = FakeProvider(said("Hi! How can I help you today?"))

        with mock.patch("knowledge.retrieval.embed_query") as embed:
            frame = self.turn("hello", provider)

        embed.assert_not_called()
        self.assertEqual(ToolExecution.objects.count(), 0)
        self.assertEqual(frame["type"], "answer")
        self.assertEqual(frame["answer"], "Hi! How can I help you today?")
        self.assertFalse(frame["agent_needed"])
        self.assertEqual(
            sorted(t["name"] for t in provider.calls[0]["tools"]),
            ["request_human_agent", "search_knowledge"],
        )


class FollowUpTests(LoopTestCase):
    def test_a_follow_up_turn_resolves_against_prior_context(self):
        """L2 dying: the earlier call and its result are replayed, not merged."""
        add_faq(self.company, SHIPPING_Q, SHIPPING_A)

        self.turn(
            SHIPPING_Q,
            FakeProvider(
                calls(("search_knowledge", {"query": SHIPPING_Q})),
                said("Yes — we ship to 40 countries."),
            ),
        )

        seen = {}

        def answer_follow_up(history, tools):
            seen["user_texts"] = [h.text for h in history if h.role == "user" and h.text]
            seen["calls"] = [h.tool_call.args for h in history if h.tool_call]
            seen["results"] = [h.tool_result for h in history if h.role == "tool"]
            return said("Germany is one of them, yes.")

        frame = self.turn("and to Germany?", FakeProvider(answer_follow_up))

        self.assertEqual(seen["user_texts"], [SHIPPING_Q, "and to Germany?"])
        self.assertEqual(seen["calls"], [{"query": SHIPPING_Q}])
        self.assertEqual(
            seen["results"][0]["data"]["chunks"][0]["content"], SHIPPING_A
        )
        self.assertEqual(frame["answer"], "Germany is one of them, yes.")

    def test_old_tool_results_are_replaced_by_their_summary(self):
        add_faq(self.company, SHIPPING_Q, SHIPPING_A)
        self.turn(
            SHIPPING_Q,
            FakeProvider(calls(("search_knowledge", {"query": SHIPPING_Q})), said("Yes.")),
        )
        for text in ("thanks", "ok"):
            self.turn(text, FakeProvider(said("You're welcome.")))

        provider = FakeProvider(said("Anything else?"))
        self.turn("bye", provider)

        tool_items = [h for h in provider.calls[0]["history"] if h.role == "tool"]
        self.assertEqual(len(tool_items), 1)
        self.assertIn("summary", tool_items[0].tool_result["data"])
        # The call itself still carries forward with its arguments (B7).
        self.assertTrue(any(h.tool_call for h in provider.calls[0]["history"]))


class TenancyTests(LoopTestCase):
    def test_cross_tenant_tool_argument_is_ignored_not_honoured(self):
        """G1: a model-supplied company id never reaches the executor."""
        other = make_company("Other", "other@example.com")
        add_faq(self.company, SHIPPING_Q, SHIPPING_A)
        add_faq(other, SHIPPING_Q, "Other company's secret answer.")

        provider = FakeProvider(
            calls(("search_knowledge", {"query": SHIPPING_Q, "company_id": other.id})),
            said("Yes."),
        )
        with self.assertLogs("orchestration.orchestrator", level="WARNING") as logs:
            self.turn(SHIPPING_Q, provider)

        self.assertIn("G1", "".join(logs.output))
        execution = ToolExecution.objects.get()
        self.assertEqual(execution.raw_arguments["company_id"], other.id)
        self.assertNotIn("company_id", execution.validated_arguments)
        self.assertEqual(execution.company_id, self.company.id)

        result = ChatMessage.objects.get(role=ChatMessage.Role.TOOL).tool_result
        answers = [chunk["content"] for chunk in result["chunks"]]
        self.assertEqual(answers, [SHIPPING_A])

    def test_a_session_id_from_another_company_is_not_reused(self):
        other = make_company("Other", "other@example.com")
        foreign = resolve_session(other.id)

        session = resolve_session(self.company.id, foreign.id)

        self.assertNotEqual(session.id, foreign.id)
        self.assertEqual(session.company_id, self.company.id)


class BudgetTests(LoopTestCase):
    def setUp(self):
        super().setUp()
        # Budgets, not retrieval, are under test: a real embedding model load
        # would itself blow the wall-clock budget and mask the path we want.
        fast = mock.patch.dict(
            executors.EXECUTORS,
            {Tool.ToolType.KNOWLEDGE_SEARCH: lambda ctx, tool, args: ExecutorResult({"chunks": [1]}, "", 1)},
        )
        fast.start()
        self.addCleanup(fast.stop)

    def _always_searching(self, final_text):
        counter = iter(range(1000))

        def step(history, tools):
            if not tools:
                return said(final_text)
            return calls(("search_knowledge", {"query": f"q{next(counter)}"}))

        return step

    def test_exhausted_round_trips_degrade_to_a_final_answer_with_tools_withheld(self):
        provider = FakeProvider(fallback=self._always_searching("Here's what I know."))

        frame = self.turn("tell me everything", provider)

        self.assertEqual(frame["answer"], "Here's what I know.")
        rounds = self.chatbot.get_policy("model_round_trips")
        self.assertEqual(len(provider.calls), rounds + 1)
        self.assertEqual(provider.calls[-1]["tools"], [])
        self.assertIn("budget", provider.calls[-1]["system"])
        self.assertLessEqual(
            ToolExecution.objects.count(), self.chatbot.get_policy("tool_calls_per_turn")
        )

    def test_tool_call_cap_is_enforced_inside_one_response(self):
        many = calls(*[("search_knowledge", {"query": f"q{i}"}) for i in range(10)])
        provider = FakeProvider(many, fallback=lambda h, tools: said("Done."))

        with mock.patch.dict(
            executors.EXECUTORS,
            {Tool.ToolType.KNOWLEDGE_SEARCH: lambda ctx, tool, args: ExecutorResult({"chunks": []}, "", 0)},
        ):
            self.turn("search a lot", provider)

        self.assertEqual(
            ToolExecution.objects.count(), self.chatbot.get_policy("tool_calls_per_turn")
        )

    def test_exhaustion_with_no_final_answer_hands_off_instead_of_hanging(self):
        provider = FakeProvider(fallback=self._always_searching(""))

        frame = self.turn("tell me everything", provider)

        self.assertTrue(frame["agent_needed"])
        self.assertEqual(frame["answer"], AGENT_HANDOFF_MESSAGE)
        self.assertTrue(self.session.agent_needed)

    def test_wall_clock_exhaustion_apologises_and_hands_off(self):
        ticks = iter(range(0, 10_000, 30))  # 30 "seconds" per reading

        frame = self.turn("hello", FakeProvider(), clock=lambda: next(ticks))

        self.assertEqual(frame["answer"], SLOW_TURN_MESSAGE)
        self.assertTrue(frame["agent_needed"])

    @override_settings(ORCHESTRATION_TOOL_THREADS=True)
    def test_a_tool_timeout_is_a_result_not_an_exception(self):
        self.chatbot.policy = {"single_tool_timeout_ms": 50}
        self.chatbot.save()

        def slow(ctx, tool, args):
            time.sleep(0.5)
            return ExecutorResult({"chunks": []}, "", 0)

        provider = FakeProvider(
            calls(("search_knowledge", {"query": "anything"})),
            said("That lookup didn't respond, sorry."),
        )
        with mock.patch.dict(executors.EXECUTORS, {Tool.ToolType.KNOWLEDGE_SEARCH: slow}):
            frame = self.turn("anything", provider)

        self.assertEqual(ToolExecution.objects.get().status, ToolExecution.Status.TIMEOUT)
        tool_row = ChatMessage.objects.get(role=ChatMessage.Role.TOOL)
        self.assertEqual(tool_row.tool_result["error"]["code"], "timeout")
        self.assertEqual(frame["answer"], "That lookup didn't respond, sorry.")


class HandoffSafetyNetTests(LoopTestCase):
    def setUp(self):
        super().setUp()
        self.agent = make_user(self.company, User.Type.AGENT, "agent@example.com")

    def test_a_deliberately_looping_model_still_reaches_an_agent(self):
        def looping(history, tools):
            if not tools:
                return said("Let me try again.")
            return calls(("search_knowledge", {}))  # always invalid

        barren = self.chatbot.get_policy("handoff_after_barren_turns")
        frames = [
            self.turn(f"question {i}", FakeProvider(fallback=looping)) for i in range(barren)
        ]

        self.assertFalse(any(f["agent_needed"] for f in frames[:-1]))
        self.assertTrue(frames[-1]["agent_needed"])
        self.assertEqual(self.session.agent_id, self.agent.id)

    def test_greetings_do_not_count_toward_the_barren_streak(self):
        for _ in range(5):
            frame = self.turn("hi", FakeProvider(said("Hello!")))
        self.assertFalse(frame["agent_needed"])

    def test_an_explicit_request_for_a_human_skips_the_model(self):
        frame = self.turn("Can I talk to a human please?", FakeProvider())

        self.assertTrue(frame["agent_needed"])
        self.assertEqual(self.session.agent_id, self.agent.id)
        self.assertEqual(UnansweredMessage.objects.count(), 1)

    def test_the_model_can_hand_off_through_the_tool(self):
        provider = FakeProvider(
            calls(("request_human_agent", {"reason": "Customer is upset."})),
            said("I've asked a colleague to join."),
        )
        frame = self.turn("this is ridiculous", provider)

        self.assertTrue(frame["agent_needed"])
        self.assertEqual(self.session.agent_id, self.agent.id)
        self.assertEqual(ToolExecution.objects.get().status, ToolExecution.Status.OK)

    def test_a_live_agent_skips_the_model_entirely(self):
        self.session.agent = self.agent
        self.session.save()

        frame = self.turn("are you there?", FakeProvider())

        self.assertEqual(frame["type"], "delivered")
        self.assertTrue(frame["agent_handling"])

    def test_no_active_chatbot_hands_off_rather_than_failing(self):
        Chatbot.objects.update(is_active=False)
        session = ChatSession.objects.create(company=self.company)

        result = run_turn(session, "hello", provider=FakeProvider())

        self.assertTrue(result.frames[-1]["agent_needed"])

    def test_no_relevant_content_is_parked_for_a_human_to_answer(self):
        add_faq(self.company, SHIPPING_Q, SHIPPING_A)
        provider = FakeProvider(
            calls(("search_knowledge", {"query": "What time does the moon rise?"})),
            said("I don't have that information."),
        )
        self.turn("What time does the moon rise?", provider)

        result = ChatMessage.objects.get(role=ChatMessage.Role.TOOL).tool_result
        self.assertEqual(result, {"chunks": [], "reason": "no_relevant_content"})
        self.assertEqual(UnansweredMessage.objects.count(), 1)


class GateTests(LoopTestCase):
    def test_an_unknown_tool_is_rejected_with_the_available_tools(self):
        provider = FakeProvider(calls(("delete_everything", {})), said("I can't do that."))
        self.turn("delete it all", provider)

        execution = ToolExecution.objects.get()
        self.assertEqual(execution.status, ToolExecution.Status.REJECTED)
        self.assertEqual(execution.error_code, "unknown_tool")
        self.assertIsNone(execution.tool)
        result = ChatMessage.objects.get(role=ChatMessage.Role.TOOL).tool_result
        self.assertEqual(
            result["error"]["available_tools"], ["request_human_agent", "search_knowledge"]
        )

    def test_invalid_arguments_return_errors_naming_the_field(self):
        provider = FakeProvider(calls(("search_knowledge", {"top_k": 50})), said("Hmm."))
        self.turn("search", provider)

        errors = ChatMessage.objects.get(role=ChatMessage.Role.TOOL).tool_result["error"]["errors"]
        self.assertEqual(
            sorted((e["field"], e["code"]) for e in errors),
            [("query", "required"), ("top_k", "above_maximum")],
        )

    def test_an_identical_repeat_call_is_served_from_cache(self):
        executor = mock.Mock(return_value=ExecutorResult({"chunks": [1]}, "one", 1))
        provider = FakeProvider(
            calls(("search_knowledge", {"query": "x"}), ("search_knowledge", {"query": "x"})),
            said("Done."),
        )
        with mock.patch.dict(executors.EXECUTORS, {Tool.ToolType.KNOWLEDGE_SEARCH: executor}):
            self.turn("x", provider)

        executor.assert_called_once()
        self.assertEqual(
            list(ToolExecution.objects.values_list("status", flat=True)),
            [ToolExecution.Status.OK, ToolExecution.Status.CACHED],
        )

    def test_per_conversation_rate_limit_is_enforced(self):
        self.chatbot.tools.filter(name="search_knowledge").update(
            rate_limit={"per_conversation": 1}
        )
        executor = mock.Mock(return_value=ExecutorResult({"chunks": [1]}, "one", 1))
        provider = FakeProvider(
            calls(("search_knowledge", {"query": "a"})),
            calls(("search_knowledge", {"query": "b"})),
            said("Done."),
        )
        with mock.patch.dict(executors.EXECUTORS, {Tool.ToolType.KNOWLEDGE_SEARCH: executor}):
            self.turn("a then b", provider)

        self.assertEqual(
            list(ToolExecution.objects.values_list("status", flat=True)),
            [ToolExecution.Status.OK, ToolExecution.Status.RATE_LIMITED],
        )

    def test_validation_coerces_integral_floats_and_rejects_booleans(self):
        self.assertEqual(
            validate_arguments(SEARCH_KNOWLEDGE_SCHEMA, {"query": "q", "top_k": 5.0}),
            {"query": "q", "top_k": 5},
        )
        with self.assertRaises(ValidationFailed):
            validate_arguments(SEARCH_KNOWLEDGE_SCHEMA, {"query": "q", "top_k": True})


# --- Transcript and schema -----------------------------------------------------
class TranscriptTests(LoopTestCase):
    def test_people_never_see_tool_rows(self):
        add_faq(self.company, SHIPPING_Q, SHIPPING_A)
        self.turn(
            SHIPPING_Q,
            FakeProvider(calls(("search_knowledge", {"query": SHIPPING_Q})), said("Yes.")),
        )
        self.assertEqual(ChatMessage.objects.count(), 4)  # user, call, result, answer

        response = self.client.get(
            "/api/chat/history/",
            {"session_id": self.session.id, "token": self.session.public_token},
        )

        messages = response.json()["messages"]
        self.assertEqual([m["message"] for m in messages], [SHIPPING_Q, "Yes."])


class SchemaBackfillTests(TestCase):
    def test_existing_rows_get_a_role_and_their_companys_chatbot(self):
        company = make_company("Acme", "acme@example.com")
        chatbot = provision_chatbot(company)
        session = ChatSession.objects.create(company=company)
        common = {"company": company, "session": session}
        customer = ChatMessage.objects.create(message="hi", sent_by_us=False, **common)
        bot = ChatMessage.objects.create(message="hello", sent_by_us=True, is_ai=True, **common)
        agent = ChatMessage.objects.create(message="agent here", sent_by_us=True, **common)
        ChatMessage.objects.update(role="system")

        from django.apps import apps

        importlib.import_module("chat.migrations.0004_backfill_roles_and_chatbots").forwards(
            apps, None
        )

        roles = dict(ChatMessage.objects.values_list("id", "role"))
        self.assertEqual(roles[customer.id], "user")
        self.assertEqual(roles[bot.id], "assistant")
        self.assertEqual(roles[agent.id], "assistant")
        session.refresh_from_db()
        self.assertEqual(session.chatbot_id, chatbot.id)

    def test_registration_provisions_a_chatbot(self):
        payload = {
            "company": {"name": "Newco", "email": "n@example.com", "mobile": "1", "address": "a"},
            "admin": {
                "name": "Ada",
                "email": "ada@example.com",
                "password": "secret123",
                "gender": "Female",
                "dob": "1990-01-01",
            },
        }
        response = self.client.post("/api/auth/register/", payload, content_type="application/json")

        chatbot = Chatbot.objects.get(company_id=response.json()["company"]["id"])
        self.assertEqual(chatbot.tools.count(), 2)


# --- Structural guarantees ------------------------------------------------------
class StructureTests(TestCase):
    root = Path(settings.BASE_DIR)

    def test_the_consumer_is_transport_only(self):
        """1.6 done-when: no threshold comparison and no LLM call."""
        source = (self.root / "questions" / "consumers.py").read_text()
        for forbidden in ("THRESHOLD", "threshold", "generate_answer", "genai", "CosineDistance"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_only_the_provider_package_imports_the_gemini_sdk(self):
        """1.3 done-when."""
        pattern = re.compile(r"^\s*(from\s+google\s+import\s+genai|(from|import)\s+google\.genai)", re.M)
        allowed = self.root / "orchestration" / "providers"
        offenders = []
        for path in self.root.rglob("*.py"):
            if "venv" in path.parts or "tests" in path.parts or allowed in path.parents:
                continue
            if pattern.search(path.read_text(errors="ignore")):
                offenders.append(str(path.relative_to(self.root)))
        self.assertEqual(offenders, [])
