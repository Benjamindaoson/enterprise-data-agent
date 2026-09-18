"""Tests for Governance and RBAC."""

import pytest

from eiw.agent.governance import (
    Role, Permission, User, Session, AccessControl,
    AuditEventType, create_demo_personas, create_demo_session,
    create_governance_config, ROLE_PERMISSIONS
)


class TestRolePermissions:
    """Tests for role permission mappings."""

    def test_admin_has_all_permissions(self):
        """Test admin has all permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]

        for perm in Permission:
            assert perm in admin_perms

    def test_viewer_has_limited_permissions(self):
        """Test viewer has limited permissions."""
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]

        assert Permission.READ_ANY_SCHEMA in viewer_perms
        assert Permission.EXECUTE_NL2SQL not in viewer_perms
        assert Permission.MANAGE_USERS not in viewer_perms

    def test_finance_has_domain_permissions(self):
        """Test finance role has finance permissions."""
        finance_perms = ROLE_PERMISSIONS[Role.FINANCE]

        assert Permission.READ_FINANCE_SCHEMA in finance_perms
        assert Permission.USE_VARIANCE_TOOLS in finance_perms
        assert Permission.USE_PVM_TOOLS in finance_perms

    def test_sales_has_domain_permissions(self):
        """Test sales role has sales permissions."""
        sales_perms = ROLE_PERMISSIONS[Role.SALES]

        assert Permission.READ_SALES_SCHEMA in sales_perms
        assert Permission.USE_TREND_TOOLS in sales_perms
        assert Permission.USE_COMPARISON_TOOLS in sales_perms


class TestUser:
    """Tests for User model."""

    def test_create_user(self):
        """Test creating a user."""
        user = User(
            user_id="user1",
            username="testuser",
            email="test@example.com",
            roles=[Role.ANALYST],
        )

        assert user.user_id == "user1"
        assert user.username == "testuser"
        assert Role.ANALYST in user.roles

    def test_has_permission(self):
        """Test checking permissions."""
        user = User(
            user_id="user1",
            username="test",
            email="test@example.com",
            roles=[Role.VIEWER],
        )

        assert user.has_permission(Permission.READ_ANY_SCHEMA)
        assert not user.has_permission(Permission.EXECUTE_NL2SQL)

    def test_has_role(self):
        """Test checking roles."""
        user = User(
            user_id="user1",
            username="test",
            email="test@example.com",
            roles=[Role.ANALYST, Role.VIEWER],
        )

        assert user.has_role(Role.ANALYST)
        assert user.has_role(Role.VIEWER)
        assert not user.has_role(Role.ADMIN)

    def test_can_access_domain(self):
        """Test domain access."""
        finance_user = User(
            user_id="user1",
            username="test",
            email="test@example.com",
            roles=[Role.FINANCE],
        )

        assert finance_user.can_access_domain("finance")
        assert not finance_user.can_access_domain("sales")

        admin_user = User(
            user_id="user2",
            username="admin",
            email="admin@example.com",
            roles=[Role.ADMIN],
        )

        assert admin_user.can_access_domain("finance")
        assert admin_user.can_access_domain("sales")


class TestSession:
    """Tests for Session model."""

    def test_create_session(self):
        """Test creating a session."""
        session = Session(
            session_id="sess1",
            user_id="user1",
            username="testuser",
            roles=["analyst"],
        )

        assert session.session_id == "sess1"
        assert session.user_id == "user1"
        assert "analyst" in session.roles

    def test_session_has_permission(self):
        """Test session permission check."""
        session = Session(
            session_id="sess1",
            user_id="user1",
            username="test",
            roles=["viewer"],
        )

        assert session.has_permission(Permission.READ_ANY_SCHEMA)
        assert not session.has_permission(Permission.EXECUTE_NL2SQL)


class TestAccessControl:
    """Tests for AccessControl."""

    @pytest.fixture
    def access_control(self):
        """Create access control."""
        return AccessControl()

    @pytest.fixture
    def analyst_session(self):
        """Create analyst session."""
        return Session(
            session_id="sess_analyst",
            user_id="analyst1",
            username="analyst",
            roles=["analyst"],
        )

    @pytest.fixture
    def viewer_session(self):
        """Create viewer session."""
        return Session(
            session_id="sess_viewer",
            user_id="viewer1",
            username="viewer",
            roles=["viewer"],
        )

    def test_check_permission_allowed(self, access_control, analyst_session):
        """Test allowed permission check."""
        result = access_control.check_permission(
            analyst_session,
            Permission.EXECUTE_NL2SQL,
            "test_resource"
        )

        assert result is True

    def test_check_permission_denied(self, access_control, viewer_session):
        """Test denied permission check."""
        result = access_control.check_permission(
            viewer_session,
            Permission.EXECUTE_NL2SQL,
            "test_resource"
        )

        assert result is False

    def test_check_domain_access(self, access_control, analyst_session):
        """Test domain access check."""
        assert access_control.check_domain_access(analyst_session, "finance")
        assert access_control.check_domain_access(analyst_session, "sales")

    def test_can_use_tool(self, access_control, analyst_session):
        """Test tool permission check."""
        assert access_control.can_use_tool(analyst_session, "nl2sql_query")
        assert access_control.can_use_tool(analyst_session, "trend_analysis")
        assert access_control.can_use_tool(analyst_session, "python_analysis")

    def test_cannot_use_tool_without_permission(self, access_control, viewer_session):
        """Test tool denied."""
        assert not access_control.can_use_tool(viewer_session, "nl2sql_query")
        assert not access_control.can_use_tool(viewer_session, "python_analysis")

    def test_can_export_data(self, access_control, analyst_session):
        """Test export permission."""
        assert access_control.can_export_data(analyst_session)

    def test_cannot_export_data(self, access_control, viewer_session):
        """Test export denied."""
        assert not access_control.can_export_data(viewer_session)


class TestAuditLog:
    """Tests for audit logging."""

    @pytest.fixture
    def access_control(self):
        """Create access control."""
        return AccessControl()

    def test_log_permission_check(self, access_control):
        """Test permission check is logged."""
        session = Session(
            session_id="sess1",
            user_id="user1",
            username="test",
            roles=["viewer"],
        )

        access_control.check_permission(session, Permission.EXECUTE_NL2SQL)

        log = access_control.get_audit_log()
        assert len(log) > 0
        assert log[-1]["event_type"] == "permission_denied"

    def test_filter_by_user(self, access_control):
        """Test filtering by user."""
        session1 = Session(
            session_id="sess1",
            user_id="user1",
            username="test1",
            roles=["analyst"],
        )
        session2 = Session(
            session_id="sess2",
            user_id="user2",
            username="test2",
            roles=["analyst"],
        )

        access_control.check_permission(session1, Permission.READ_ANY_SCHEMA)
        access_control.check_permission(session2, Permission.EXECUTE_NL2SQL)

        log1 = access_control.get_audit_log(user_id="user1")
        assert len(log1) == 1
        assert log1[0]["user_id"] == "user1"


class TestDemoPersonas:
    """Tests for demo personas."""

    def test_create_demo_personas(self):
        """Test creating demo personas."""
        personas = create_demo_personas()

        assert "admin" in personas
        assert "analyst_alice" in personas
        assert "viewer_bob" in personas
        assert "finance_carol" in personas
        assert "sales_david" in personas
        assert "ops_eve" in personas

    def test_demo_persona_roles(self):
        """Test demo persona roles."""
        personas = create_demo_personas()

        assert Role.ADMIN in personas["admin"].roles
        assert Role.ANALYST in personas["analyst_alice"].roles
        assert Role.VIEWER in personas["viewer_bob"].roles
        assert Role.FINANCE in personas["finance_carol"].roles
        assert Role.SALES in personas["sales_david"].roles
        assert Role.OPERATIONS in personas["ops_eve"].roles

    def test_create_demo_session(self):
        """Test creating demo session."""
        personas = create_demo_personas()
        session = create_demo_session(personas["analyst_alice"])

        assert session.user_id == "analyst_alice"
        assert "analyst" in session.roles


class TestGovernanceConfig:
    """Tests for governance configuration."""

    def test_default_config(self):
        """Test default config."""
        config = create_governance_config()

        assert config.enable_rbac is True
        assert config.enable_audit_log is True
        assert config.require_authentication is True
        assert config.max_query_timeout_seconds == 60
        assert config.max_export_rows == 10000

    def test_custom_config(self):
        """Test custom config."""
        from eiw.agent.governance import GovernanceConfig

        config = GovernanceConfig(
            enable_rbac=False,
            enable_audit_log=True,
            max_export_rows=5000,
        )

        assert config.enable_rbac is False
        assert config.max_export_rows == 5000
