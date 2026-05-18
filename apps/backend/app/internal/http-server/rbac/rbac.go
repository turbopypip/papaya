package rbac

import (
	"net/http"
	"papaya-backend/internal/storage/models"

	"github.com/gin-gonic/gin"
	"github.com/gofrs/uuid"
)

type Resource string
type Action string

const (
	ResourceThreads     Resource = "threads"
	ResourcePosts       Resource = "posts"
	ResourceComments    Resource = "comments"
	ResourceCategories  Resource = "categories"
	ResourceLikes       Resource = "likes"
	ResourceAttachments Resource = "attachments"
	ResourceUsers       Resource = "users"
)

const (
	ActionCreate Action = "create"
	ActionRead   Action = "read"
	ActionUpdate Action = "update"
	ActionDelete Action = "delete"
)

func CurrentUser(c *gin.Context) (models.User, bool) {
	value, ok := c.Get("user")
	if !ok {
		return models.User{}, false
	}

	user, ok := value.(models.User)
	return user, ok
}

func CurrentRole(c *gin.Context) (models.Role, bool) {
	value, ok := c.Get("role")
	if !ok {
		return models.Role{}, false
	}

	role, ok := value.(models.Role)
	return role, ok
}

func Require(resource Resource, action Action) gin.HandlerFunc {
	return func(c *gin.Context) {
		if !Can(c, resource, action, uuid.Nil) {
			AbortForbidden(c, "У вас нет прав на это действие")
			return
		}

		c.Next()
	}
}

func RequireAny(resource Resource, action Action) gin.HandlerFunc {
	return func(c *gin.Context) {
		role, ok := CurrentRole(c)
		if !ok || !CanWithRoleAny(role, resource, action) {
			AbortForbidden(c, "У вас нет прав на это действие")
			return
		}

		c.Next()
	}
}

func RequireAdmin() gin.HandlerFunc {
	return func(c *gin.Context) {
		role, ok := CurrentRole(c)
		if !ok || role.Name != "admin" {
			AbortForbidden(c, "Для этого действия нужны права администратора")
			return
		}

		c.Next()
	}
}

func Can(c *gin.Context, resource Resource, action Action, ownerID uuid.UUID) bool {
	user, ok := CurrentUser(c)
	if !ok {
		return false
	}

	role, ok := CurrentRole(c)
	if !ok {
		return false
	}

	return CanWithRole(role, resource, action, ownerID != uuid.Nil && ownerID == user.Id)
}

func CanAny(c *gin.Context, resource Resource, action Action) bool {
	role, ok := CurrentRole(c)
	if !ok {
		return false
	}

	return CanWithRoleAny(role, resource, action)
}

func CanWithRole(role models.Role, resource Resource, action Action, isOwner bool) bool {
	switch resource {
	case ResourceThreads:
		return canResource(role.Permissions.Threads, action, isOwner)
	case ResourcePosts:
		return canResource(role.Permissions.Posts, action, isOwner)
	case ResourceComments:
		return canResource(role.Permissions.Comments, action, isOwner)
	case ResourceCategories:
		return canResource(role.Permissions.Categories, action, isOwner)
	case ResourceLikes:
		return canResource(role.Permissions.Likes, action, isOwner)
	case ResourceAttachments:
		return canResource(role.Permissions.Attachments, action, isOwner)
	case ResourceUsers:
		return canUser(role.Permissions.Users, action, isOwner)
	default:
		return false
	}
}

func CanWithRoleAny(role models.Role, resource Resource, action Action) bool {
	switch resource {
	case ResourceThreads:
		return canResourceAny(role.Permissions.Threads, action)
	case ResourcePosts:
		return canResourceAny(role.Permissions.Posts, action)
	case ResourceComments:
		return canResourceAny(role.Permissions.Comments, action)
	case ResourceCategories:
		return canResourceAny(role.Permissions.Categories, action)
	case ResourceLikes:
		return canResourceAny(role.Permissions.Likes, action)
	case ResourceAttachments:
		return canResourceAny(role.Permissions.Attachments, action)
	case ResourceUsers:
		return canUserAny(role.Permissions.Users, action)
	default:
		return false
	}
}

func AbortForbidden(c *gin.Context, message string) {
	c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": message})
}

func canResource(permissions models.ResourcePermissions, action Action, isOwner bool) bool {
	switch action {
	case ActionCreate:
		return permissions.Create
	case ActionRead:
		return permissions.Read
	case ActionUpdate:
		return permissions.UpdateAny || (isOwner && permissions.UpdateOwn)
	case ActionDelete:
		return permissions.DeleteAny || (isOwner && permissions.DeleteOwn)
	default:
		return false
	}
}

func canResourceAny(permissions models.ResourcePermissions, action Action) bool {
	switch action {
	case ActionCreate:
		return permissions.Create
	case ActionRead:
		return permissions.Read
	case ActionUpdate:
		return permissions.UpdateAny || permissions.UpdateOwn
	case ActionDelete:
		return permissions.DeleteAny || permissions.DeleteOwn
	default:
		return false
	}
}

func canUser(permissions models.UserPermissions, action Action, isOwner bool) bool {
	switch action {
	case ActionCreate:
		return permissions.Create
	case ActionRead:
		return permissions.Read
	case ActionUpdate:
		return permissions.UpdateAny || (isOwner && permissions.UpdateOwn)
	case ActionDelete:
		return permissions.DeleteAny || (isOwner && permissions.DeleteOwn)
	default:
		return false
	}
}

func canUserAny(permissions models.UserPermissions, action Action) bool {
	switch action {
	case ActionCreate:
		return permissions.Create
	case ActionRead:
		return permissions.Read
	case ActionUpdate:
		return permissions.UpdateAny || permissions.UpdateOwn
	case ActionDelete:
		return permissions.DeleteAny || permissions.DeleteOwn
	default:
		return false
	}
}
