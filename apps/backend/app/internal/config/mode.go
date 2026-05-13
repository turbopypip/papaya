package config

import (
	"os"
	"strings"
)

func CurrentEnv() string {
	if env := os.Getenv("APP_ENV"); env != "" {
		return strings.ToLower(env)
	}

	if env := os.Getenv("ENV"); env != "" {
		return strings.ToLower(env)
	}

	if os.Getenv("LOCAL_CONFIG_PATH") == "" {
		return "prod"
	}

	return strings.ToLower(MustLoad().Env)
}

func IsDev() bool {
	env := CurrentEnv()
	return env == "dev" || env == "development"
}
