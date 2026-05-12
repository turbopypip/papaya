package forumvalidation

import (
	"strings"
	"testing"
)

func TestValidatePostContent(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		content string
		wantErr bool
	}{
		{
			name:    "plain text",
			content: "This is a valid post",
		},
		{
			name:    "html with code block",
			content: "<p>Example</p><pre><code>const x = 1;</code></pre>",
		},
		{
			name:    "empty text",
			content: "   \n\t",
			wantErr: true,
		},
		{
			name:    "too long",
			content: strings.Repeat("a", MaxPostContentRunes+1),
			wantErr: true,
		},
		{
			name:    "invalid utf8",
			content: string([]byte{0xff, 0xfe}),
			wantErr: true,
		},
		{
			name:    "unsupported control character",
			content: "hello" + string(rune(0x00)),
			wantErr: true,
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			err := ValidatePostContent(tt.content)
			if tt.wantErr && err == nil {
				t.Fatal("expected validation error")
			}
			if !tt.wantErr && err != nil {
				t.Fatalf("expected valid content, got %v", err)
			}
		})
	}
}
