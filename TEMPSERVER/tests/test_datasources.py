"""Phase 2 — structured data, the universality payoff (WORKFLOW.md B2.3, B3, E2–E4).

Pinned here, in the order the product depends on them:

1. A second, unrelated vertical onboards through the API with no Python.
2. `data_source_fields` is the security boundary: a hidden field cannot be
   filtered on and never comes back; a fixed filter is always applied.
3. The B0/E2 worked examples compile to the right IR and the right rows.
4. Results narrow instead of dead-ending (`matched`, `truncated`,
   `relaxable_filters`).
5. One conversation crosses between `search_knowledge` and `search_<thing>`.
"""

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from chat.models import ChatMessage, ToolExecution
from company.models import Company
from datasources import types
from datasources.declarations import compile_input_schema
from datasources.ingest import import_records
from datasources.models import DataRecord, DataSource
from datasources.publishing import PublishError, publish, publish_errors
from datasources.search import validate_ir
from orchestration.orchestrator import resolve_session, run_turn
from orchestration.validation import ValidationFailed
from registry.models import Chatbot, Tool
from registry.presets import provision_chatbot
from tests.test_orchestration import FakeProvider, add_faq, calls, said

PROPERTIES_CSV = """ref,title,listing_type,property_type,city,locality,bedrooms,sale_price,monthly_rent,deposit,area_sqft,floor,total_floors,is_top_floor,furnishing,amenities,status,description,owner_phone,internal_margin
P-101,Shivalik Residency,buy,apartment,Ahmedabad,New Ranip,2,6500000,,,1050,3,11,false,unfurnished,lift;parking,available,Spacious 2BHK near the metro,9825000001,120000
P-102,Green Heights,rent,apartment,Ahmedabad,Chandkheda,1,,14000,50000,620,5,9,false,semi,lift;gym,available,Cosy 1BHK,9825000002,2000
P-103,Ranip Towers,buy,apartment,Ahmedabad,New Ranip,2,7200000,,,1100,12,12,true,furnished,lift;parking;gym,available,Top floor 2BHK,9825000003,150000
P-104,Sunrise Villa,buy,villa,Ahmedabad,SG Highway,4,25000000,,,3200,1,2,false,furnished,garden;parking,available,Independent villa,9825000004,900000
P-105,Old Ranip Flat,buy,apartment,Ahmedabad,New Ranip,2,5900000,,,980,2,7,false,unfurnished,parking,sold,Already sold 2BHK,9825000005,100000
P-106,Metro Nest,rent,apartment,Ahmedabad,New Ranip,1,,12000,40000,550,4,10,false,semi,lift,available,Near metro,9825000006,1500
P-107,Surat Heights,rent,apartment,Surat,Adajan,1,,11000,30000,600,2,8,false,unfurnished,lift,available,Quiet street,9825000007,1200
P-108,Chandkheda Homes,buy,apartment,Ahmedabad,Chandkheda,3,9200000,,,1500,6,14,false,semi,lift;parking,available,Family 3BHK,9825000008,200000
P-109,SG Studio,rent,apartment,Ahmedabad,SG Highway,1,,18000,60000,500,9,15,false,furnished,lift;gym,available,Furnished studio,9825000009,2500
P-110,Ranip Let,rent,apartment,Ahmedabad,New Ranip,1,,13000,40000,560,3,9,false,semi,lift,rented,Already let,9825000010,1400
"""

PRODUCTS_CSV = """sku,name,category,sub_category,brand,price,size,color,in_stock,cost_price
SKU-77,Running Shoes,Footwear,Sports,Nike,4999,9,Black,true,2100
SKU-78,Cotton Kurta,Clothing,Ethnic,Fabindia,1899,M,Blue,true,700
SKU-79,Silk Kurta,Clothing,Ethnic,Fabindia,1500,L,Blue,false,600
SKU-80,Denim Jacket,Clothing,Western,Levis,3499,L,Blue,true,1500
"""

PROPERTY_DESCRIPTIONS = {
    "bedrooms": "Number of bedrooms. Customers call this BHK — '2BHK' means 2.",
    "property_type": "Customers may say 'flat' for apartment, 'bungalow' for villa.",
    "listing_type": "'buy' for properties for sale, 'rent' for rentals.",
    "is_top_floor": "Whether the flat is on the top floor.",
}


def make_company(name, email):
    return Company.objects.create(name=name, email=email, mobile="1", address="a")


def build_properties(chatbot, csv_text=PROPERTIES_CSV):
    source = DataSource.objects.create(
        company=chatbot.company,
        chatbot=chatbot,
        name="properties",
        display_name="Properties",
        description="Search available property listings to buy or rent by location, budget and size.",
    )
    import_records(source, "properties.csv", csv_text.encode())
    for field in source.fields.all():
        if field.name == "status":
            field.is_exposed = False
        if field.is_exposed:
            field.description = PROPERTY_DESCRIPTIONS.get(field.name, f"The listing's {field.label}.")
        field.save()
    source.config = {**source.config, "fixed_filters": [{"field": "status", "operator": "equals", "value": "available"}]}
    source.schema_confirmed_at = timezone.now()
    source.save()
    publish(source)
    source.refresh_from_db()
    return source


@override_settings(ORCHESTRATION_TOOL_THREADS=False)
class StructuredTestCase(TestCase):
    def setUp(self):
        self.company = make_company("Acme Realty", "acme@example.com")
        self.chatbot = provision_chatbot(self.company)
        self.source = build_properties(self.chatbot)

    def search(self, args, tool="search_properties"):
        session = resolve_session(self.company.id)
        run_turn(session, "search", provider=FakeProvider(calls((tool, args)), said("ok")))
        execution = ToolExecution.objects.filter(conversation=session).get()
        result = ChatMessage.objects.get(session=session, role=ChatMessage.Role.TOOL).tool_result
        return result, execution

    def refs(self, result):
        return sorted(row["ref"] for row in result["rows"])


# --- 2.2 Ingestion ------------------------------------------------------------------
class IngestionTests(StructuredTestCase):
    def test_types_are_inferred_from_the_data(self):
        inferred = dict(self.source.fields.values_list("name", "data_type"))
        self.assertEqual(inferred["bedrooms"], types.INTEGER)
        self.assertEqual(inferred["sale_price"], types.INTEGER)
        self.assertEqual(inferred["is_top_floor"], types.BOOLEAN)
        self.assertEqual(inferred["amenities"], types.STRING_ARRAY)
        self.assertEqual(inferred["locality"], types.STRING)

        record = DataRecord.objects.get(external_id="P-101")
        self.assertEqual(record.payload["sale_price"], 6500000)
        self.assertEqual(record.payload["amenities"], ["lift", "parking"])
        self.assertNotIn("monthly_rent", record.payload)  # blank → absent, not null

    def test_sensitive_looking_columns_start_hidden(self):
        hidden = set(self.source.fields.filter(is_exposed=False).values_list("name", flat=True))
        self.assertLessEqual({"owner_phone", "internal_margin"}, hidden)

    def test_cardinality_drives_enum_versus_free_text(self):
        locality = self.source.fields.get(name="locality")
        self.assertEqual(locality.cardinality, 4)
        self.assertEqual(locality.allowed_operators, [types.EQUALS])
        self.assertIn("New Ranip", locality.enum_values)

    def test_reimporting_upserts_and_replace_soft_deletes(self):
        changed = PROPERTIES_CSV.replace("P-101,Shivalik Residency,buy,apartment,Ahmedabad,New Ranip,2,6500000", "P-101,Shivalik Residency,buy,apartment,Ahmedabad,New Ranip,2,6600000")
        sync = import_records(self.source, "properties.csv", changed.encode())

        self.assertEqual((sync.rows_upserted, sync.rows_rejected), (10, 0))
        self.assertEqual(DataRecord.objects.filter(data_source=self.source).count(), 10)
        self.assertEqual(DataRecord.objects.get(external_id="P-101").payload["sale_price"], 6600000)

        without_last = "\n".join(PROPERTIES_CSV.strip().splitlines()[:-1]) + "\n"
        import_records(self.source, "properties.csv", without_last.encode(), mode="replace")
        self.source.refresh_from_db()
        self.assertEqual(self.source.row_count, 9)
        self.assertIsNotNone(DataRecord.objects.get(external_id="P-110").deleted_at)

    def test_bad_rows_are_rejected_and_reported(self):
        csv_text = PROPERTIES_CSV + ",No ref,buy\nP-101,Duplicate,buy\n"
        sync = import_records(self.source, "properties.csv", csv_text.encode())
        self.assertEqual(sync.rows_rejected, 2)
        self.assertTrue(any("missing ref" in e for e in sync.errors))
        self.assertTrue(any("duplicate" in e for e in sync.errors))

    def test_json_upload_is_accepted(self):
        source = DataSource.objects.create(company=self.company, chatbot=self.chatbot, name="items", display_name="Items")
        body = json.dumps({"records": [{"id": 1, "name": "A", "tags": ["x", "y"], "price": 9.5}]})
        sync = import_records(source, "items.json", body.encode())

        self.assertEqual(sync.rows_upserted, 1)
        self.assertEqual(dict(source.fields.values_list("name", "data_type"))["tags"], types.STRING_ARRAY)
        self.assertEqual(DataRecord.objects.get(data_source=source).payload["price"], 9.5)

    def test_new_columns_require_the_schema_to_be_confirmed_again(self):
        extended = PROPERTIES_CSV.replace("owner_phone,internal_margin", "owner_phone,internal_margin,parking_slots", 1)
        import_records(self.source, "properties.csv", extended.encode())
        self.source.refresh_from_db()
        self.assertIsNone(self.source.schema_confirmed_at)


class ModellingTrapWarningTests(TestCase):
    def setUp(self):
        company = make_company("Acme", "a@example.com")
        self.chatbot = provision_chatbot(company)
        self.company = company

    def warn(self, csv_text, name="things"):
        source = DataSource.objects.create(company=self.company, chatbot=self.chatbot, name=name, display_name=name)
        return {w["code"] for w in import_records(source, f"{name}.csv", csv_text.encode()).warnings}

    def test_one_price_column_for_buy_and_rent_is_flagged(self):
        csv_text = "ref,listing_type,price\n" + "\n".join(
            [f"B{i},buy,{6500000 + i}" for i in range(3)] + [f"R{i},rent,{14000 + i}" for i in range(3)]
        )
        self.assertIn("column_meaning_depends_on_another", self.warn(csv_text))

    def test_the_e2_template_itself_raises_no_dependent_column_warning(self):
        self.assertNotIn("column_meaning_depends_on_another", self.warn(PROPERTIES_CSV))

    def test_a_source_holding_one_category_is_flagged(self):
        csv_text = "ref,listing_type,price\n" + "\n".join(f"R{i},rent,{14000 + i}" for i in range(6))
        self.assertIn("looks_split_by_category", self.warn(csv_text))

    def test_a_collapsed_hierarchy_is_flagged(self):
        csv_text = "sku,category\nA,Clothing > Ethnic\nB,Clothing > Western\nC,Footwear > Sports\nD,Footwear > Casual\n"
        self.assertIn("collapsed_hierarchy", self.warn(csv_text))


# --- Publishing and 2.3 declarations ----------------------------------------------------
class PublishingTests(StructuredTestCase):
    def test_publishing_needs_a_confirmed_schema_and_described_fields(self):
        source = DataSource.objects.create(company=self.company, chatbot=self.chatbot, name="more", display_name="More", description="More listings.")
        import_records(source, "more.csv", PROPERTIES_CSV.encode())

        codes = {e["code"] for e in publish_errors(source)}
        self.assertIn("schema_not_confirmed", codes)

        source.schema_confirmed_at = timezone.now()
        source.save()
        with self.assertRaises(PublishError) as raised:
            publish(source)
        blank = {e["field"] for e in raised.exception.errors if e["code"] == "description_required"}
        self.assertIn("bedrooms", blank)
        self.assertNotIn("owner_phone", blank)  # hidden fields need no description

    def test_publish_generates_the_search_tool(self):
        tool = Tool.objects.get(chatbot=self.chatbot, name="search_properties")
        self.assertEqual(tool.tool_type, Tool.ToolType.STRUCTURED_SEARCH)
        self.assertTrue(tool.is_active)

    def test_the_declaration_is_flat_and_leaks_nothing(self):
        declaration = Tool.objects.get(name="search_properties").declaration()
        params = declaration["parameters"]["properties"]

        self.assertEqual(params["locality"]["type"], "string")
        self.assertIn("New Ranip", params["locality"]["enum"])
        self.assertEqual(params["bedrooms"]["type"], "integer")
        self.assertIn("BHK", params["bedrooms"]["description"])
        self.assertEqual({params["min_sale_price"]["type"], params["max_sale_price"]["type"]}, {"integer"})
        self.assertEqual(params["is_top_floor"]["type"], "boolean")
        self.assertEqual(params["amenities"]["type"], "array")
        self.assertIn("sale_price_asc", params["sort_by"]["enum"])
        self.assertEqual(params["limit"]["maximum"], self.chatbot.get_policy("max_rows_returned"))

        for absent in ("status", "owner_phone", "internal_margin", "max_internal_margin"):
            self.assertNotIn(absent, params)
        text = json.dumps(declaration)
        for leak in ("data_source_id", "operator", "payload", "data_records", str(self.source.id) + '"'):
            self.assertNotIn(leak, text)

    def test_editing_a_field_recompiles_the_cached_declaration(self):
        tool = Tool.objects.get(name="search_properties")
        before = tool.schema_version

        field = self.source.fields.get(name="locality")
        field.description = "Neighbourhood within the city."
        field.save()

        tool.refresh_from_db()
        self.assertEqual(tool.schema_version, before + 1)
        self.assertIn("Neighbourhood", tool.input_schema["properties"]["locality"]["description"])

    def test_expression_indexes_are_created_once_at_publish(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'data_records' AND indexname LIKE %s", [f"dr_s{self.source.id}_%"])
            names = [row[0] for row in cursor.fetchall()]
        numeric_or_date = self.source.fields.filter(
            is_exposed=True, data_type__in=types.ORDERED_TYPES
        ).count()
        self.assertEqual(len(names), numeric_or_date)


# --- 2.4 Compiler, validator, adapter ---------------------------------------------------
class StructuredSearchTests(StructuredTestCase):
    def test_the_b0_worked_example_end_to_end(self):
        """'2BHK in New Ranip, not top floor' → the right IR → the right rows."""
        result, execution = self.search({"locality": "New Ranip", "bedrooms": 2, "is_top_floor": False})

        self.assertEqual(self.refs(result), ["P-101"])  # P-103 is top floor, P-105 is sold
        self.assertEqual(
            execution.compiled_query["ir"]["filters"],
            [
                {"field": "locality", "operator": "equals", "value": "New Ranip"},
                {"field": "bedrooms", "operator": "equals", "value": 2},
                {"field": "is_top_floor", "operator": "equals", "value": False},
            ],
        )

    def test_the_fixed_filter_means_sold_properties_are_never_shown(self):
        result, _ = self.search({"locality": "New Ranip", "status": "sold"})
        self.assertNotIn("P-105", self.refs(result))
        self.assertNotIn("P-110", self.refs(result))
        self.assertEqual(self.refs(result), ["P-101", "P-103", "P-106"])

    def test_a_hidden_field_is_invisible_in_both_directions(self):
        result, _ = self.search({"max_internal_margin": 1, "city": "Ahmedabad"})
        self.assertGreater(result["matched"], 0)  # the unknown argument was ignored
        for row in result["rows"]:
            self.assertNotIn("owner_phone", row)
            self.assertNotIn("internal_margin", row)
            self.assertNotIn("status", row)

        fields = {f.name: f for f in self.source.fields.all()}
        with self.assertRaises(ValidationFailed) as raised:
            validate_ir(
                {"filters": [{"field": "internal_margin", "operator": "lte", "value": 1}], "sort": [], "limit": 5},
                fields,
                max_rows=20,
            )
        self.assertEqual(raised.exception.errors[0]["code"], "unknown_field")

    def test_g5_and_g6_reject_with_the_allowed_values(self):
        fields = {f.name: f for f in self.source.fields.all()}

        def errors(field, operator, value):
            with self.assertRaises(ValidationFailed) as raised:
                validate_ir({"filters": [{"field": field, "operator": operator, "value": value}], "sort": [], "limit": 5}, fields, max_rows=20)
            return raised.exception.errors[0]

        self.assertEqual(errors("bedrooms", "ilike", "2")["allowed"], ["equals", "gte", "lte"])
        not_allowed = errors("locality", "equals", "new ranip")
        self.assertEqual(not_allowed["code"], "not_allowed")
        self.assertIn("New Ranip", not_allowed["allowed"])
        self.assertEqual(errors("bedrooms", "equals", "two")["code"], "wrong_type")

    def test_an_invalid_enum_reaches_the_model_as_an_informed_rejection(self):
        tool = Tool.objects.get(name="search_properties")
        schema = dict(tool.input_schema)
        schema["properties"] = {**schema["properties"], "locality": {"type": "string"}}  # stale cache
        Tool.objects.filter(id=tool.id).update(input_schema=schema)

        result, execution = self.search({"locality": "new ranip"})

        self.assertEqual(execution.status, ToolExecution.Status.REJECTED)
        self.assertIn("New Ranip", result["error"]["errors"][0]["allowed"])

    def test_a_zero_result_query_names_the_filter_to_relax(self):
        result, _ = self.search({"locality": "New Ranip", "bedrooms": 2, "max_sale_price": 1000000})
        self.assertEqual(result["matched"], 0)
        self.assertEqual(result["relaxable_filters"], ["max_sale_price"])

    def test_a_city_level_query_is_truncated_so_the_bot_narrows(self):
        result, _ = self.search({"listing_type": "rent", "bedrooms": 1, "city": "Ahmedabad", "limit": 2})
        self.assertEqual((result["matched"], result["returned"], result["truncated"]), (3, 2, True))

    def test_a_locality_query_works_alongside_a_city_query(self):
        result, _ = self.search({"locality": "Chandkheda"})
        self.assertEqual(self.refs(result), ["P-102", "P-108"])

    def test_buy_and_rent_live_in_one_source_with_separate_price_columns(self):
        under_80_lakh, _ = self.search({"max_sale_price": 8000000})
        self.assertEqual(self.refs(under_80_lakh), ["P-101", "P-103"])  # rentals have no sale_price
        under_15k, _ = self.search({"max_monthly_rent": 15000, "city": "Ahmedabad"})
        self.assertEqual(self.refs(under_15k), ["P-102", "P-106"])

    def test_sorting_and_array_filters(self):
        result, _ = self.search({"amenities": ["gym"], "sort_by": "sale_price_desc", "listing_type": "buy"})
        self.assertEqual([r["ref"] for r in result["rows"]], ["P-103"])
        cheapest, _ = self.search({"listing_type": "rent", "sort_by": "monthly_rent_asc", "limit": 1})
        self.assertEqual(cheapest["rows"][0]["ref"], "P-107")

    def test_a_tool_pointing_at_another_tenants_source_finds_nothing(self):
        other = provision_chatbot(make_company("Other", "o@example.com"))
        foreign = build_properties(other)
        tool = Tool.objects.get(chatbot=self.chatbot, name="search_properties")
        tool.configuration = {"data_source_id": foreign.id}
        tool.save()

        result, _ = self.search({"city": "Ahmedabad"})
        self.assertEqual(result["error"]["code"], "tool_unavailable")


# --- 2.5 Prove it ----------------------------------------------------------------------
class ConversationTests(StructuredTestCase):
    def test_the_e2_questions_cross_tools_in_one_conversation(self):
        add_faq(self.company, "How much brokerage do you charge?", "1% of the deal value.")
        session = resolve_session(self.company.id)

        run_turn(session, "i want to buy 2bhk property into new ranip", provider=FakeProvider(
            calls(("search_properties", {"listing_type": "buy", "bedrooms": 2, "locality": "New Ranip"})), said("Two options."),
        ))
        run_turn(session, "how much brokerage you take", provider=FakeProvider(
            calls(("search_knowledge", {"query": "how much brokerage you take"})), said("1%."),
        ))
        run_turn(session, "i want to rent a 1bhk flat in ahmedabad", provider=FakeProvider(
            calls(("search_properties", {"listing_type": "rent", "bedrooms": 1, "city": "Ahmedabad"})), said("Three rentals."),
        ))

        executions = list(ToolExecution.objects.filter(conversation=session).values_list("tool_name", "status", "rows_returned"))
        self.assertEqual(
            executions,
            [("search_properties", "ok", 2), ("search_knowledge", "ok", 1), ("search_properties", "ok", 3)],
        )


class SecondVerticalTests(TestCase):
    """The acceptance test for the whole product: onboard an unrelated vertical
    through the API alone — no Python, no code change."""

    def api(self, method, url, token, **kwargs):
        return getattr(self.client, method)(url, HTTP_AUTHORIZATION=f"Bearer {token}", **kwargs)

    def register(self, name, email):
        response = self.client.post(
            "/api/auth/register/",
            {
                "company": {"name": name, "email": email, "mobile": "1", "address": "a"},
                "admin": {"name": "Ada", "email": f"admin-{email}", "password": "secret123", "gender": "Female", "dob": "1990-01-01"},
            },
            content_type="application/json",
        )
        body = response.json()
        return body["token"], body["company"]["id"]

    @override_settings(ORCHESTRATION_TOOL_THREADS=False)
    def test_an_ecommerce_store_onboards_through_the_api_alone(self):
        token, company_id = self.register("Kurta Co", "k@example.com")

        created = self.api("post", "/api/data-sources/", token, data={
            "display_name": "Products",
            "description": "Search the product catalogue by category, brand, colour, size and price.",
        }, content_type="application/json")
        self.assertEqual(created.status_code, 201, created.content)
        source_id = created.json()["id"]

        upload = SimpleUploadedFile("products.csv", PRODUCTS_CSV.encode(), content_type="text/csv")
        imported = self.api("post", f"/api/data-sources/{source_id}/import/", token, data={"file": upload})
        self.assertEqual(imported.status_code, 201, imported.content)
        fields = {f["name"]: f for f in imported.json()["fields"]}
        self.assertFalse(fields["cost_price"]["is_exposed"])

        for field in fields.values():
            patch = {"description": f"The product's {field['label']}."} if field["is_exposed"] else {}
            if field["name"] == "in_stock":
                patch = {"is_exposed": False}
            if patch:
                response = self.api("patch", f"/api/data-source-fields/{field['id']}/", token, data=patch, content_type="application/json")
                self.assertEqual(response.status_code, 200, response.content)

        configured = self.api("patch", f"/api/data-sources/{source_id}/", token, data={
            "config": {"fixed_filters": [{"field": "in_stock", "operator": "equals", "value": True}]},
        }, content_type="application/json")
        self.assertEqual(configured.status_code, 200, configured.content)

        self.assertEqual(self.api("post", f"/api/data-sources/{source_id}/confirm-schema/", token).status_code, 200)
        published = self.api("post", f"/api/data-sources/{source_id}/publish/", token)
        self.assertEqual(published.status_code, 200, published.content)
        self.assertEqual(published.json()["tool"]["name"], "search_products")

        session = resolve_session(company_id)
        run_turn(session, "show me blue kurtas under 2000", provider=FakeProvider(
            calls(("search_products", {"color": "Blue", "sub_category": "Ethnic", "max_price": 2000})), said("One kurta."),
        ))
        result = ChatMessage.objects.get(session=session, role=ChatMessage.Role.TOOL).tool_result
        self.assertEqual([row["ref"] for row in result["rows"]], ["SKU-78"])  # SKU-79 is out of stock
        self.assertNotIn("cost_price", result["rows"][0])

    def test_another_company_cannot_see_or_edit_the_source(self):
        token, company_id = self.register("Kurta Co", "k@example.com")
        other_token, _ = self.register("Rival", "r@example.com")
        chatbot = Chatbot.objects.get(company_id=company_id)
        source = DataSource.objects.create(company_id=company_id, chatbot=chatbot, name="products", display_name="Products")
        import_records(source, "products.csv", PRODUCTS_CSV.encode())
        field = source.fields.first()

        self.assertEqual(self.api("get", f"/api/data-sources/{source.id}/", other_token).status_code, 404)
        self.assertEqual(self.api("get", "/api/data-sources/", other_token).json(), [])
        self.assertEqual(
            self.api("patch", f"/api/data-source-fields/{field.id}/", other_token, data={"is_exposed": True}, content_type="application/json").status_code,
            404,
        )

    def test_publish_errors_come_back_naming_the_field(self):
        token, _ = self.register("Kurta Co", "k@example.com")
        source_id = self.api("post", "/api/data-sources/", token, data={"display_name": "Products", "description": "Products."}, content_type="application/json").json()["id"]
        upload = SimpleUploadedFile("products.csv", PRODUCTS_CSV.encode(), content_type="text/csv")
        self.api("post", f"/api/data-sources/{source_id}/import/", token, data={"file": upload})
        self.api("post", f"/api/data-sources/{source_id}/confirm-schema/", token)

        response = self.api("post", f"/api/data-sources/{source_id}/publish/", token)

        self.assertEqual(response.status_code, 400)
        self.assertIn("color", {e["field"] for e in response.json()["errors"]})
