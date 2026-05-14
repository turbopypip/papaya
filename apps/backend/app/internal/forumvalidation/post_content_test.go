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

func TestValidateCommentContent(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		content string
		wantErr bool
	}{
		{
			name:    "plain text",
			content: "This is a valid comment",
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
			content: strings.Repeat("a", MaxCommentContentRunes+1),
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

			err := ValidateCommentContent(tt.content)
			if tt.wantErr && err == nil {
				t.Fatal("expected validation error")
			}
			if !tt.wantErr && err != nil {
				t.Fatalf("expected valid content, got %v", err)
			}
		})
	}
}

func TestValidateThread(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		title      string
		categories []string
		want       []string
		wantErr    bool
	}{
		{
			name:       "valid thread",
			title:      "How to profile Go services?",
			categories: []string{" go ", "performance"},
			want:       []string{"go", "performance"},
		},
		{
			name:       "multiline title",
			title:      "How to profile\nGo services?",
			categories: []string{"go"},
			wantErr:    true,
		},
		{
			name:    "empty title",
			title:   "   ",
			wantErr: true,
		},
		{
			name:    "too long title",
			title:   strings.Repeat("a", MaxThreadTitleRunes+1),
			wantErr: true,
		},
		{
			name:       "empty categories are dropped",
			title:      "Valid",
			categories: []string{"go", " ", ""},
			want:       []string{"go"},
		},
		{
			name:       "too many categories",
			title:      "Valid",
			categories: []string{"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"},
			wantErr:    true,
		},
		{
			name:       "invalid category",
			title:      "Valid",
			categories: []string{"go" + string(rune(0x00))},
			wantErr:    true,
		},
		{
			name:       "multiline category",
			title:      "Valid",
			categories: []string{"go\nbackend"},
			wantErr:    true,
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got, err := ValidateThread(tt.title, tt.categories)
			if tt.wantErr && err == nil {
				t.Fatal("expected validation error")
			}
			if !tt.wantErr && err != nil {
				t.Fatalf("expected valid thread, got %v", err)
			}
			if !tt.wantErr {
				if len(got) != len(tt.want) {
					t.Fatalf("expected %d categories, got %d", len(tt.want), len(got))
				}
				for i := range got {
					if got[i] != tt.want[i] {
						t.Fatalf("expected category %q at index %d, got %q", tt.want[i], i, got[i])
					}
				}
			}
		})
	}
}
