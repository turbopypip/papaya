package authvalidation

import "testing"

func TestValidatePassword(t *testing.T) {
	tests := []struct {
		name          string
		password      string
		wantErr       bool
		wantReasonLen int
	}{
		{
			name:     "valid password",
			password: "Papaya-123",
		},
		{
			name:          "empty password",
			password:      "",
			wantErr:       true,
			wantReasonLen: 5,
		},
		{
			name:          "too short",
			password:      "Pa1!",
			wantErr:       true,
			wantReasonLen: 1,
		},
		{
			name:          "too short with multibyte characters",
			password:      "Pa1!Ж",
			wantErr:       true,
			wantReasonLen: 1,
		},
		{
			name:          "missing lowercase latin",
			password:      "PAPAYA-123",
			wantErr:       true,
			wantReasonLen: 1,
		},
		{
			name:          "missing uppercase latin",
			password:      "papaya-123",
			wantErr:       true,
			wantReasonLen: 1,
		},
		{
			name:          "missing digit",
			password:      "Papaya-pass",
			wantErr:       true,
			wantReasonLen: 1,
		},
		{
			name:          "missing special character",
			password:      "Papaya123",
			wantErr:       true,
			wantReasonLen: 1,
		},
		{
			name:          "non latin letters do not satisfy latin requirements",
			password:      "Пароль-123",
			wantErr:       true,
			wantReasonLen: 2,
		},
		{
			name:     "non latin characters can be special characters",
			password: "Papaya1Ж",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidatePassword(tt.password)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected validation error")
				}

				validationError, ok := err.(PasswordValidationError)
				if !ok {
					t.Fatalf("expected PasswordValidationError, got %T", err)
				}
				if got := len(validationError.Reasons); got != tt.wantReasonLen {
					t.Fatalf("expected %d reasons, got %d: %v", tt.wantReasonLen, got, validationError.Reasons)
				}

				return
			}

			if err != nil {
				t.Fatalf("expected valid password, got %v", err)
			}
		})
	}
}
