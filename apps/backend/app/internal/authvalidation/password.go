package authvalidation

import (
	"strings"
	"unicode/utf8"
)

const PasswordMinLength = 8

type PasswordValidationError struct {
	Reasons []string
}

func (e PasswordValidationError) Error() string {
	return strings.Join(e.Reasons, "; ")
}

func ValidatePassword(password string) error {
	var reasons []string

	if utf8.RuneCountInString(password) < PasswordMinLength {
		reasons = append(reasons, "Пароль должен быть не короче 8 символов")
	}
	if !hasLowercaseLatin(password) {
		reasons = append(reasons, "Пароль должен содержать строчную латинскую букву")
	}
	if !hasUppercaseLatin(password) {
		reasons = append(reasons, "Пароль должен содержать заглавную латинскую букву")
	}
	if !hasDigit(password) {
		reasons = append(reasons, "Пароль должен содержать цифру")
	}
	if !hasSpecialCharacter(password) {
		reasons = append(reasons, "Пароль должен содержать специальный символ")
	}

	if len(reasons) > 0 {
		return PasswordValidationError{Reasons: reasons}
	}

	return nil
}

func hasLowercaseLatin(password string) bool {
	for _, char := range password {
		if char >= 'a' && char <= 'z' {
			return true
		}
	}

	return false
}

func hasUppercaseLatin(password string) bool {
	for _, char := range password {
		if char >= 'A' && char <= 'Z' {
			return true
		}
	}

	return false
}

func hasDigit(password string) bool {
	for _, char := range password {
		if char >= '0' && char <= '9' {
			return true
		}
	}

	return false
}

func hasSpecialCharacter(password string) bool {
	for _, char := range password {
		isLowercaseLatin := char >= 'a' && char <= 'z'
		isUppercaseLatin := char >= 'A' && char <= 'Z'
		isDigit := char >= '0' && char <= '9'

		if !isLowercaseLatin && !isUppercaseLatin && !isDigit {
			return true
		}
	}

	return false
}
