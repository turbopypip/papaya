package logger

import (
	"os"
	"papaya-backend/internal/config"

	"github.com/sirupsen/logrus"
)

func InitLogger() {
	// Process name for logging
	const processName = "InitLogger"

	// Load config
	cfg := config.MustLoad()

	// Format
	logrus.SetFormatter(&logrus.JSONFormatter{})

	// Output
	logrus.SetOutput(os.Stdout)

	level, err := logrus.ParseLevel(cfg.LogLevel)
	if err != nil {
		logrus.Fatal("Error: ", err, ". Process: ", processName, ".")
	} else {
		logrus.SetLevel(level)
	}
}
