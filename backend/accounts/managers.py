from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Users log in by email, stored lower-case so "Ana@x.test" and "ana@x.test" match."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        from accounts.models import Role

        extra.update(role=Role.ADMIN, is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra)
