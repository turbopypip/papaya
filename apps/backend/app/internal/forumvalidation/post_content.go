package forumvalidation

import (
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"

	"golang.org/x/net/html"
)

const (
	MaxPostContentRunes    = 20000
	MaxCommentContentRunes = 20000
)

func ValidatePostContent(content string) error {
	return validateContent(content, "Post", MaxPostContentRunes)
}

func ValidateCommentContent(content string) error {
	return validateContent(content, "Comment", MaxCommentContentRunes)
}

func validateContent(content string, label string, maxRunes int) error {
	if strings.TrimSpace(content) == "" {
		return fmt.Errorf("%s content is required", label)
	}

	if !utf8.ValidString(content) {
		return fmt.Errorf("%s content must be valid UTF-8", label)
	}

	if utf8.RuneCountInString(content) > maxRunes {
		return fmt.Errorf("%s content must be %d characters or fewer", label, maxRunes)
	}

	for _, r := range content {
		if unicode.IsControl(r) && r != '\n' && r != '\r' && r != '\t' {
			return fmt.Errorf("%s content contains unsupported control characters", label)
		}
	}

	if _, err := html.ParseFragment(strings.NewReader(content), nil); err != nil {
		return fmt.Errorf("%s content must be valid HTML or plain text", label)
	}

	return nil
}
