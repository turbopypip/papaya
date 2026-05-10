package config

import (
	"log"
	"os"
	"time"

	"github.com/ilyakaznacheev/cleanenv"
)

type Config struct {
	Env         string `yaml:"env" env:"ENV" env-default:"local" env-required:"true"`
	StoragePath string `yaml:"storage-path"`
	LogLevel    string `yaml:"log-level" env-default:"info"`
	HTTPServer  `yaml:"http_server"`
	Redis       RedisConfig `yaml:"redis"`
}

type HTTPServer struct {
	Address     string        `yaml:"address" env-default:"8888"`
	Timeout     time.Duration `yaml:"timeout" env-default:"4s"`
	IdleTimeout time.Duration `yaml:"idle-timeout" env-default:"60s"`
}

type RedisConfig struct {
	Address  string `yaml:"address" env-default:"localhost:6379"`
	Password string `yaml:"password" env-default:""`
	DB       int    `yaml:"db" env-default:"0"`
}

func MustLoad() *Config {
	configPath := os.Getenv("LOCAL_CONFIG_PATH")
	if configPath == "" {
		log.Fatal("LOCAL_CONFIG_PATH has to be set")
	}

	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		log.Fatalf("config file %s does not exist", configPath)
	}
	var cfg Config

	if err := cleanenv.ReadConfig(configPath, &cfg); err != nil {
		log.Fatalf("cannot read config: %s", configPath)
	}

	return &cfg
}
