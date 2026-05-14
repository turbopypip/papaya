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
	MaxThreadTitleRunes    = 200
	MaxThreadCategories    = 10
	MaxThreadCategoryRunes = 40
)

func ValidatePostContent(content string) error {
	return validateContent(content, "Post", MaxPostContentRunes)
}

func ValidateCommentContent(content string) error {
	return validateContent(content, "Comment", MaxCommentContentRunes)
}

func ValidateThread(title string, categories []string) ([]string, error) {
	if err := validatePlainText(title, "Thread title", MaxThreadTitleRunes, false); err != nil {
		return nil, err
	}

	normalizedCategories := make([]string, 0, len(categories))
	for _, category := range categories {
		category = strings.TrimSpace(category)
		if category == "" {
			continue
		}
		if err := validatePlainText(category, "Thread category", MaxThreadCategoryRunes, false); err != nil {
			return nil, err
		}
		normalizedCategories = append(normalizedCategories, category)
	}

	if len(normalizedCategories) > MaxThreadCategories {
		return nil, fmt.Errorf("Thread can have at most %d categories", MaxThreadCategories)
	}

	return normalizedCategories, nil
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

func validatePlainText(value string, label string, maxRunes int, allowWhitespaceControls bool) error {
	if strings.TrimSpace(value) == "" {
		return fmt.Errorf("%s is required", label)
	}

	if !utf8.ValidString(value) {
		return fmt.Errorf("%s must be valid UTF-8", label)
	}

	if utf8.RuneCountInString(value) > maxRunes {
		return fmt.Errorf("%s must be %d characters or fewer", label, maxRunes)
	}

	for _, r := range value {
		if unicode.IsControl(r) && (!allowWhitespaceControls || (r != '\n' && r != '\r' && r != '\t')) {
			return fmt.Errorf("%s contains unsupported control characters", label)
		}
	}

	return nil
}
