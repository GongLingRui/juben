"""
Unit tests for RBAC (Role-Based Access Control)

Tests role and permission management
"""
import pytest
from enum import Enum


@pytest.mark.unit
class TestRoleEnum:
    """Test Role enumeration"""

    def test_role_values(self):
        """Test all role enum values exist"""
        from utils.rbac import Role

        assert Role.USER.value == "user"
        assert Role.ADMIN.value == "admin"
        assert Role.MODERATOR.value == "moderator"
        assert Role.EDITOR.value == "editor"
        assert Role.VIEWER.value == "viewer"
        assert Role.SYSTEM_ADMIN.value == "system_admin"

    def test_role_from_string(self):
        """Test creating Role from string value"""
        from utils.rbac import Role

        role = Role("admin")
        assert role == Role.ADMIN

    def test_invalid_role(self):
        """Test invalid role raises error"""
        from utils.rbac import Role
        from enum import ValidationError

        with pytest.raises((ValueError, KeyError)):
            Role("invalid_role")


@pytest.mark.unit
class TestPermissionEnum:
    """Test Permission enumeration"""

    def test_permission_categories(self):
        """Test permissions are categorized properly"""
        from utils.rbac import Permission

        # System permissions
        assert Permission.SYSTEM_ADMIN in Permission
        assert Permission.SYSTEM_READ in Permission

        # User permissions
        assert Permission.USER_CREATE in Permission
        assert Permission.USER_READ in Permission
        assert Permission.USER_UPDATE in Permission
        assert Permission.USER_DELETE in Permission

        # Content permissions
        assert Permission.CONTENT_CREATE in Permission
        assert Permission.CONTENT_READ in Permission
        assert Permission.CONTENT_UPDATE in Permission
        assert Permission.CONTENT_DELETE in Permission

    def test_permission_values_are_unique(self):
        """Test all permission values are unique"""
        from utils.rbac import Permission

        values = [p.value for p in Permission]
        assert len(values) == len(set(values)), "Permission values should be unique"


@pytest.mark.unit
class TestRoleDefinition:
    """Test RoleDefinition dataclass"""

    def test_role_definition_structure(self):
        """Test role definition has correct structure"""
        from utils.rbac import RoleDefinition, Role, Permission

        definition = RoleDefinition(
            name=Role.ADMIN,
            display_name="管理员",
            description="系统管理员",
            permissions=[
                Permission.SYSTEM_ADMIN,
                Permission.USER_CREATE
            ],
            is_system_role=True
        )

        assert definition.name == Role.ADMIN
        assert definition.display_name == "管理员"
        assert len(definition.permissions) == 2
        assert definition.is_system_role is True


@pytest.mark.unit
class TestRBACChecker:
    """Test RBACChecker class"""

    @pytest.fixture
    def checker(self):
        """Create RBACChecker instance"""
        from utils.rbac import RBACChecker
        return RBACChecker()

    def test_get_all_roles(self, checker):
        """Test getting all available roles"""
        roles = checker.list_all_roles()

        assert isinstance(roles, list)
        assert len(roles) > 0
        assert all("name" in role and "display_name" in role for role in roles)

    def test_get_role_definition(self, checker):
        """Test getting specific role definition"""
        from utils.rbac import Role

        definition = checker.get_role_definition(Role.ADMIN)

        assert definition is not None
        assert definition.name == Role.ADMIN
        assert len(definition.permissions) > 0

    def test_get_permissions_for_roles(self, checker):
        """Test getting permissions for multiple roles"""
        from utils.rbac import Role, Permission

        permissions = checker.get_permissions_for_roles([Role.USER])

        assert isinstance(permissions, set)
        assert len(permissions) > 0

    def test_admin_has_all_permissions(self, checker):
        """Test admin role has all permissions"""
        from utils.rbac import Role, Permission

        permissions = checker.get_permissions_for_roles([Role.ADMIN])

        # Admin should have SYSTEM_ADMIN which gives all permissions
        assert Permission.SYSTEM_ADMIN in permissions

    def test_user_has_limited_permissions(self, checker):
        """Test user role has limited permissions"""
        from utils.rbac import Role, Permission

        permissions = checker.get_permissions_for_roles([Role.USER])

        # Regular users should not have admin permissions
        assert Permission.SYSTEM_ADMIN not in permissions
        assert Permission.USER_DELETE not in permissions

    def test_viewer_has_read_only_permissions(self, checker):
        """Test viewer role only has read permissions"""
        from utils.rbac import Role, Permission

        permissions = checker.get_permissions_for_roles([Role.VIEWER])

        # Viewers should only have read permissions
        assert Permission.CONTENT_READ in permissions
        assert Permission.CONTENT_CREATE not in permissions

    def test_check_permission_for_role(self, checker):
        """Test checking permission for specific role"""
        from utils.rbac import Role, Permission

        # Admin should have all permissions
        assert checker.role_has_permission(Role.ADMIN, Permission.SYSTEM_ADMIN)
        assert checker.role_has_permission(Role.ADMIN, Permission.USER_CREATE)

        # Viewer should only have read
        assert checker.role_has_permission(Role.VIEWER, Permission.CONTENT_READ)
        assert not checker.role_has_permission(Role.VIEWER, Permission.CONTENT_DELETE)


@pytest.mark.unit
class TestRBACDecorator:
    """Test RBAC decorator functions"""

    def test_require_permissions_decorator(self):
        """Test require_permissions decorator"""
        from utils.rbac import require_permissions, Permission

        @require_permissions([Permission.USER_READ])
        def read_user_function():
            return "success"

        # This should not raise an error
        assert read_user_function.__name__ == "read_user_function"

    def test_require_permissions_multiple(self):
        """Test require_permissions with multiple permissions"""
        from utils.rbac import require_permissions, Permission

        @require_permissions([
            Permission.USER_CREATE,
            Permission.USER_UPDATE
        ])
        def manage_user_function():
            return "success"

        assert manage_user_function.__name__ == "manage_user_function"


@pytest.mark.unit
class TestRBACIntegration:
    """Test RBAC integration scenarios"""

    def test_user_permissions_calculation(self):
        """Test calculating user permissions from roles"""
        from utils.rbac import RBACChecker, Role, Permission

        checker = RBACChecker()

        # User with single role
        user_roles = [Role.USER]
        permissions = checker.get_permissions_for_roles(user_roles)

        assert len(permissions) > 0
        assert Permission.CONTENT_READ in permissions

    def test_mixed_role_permissions(self):
        """Test permissions with mixed roles"""
        from utils.rbac import RBACChecker, Role, Permission

        checker = RBACChecker()

        # User with multiple roles
        user_roles = [Role.VIEWER, Role.EDITOR]
        permissions = checker.get_permissions_for_roles(user_roles)

        # Should have union of permissions
        assert Permission.CONTENT_READ in permissions  # From VIEWER
        assert Permission.CONTENT_UPDATE in permissions  # From EDITER

    def test_role_hierarchy(self):
        """Test that admin role has more permissions than user"""
        from utils.rbac import RBACChecker, Role

        checker = RBACChecker()

        admin_perms = checker.get_permissions_for_roles([Role.ADMIN])
        user_perms = checker.get_permissions_for_roles([Role.USER])

        assert len(admin_perms) > len(user_perms)
