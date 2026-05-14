package rbac

import (
	"papaya-backend/internal/storage/models"
	"testing"
)

func TestCanWithRoleSeparatesOwnAndAnyPermissions(t *testing.T) {
	role := models.Role{
		Permissions: models.Permissions{
			Posts: models.ResourcePermissions{
				Read:      true,
				UpdateOwn: true,
				DeleteOwn: true,
			},
		},
	}

	if !CanWithRole(role, ResourcePosts, ActionUpdate, true) {
		t.Fatal("expected owner update to be allowed")
	}
	if CanWithRole(role, ResourcePosts, ActionUpdate, false) {
		t.Fatal("expected foreign update to be forbidden")
	}
	if !CanWithRole(role, ResourcePosts, ActionDelete, true) {
		t.Fatal("expected owner delete to be allowed")
	}
	if CanWithRole(role, ResourcePosts, ActionDelete, false) {
		t.Fatal("expected foreign delete to be forbidden")
	}
}

func TestCanWithRoleAllowsAdminAnyPermissions(t *testing.T) {
	role := models.Role{
		Permissions: models.Permissions{
			Comments: models.ResourcePermissions{
				UpdateAny: true,
				DeleteAny: true,
			},
		},
	}

	if !CanWithRole(role, ResourceComments, ActionUpdate, false) {
		t.Fatal("expected admin-style update_any to allow foreign update")
	}
	if !CanWithRole(role, ResourceComments, ActionDelete, false) {
		t.Fatal("expected admin-style delete_any to allow foreign delete")
	}
}

func TestCanWithRoleAnyAllowsRoutesForOwnScopedPermissions(t *testing.T) {
	role := models.Role{
		Permissions: models.Permissions{
			Likes: models.ResourcePermissions{
				DeleteOwn: true,
			},
		},
	}

	if !CanWithRoleAny(role, ResourceLikes, ActionDelete) {
		t.Fatal("expected route guard to allow own-scoped delete handlers")
	}
}
