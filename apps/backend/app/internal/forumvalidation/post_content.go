package forumvalidation

import (
	"errors"
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"

	"golang.org/x/net/html"
)

const MaxPostContentRunes = 20000

func ValidatePostContent(content string) error {
	if strings.TrimSpace(content) == "" {
		return errors.New("Post content is required")
	}

	if !utf8.ValidString(content) {
		return errors.New("Post content must be valid UTF-8")
	}

	if utf8.RuneCountInString(content) > MaxPostContentRunes {
		return fmt.Errorf("Post content must be %d characters or fewer", MaxPostContentRunes)
	}

	for _, r := range content {
		if unicode.IsControl(r) && r != '\n' && r != '\r' && r != '\t' {
			return errors.New("Post content contains unsupported control characters")
		}
	}

	if _, err := html.ParseFragment(strings.NewReader(content), nil); err != nil {
		return errors.New("Post content must be valid HTML or plain text")
	}

	return nil
}
