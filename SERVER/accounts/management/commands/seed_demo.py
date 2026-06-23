"""Seed a demo tenant + login-ready users for local development.

Idempotent: re-running updates the password on existing accounts rather than
erroring on the unique email. Safe to run as many times as you like.

Examples
--------
    # Defaults: company "Demo Co" + admin@demo.com / Demo12345!
    python manage.py seed_demo

    # Custom company-admin credentials
    python manage.py seed_demo --email me@example.com --password "Secret123!"

    # Also create a Django superuser (for /admin/)
    python manage.py seed_demo --superuser
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from companies.models import Company, UserCompany
from core.enums import CompanyStatus, UserRole


class Command(BaseCommand):
    help = "Create a demo company and login-ready user(s) for development."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@demo.com",
                            help="Company-admin email (default: admin@demo.com)")
        parser.add_argument("--password", default="Demo12345!",
                            help="Password for the seeded user(s) (default: Demo12345!)")
        parser.add_argument("--full-name", default="Demo Admin",
                            help="Full name of the company admin.")
        parser.add_argument("--company", default="Demo Co",
                            help="Company (tenant) name (default: Demo Co).")
        parser.add_argument("--superuser", action="store_true",
                            help="Also create a SUPER_ADMIN Django superuser.")

    @transaction.atomic
    def handle(self, *args, **opts):
        email = opts["email"].lower().strip()
        password = opts["password"]

        # 1) Tenant ---------------------------------------------------------
        company, created = Company.objects.get_or_create(
            name=opts["company"],
            defaults={"email": email, "status": CompanyStatus.ACTIVE},
        )
        self.stdout.write(
            self.style.SUCCESS(f"{'Created' if created else 'Found'} company: {company.name}")
        )

        # 2) Company admin, bound to the tenant -----------------------------
        admin = self._upsert_user(
            email=email,
            password=password,
            full_name=opts["full_name"],
            role=UserRole.COMPANY_ADMIN,
            company=company,
        )
        # Record the multi-tenant membership too.
        UserCompany.objects.get_or_create(
            user=admin, company=company,
            defaults={"role": UserRole.COMPANY_ADMIN},
        )

        # 3) Optional platform superuser ------------------------------------
        if opts["superuser"]:
            su_email = f"super+{email}" if "@" not in email else "super@demo.com"
            self._upsert_user(
                email=su_email,
                password=password,
                full_name="Super Admin",
                role=UserRole.SUPER_ADMIN,
                company=None,
                is_staff=True,
                is_superuser=True,
            )

        self.stdout.write(self.style.SUCCESS("\nDone. Log in with:"))
        self.stdout.write(f"  email:    {email}")
        self.stdout.write(f"  password: {password}")

    def _upsert_user(self, *, email, password, full_name, role, company,
                     is_staff=False, is_superuser=False):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": full_name,
                "role": role,
                "company": company,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
                "is_active": True,
            },
        )
        # Always (re)set the password + role so re-runs are predictable.
        user.full_name = full_name
        user.role = role
        user.company = company
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(
            self.style.SUCCESS(f"{'Created' if created else 'Updated'} user: {email} ({role})")
        )
        return user
